"""
addons/eticaret/extends.py — StokKarti'ye e-ticaret alanlarını ekler

BU DOSYA "base form extend" MANTIĞININ SOMUT ÖRNEĞİDİR.

Odoo'da şöyle yazılır:
    class ProductTemplate(models.Model):
        _inherit = 'product.template'
        woo_id = fields.Integer('WooCommerce ID')
        trendyol_barkod = fields.Char('Trendyol Barkod')

OpenPyERP'te:
    1. Bu dosyada mixin tanımla + extend_model() çağır (Python tarafı)
    2. migrations/ altında Alembic dosyası yaz (DB tarafı)

SONUÇ: addons/stok/models.py'e tek satır dokunulmaz. E-ticaret addon'u
devre dışı bırakıldığında (KAYITLI_ADDONLAR'dan çıkarıldığında) bu
alanlar otomatik olarak yüklenmez — stok modülü bunlardan haberdar bile olmaz.
"""
from core.extensions import db
from core.registry import extend_model
from addons.stok.models import StokKarti


class StokKartiEticaretMixin:
    """StokKarti'ye e-ticaret platformu alanları ekleyen mixin.

    Bu sınıf doğrudan kullanılmaz — extend_model() tarafından StokKarti'ye
    dinamik olarak eklenir. İleride StokKarti.woo_id, StokKarti.trendyol_barkod
    şeklinde erişilebilir olur.
    """
    woo_id = db.Column(
        db.Integer, nullable=True, index=True,
        comment='WooCommerce ürün ID — platform senkronizasyonu için'
    )
    trendyol_barkod = db.Column(
        db.String(50), nullable=True,
        comment='Trendyol platformuna özgü barkod (EAN13 ile farklı olabilir)'
    )
    eticaret_aktif = db.Column(
        db.Boolean, default=False, server_default='0',
        comment='Bu ürün e-ticaret platformlarında yayınlanıyor mu?'
    )


# ── Extend işlemi: Python mapper'ına yeni alanları bildir ───────────────────
# Bu satır çalıştığında, artık her yerde:
#   stok = StokKarti.query.get(1)
#   stok.woo_id = 12345  # ← çalışır
# DB'de fiziksel kolon için: addons/eticaret/migrations/ altındaki Alembic dosyasını çalıştır.
extend_model(StokKarti, StokKartiEticaretMixin)
