"""addons/uretim/views.py — Üretim fişi ekran konfigürasyonları"""
from core.views import Alan, SatirAlani, FormView, ListeKolon, ListView


def _stok_secenekler(sadece_malzeme=False):
    def _inner():
        from addons.stok.models import StokKarti
        from core.context import aktif_sirket_id
        q = StokKarti.query.filter_by(aktif=True, sirket_id=aktif_sirket_id())
        if sadece_malzeme:
            q = q.filter_by(tip='MALZEME')
        return [(str(s.id), f"{s.kod} — {s.ad}") for s in q.order_by(StokKarti.ad).all()]
    return _inner


def _birim_secenekler():
    def _inner():
        from addons.birim.models import Birim
        return [(str(b.id), b.ad) for b in Birim.query.filter_by(aktif=True).all()]
    return _inner


def _depo_secenekler():
    def _inner():
        from addons.sirket.models import Depo
        from core.context import aktif_sirket_id
        return [(str(d.id), d.ad)
                for d in Depo.query.filter_by(aktif=True, sirket_id=aktif_sirket_id()).all()]
    return _inner


URETIM_FORM = FormView(
    baslik='Üretim Fişi',
    alanlar=[
        Alan('fis_no',            'Fiş No',           readonly=True, genislik=4,
             yardim='Otomatik oluşturulur'),
        Alan('tarih',             'Tarih',             tip='date', zorunlu=True, genislik=4),
        Alan('mamul_stok_id',     'Mamul',             tip='select', zorunlu=True, genislik=8,
             secenekler=_stok_secenekler(sadece_malzeme=True),
             yardim='Üretilecek nihai ürün'),
        Alan('uretilecek_miktar', 'Üretilecek Miktar', tip='number', zorunlu=True,
             genislik=4, adim='0.0001'),
        Alan('depo_id',           'Hedef Depo',        tip='select', genislik=4,
             secenekler=_depo_secenekler),
        Alan('aciklama',          'Açıklama',          tip='textarea', genislik=12),
    ],
    satir_alanlari=[
        SatirAlani('stok_id',  'Hammadde', tip='select',
                   secenekler=_stok_secenekler(), genislik='200px'),
        SatirAlani('miktar',   'Miktar',   tip='number', genislik='90px', adim='0.0001'),
        SatirAlani('birim_id', 'Birim',    tip='select',
                   secenekler=_birim_secenekler, genislik='80px'),
    ],
    cok_satirli=True,
    submit_etiket='Kaydet',
)

URETIM_LISTE = ListView(
    baslik='Üretim Fişleri',
    kolonlar=[
        ListeKolon('fis_no',            'Fiş No',    genislik='120px'),
        ListeKolon('tarih',             'Tarih',     tarih=True, genislik='100px'),
        ListeKolon('uretilecek_miktar', 'Miktar',    genislik='80px'),
        ListeKolon('durum',             'Durum',     badge=True, genislik='110px'),
    ],
    yeni_etiket='Yeni Üretim Fişi',
    filtreler=[
        {'ad': 'durum', 'etiket': 'Durum', 'secenekler': [
            ('TASLAK','Taslak'), ('BASLAMIS','Başlamış'),
            ('TAMAMLANDI','Tamamlandı'), ('IPTAL','İptal'),
        ]},
    ],
)
