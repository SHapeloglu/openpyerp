"""
core/views.py — Generic form/liste/detay konfigürasyon sistemi

FELSEFE:
    Odoo'da her model için XML view yazılır:
        <form string="Fatura">
            <field name="belge_no"/>
            <field name="tarih"/>
        </form>

    ERPNext'te Doctype JSON'ı aynı işi yapar.

    OpenPyERP'te saf Python dict — daha az syntax, IDE desteği tam,
    import edilebilir, test edilebilir:

        from core.views import Alan, FormView

        FATURA_FORM = FormView(
            baslik='Fatura',
            alanlar=[
                Alan('belge_no', 'Belge No', readonly=True),
                Alan('tarih',    'Tarih',    tip='date'),
            ]
        )

    Template bu konfigürasyonu okur ve formu otomatik oluşturur.
    YENİ MODÜL = sadece views.py yaz, template'e dokunma.

ALAN TİPLERİ:
    text     → <input type="text">
    number   → <input type="number">
    date     → <input type="date">
    select   → <select> (secenekler: list veya callable)
    textarea → <textarea>
    hidden   → <input type="hidden">
    readonly → <span> (değiştirilemeyen alan)
    money    → sağa hizalı number, 2 ondalık
    satir    → belge satır tablosu (özel bileşen)
"""
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Union


@dataclass
class Alan:
    """Tek bir form alanının tam konfigürasyonu."""
    ad: str                          # model attribute adı
    etiket: str                      # kullanıcıya gösterilen ad
    tip: str = 'text'                # text|number|date|select|textarea|hidden|readonly|money|satir
    zorunlu: bool = False
    readonly: bool = False
    placeholder: str = ''
    yardim: str = ''                 # form-text açıklaması
    genislik: int = 6                # Bootstrap col-md-{genislik} (1-12)
    secenekler: Any = None           # select için: [('deger','etiket')] veya callable
    varsayilan: Any = None
    gizle_kosul: str = ''            # JS expression — koşul true ise alanı gizle
    para_birimi: str = 'TRY'        # money tipi için
    adim: str = '0.01'              # number/money için step


@dataclass
class SatirAlani:
    """Belge satır tablosundaki tek kolon konfigürasyonu."""
    ad: str
    etiket: str
    tip: str = 'text'               # text|number|select|readonly|money
    genislik: str = 'auto'          # px veya 'auto'
    secenekler: Any = None
    adim: str = '0.01'
    zorunlu: bool = False


@dataclass
class FormView:
    """Bir modülün form ekranı konfigürasyonu."""
    baslik: str
    alanlar: List[Alan] = field(default_factory=list)
    satir_alanlari: List[SatirAlani] = field(default_factory=list)
    cok_satirli: bool = False        # True → satır tablosu göster (belge formu)
    submit_etiket: str = 'Kaydet'
    iptal_url: str = ''


@dataclass
class ListeKolon:
    """Liste ekranındaki tek kolon konfigürasyonu."""
    ad: str                          # template'de {{ belge[ad] }} veya özel
    etiket: str
    siralanable: bool = True
    para_birimi: bool = False
    badge: bool = False              # durum badge'i olarak göster
    tarih: bool = False
    genislik: str = 'auto'
    renderer: Optional[Callable] = None   # özel render fonksiyonu


@dataclass
class ListView:
    """Bir modülün liste ekranı konfigürasyonu."""
    baslik: str
    kolonlar: List[ListeKolon] = field(default_factory=list)
    yeni_url: str = ''
    yeni_etiket: str = 'Yeni'
    arama_alanlari: List[str] = field(default_factory=list)  # aranacak alan adları
    filtreler: List[dict] = field(default_factory=list)       # dropdown filtreler
