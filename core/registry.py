"""
core/registry.py — Addon yükleme motoru + şema genişletme (extend) mekanizması

ODOO İLE KARŞILAŞTIRMA:
    Odoo'da her modül `__manifest__.py` içinde bağımlılıklarını bildirir ve
    Odoo'nun registry'si (odoo/modules/registry.py) modülleri doğru sırada
    yükler, modelleri birleştirir (mro chain), ve DB'yi günceller.

    Burada aynı prensibi Flask + SQLAlchemy + Alembic üçlüsü için kuruyoruz:

    1. Her addon __manifest__.py'da 'bagimliliklar' bildirir
    2. register_addons() bu bildirimleri okuyup topolojik sıralama yapar
       (bağımlılık önce yüklenir)
    3. Her addon'un routes.py'si Flask app'e Blueprint olarak kaydedilir
    4. Şema extend isteyen addon'lar extend_model() ile mixin ekler

ŞEMA EXTEND MEKANİZMASI (Odoo'nun _inherit'ine karşılık):
    Odoo'da:
        class StokKarti(models.Model):
            _inherit = 'stok.karti'
            barkod_qr = fields.Char()

    OpenPyERP'te:
        # addons/eticaret/models.py
        class StokKartiEticaretMixin:
            barkod_qr = db.Column(db.String(200))

        # addons/eticaret/__init__.py
        from core.registry import extend_model
        from addons.stok.models import StokKarti
        from addons.eticaret.models import StokKartiEticaretMixin
        extend_model(StokKarti, StokKartiEticaretMixin)

    + addons/eticaret/migrations/xxxx_stok_karti_barkod_qr.py Alembic migration

    Bu iki adım:
    - Python tarafı (extend_model) → runtime'da alan erişilebilir olur
    - Alembic migration → DB'de fiziksel kolon oluşur
    - İkisi birlikte Odoo'nun ALTER TABLE + registry birleştirmesine karşılık gelir

NEDEN METACLASS / POOL DEĞİL?
    Tryton'un PoolMeta, Odoo'nun ModelRegistry gibi metaclass tabanlı çözümler
    Python'ın class yükleme mekanizmasına müdahale eder — güçlüdür ama
    hata ayıklaması çok zordur, IDE desteği zayıftır, SQLAlchemy ile
    çakışma riski yüksektir. SQLAlchemy zaten kendi mapper registry'sini
    yönetir — bunun üstüne bir metaclass daha eklemek "iki kayıt defteri"
    sorununa yol açar. extend_model() + Alembic, daha az sihir, daha fazla
    kontrol sağlar.
"""
import importlib
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

# Yüklü addon listesi — app factory tarafından doldurulur
_yuklenmis_addonlar: List[str] = []


# ════════════════════════════════════════════════════════════
#  ŞEMA EXTEND MEKANİZMASI
# ════════════════════════════════════════════════════════════

def extend_model(hedef_model, mixin_sinifi):
    """Var olan bir SQLAlchemy modeline, başka bir addon'dan mixin ekler.

    Odoo'nun `_inherit = 'model.adi'` ile aynı AMACI taşır ama farklı mekanizma:
    Python'ın __bases__ manipülasyonu yerine, SQLAlchemy'nin declared_attr ve
    __table_args__ extend_existing mekanizmasını kullanır.

    KULLANIM:
        from core.registry import extend_model
        from addons.stok.models import StokKarti

        class StokKartiEticaretMixin:
            '''addons/eticaret/models.py içinde tanımlanır'''
            barkod_qr = db.Column(db.String(200), nullable=True)

        extend_model(StokKarti, StokKartiEticaretMixin)
        # Artık StokKarti.barkod_qr erişilebilir

    ÖNEMLİ: Bu SADECE Python tarafını günceller. DB'de fiziksel kolonun
    oluşması için addons/eticaret/migrations/ altında Alembic migration
    dosyası da gerekir. İkisi birlikte Odoo'nun _inherit + ALTER TABLE'ına
    karşılık gelir.

    SINIRLAMALAR:
        - Sadece Column ekleyebilirsiniz (relationship, index eklemek için
          ayrıca __table_args__ ve mapper konfigürasyonu gerekir — bu
          durumda doğrudan migration dosyasına yazın)
        - app.py factory çalışmadan ÖNCE çağrılmalıdır (db.init_app öncesi)
        - Aynı kolon adı iki kez extend edilirse SQLAlchemy hata verir
    """
    for attr_adi, deger in vars(mixin_sinifi).items():
        if attr_adi.startswith('_'):
            continue
        if not hasattr(hedef_model, attr_adi):
            setattr(hedef_model, attr_adi, deger)
            logger.debug(
                "extend_model: %s.%s ← %s",
                hedef_model.__name__, attr_adi, mixin_sinifi.__name__
            )
        else:
            logger.warning(
                "extend_model: %s.%s zaten var, %s'dan gelen alan ATLANДИ.",
                hedef_model.__name__, attr_adi, mixin_sinifi.__name__
            )


# ════════════════════════════════════════════════════════════
#  BAĞIMLILIK SIRALAMA (topolojik sort)
# ════════════════════════════════════════════════════════════

def _topolojik_sirala(addonlar: Dict[str, List[str]]) -> List[str]:
    """Bağımlılık sıralaması yapar — bağımlılık önceden yüklenir.

    addonlar: {'belge': ['sirket', 'cari', 'stok'], 'cari': ['sirket'], ...}
    Döner: ['sirket', 'birim', 'cari', 'stok', 'belge', ...]
    """
    ziyaret_edildi = set()
    sonuc = []

    def ziyaret(ad):
        if ad in ziyaret_edildi:
            return
        ziyaret_edildi.add(ad)
        for bag in addonlar.get(ad, []):
            ziyaret(bag)
        sonuc.append(ad)

    for ad in addonlar:
        ziyaret(ad)

    return sonuc


# ════════════════════════════════════════════════════════════
#  ADDON YÜKLEME
# ════════════════════════════════════════════════════════════

KAYITLI_ADDONLAR = [
    'sirket', 'birim', 'ayarlar',
    'cari', 'stok', 'finans',
    'belge', 'uretim', 'personel',
    'rapor', 'dashboard',
]


def register_addons(app):
    """Tüm addon'ları bağımlılık sırasına göre yükler ve Blueprint'leri kaydeder.

    Her addon için şu adımları gerçekleştirir:
    1. __manifest__.py'den bağımlılıkları okur
    2. Topolojik sıralama yapar (Odoo'nun module graph'ına karşılık)
    3. Her addon'un routes.py'sini import eder ve Blueprint'i app'e kaydeder
    4. Her addon'un listeners.py'si varsa import eder (hook dinleyicileri)
    """
    bagimlilikar_haritasi = {}
    for addon_adi in KAYITLI_ADDONLAR:
        try:
            manifest_mod = importlib.import_module(f'addons.{addon_adi}.__manifest__')
            manifest = getattr(manifest_mod, 'MANIFEST', {})
            bagimlilikar_haritasi[addon_adi] = manifest.get('bagimliliklar', [])
        except ModuleNotFoundError:
            bagimlilikar_haritasi[addon_adi] = []

    siralama = _topolojik_sirala(bagimlilikar_haritasi)

    for addon_adi in siralama:
        if addon_adi not in KAYITLI_ADDONLAR:
            continue
        _addon_yukle(app, addon_adi)


def _addon_yukle(app, addon_adi: str):
    """Tek bir addon'u yükler: Blueprint + hook dinleyicileri."""
    # 1. extend dosyası varsa önce yükle (şema extend'i Blueprint'ten önce olmalı)
    try:
        importlib.import_module(f'addons.{addon_adi}.extends')
        logger.debug("addon: %s — extends.py yüklendi", addon_adi)
    except ModuleNotFoundError:
        pass

    # 2. Blueprint kaydı
    try:
        routes_mod = importlib.import_module(f'addons.{addon_adi}.routes')
        bp = getattr(routes_mod, 'bp', None)
        if bp:
            app.register_blueprint(bp)
            logger.info("addon: %s — Blueprint kaydedildi (%s)", addon_adi, bp.url_prefix)
    except ModuleNotFoundError:
        logger.debug("addon: %s — routes.py yok, atlanıyor", addon_adi)

    # 3. Hook dinleyicileri — @on() decorator'lı fonksiyonları kaydetmek için
    try:
        importlib.import_module(f'addons.{addon_adi}.listeners')
        logger.debug("addon: %s — listeners.py yüklendi", addon_adi)
    except ModuleNotFoundError:
        pass

    _yuklenmis_addonlar.append(addon_adi)


def yuklenmis_addonlar() -> List[str]:
    """Yüklenmiş addon listesini döner (sağlık kontrolü / admin paneli için)."""
    return list(_yuklenmis_addonlar)
