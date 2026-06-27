"""addons/stok/views.py — Stok modülü ekran konfigürasyonları"""
from core.views import Alan, FormView, ListeKolon, ListView


def _birim_secenekler():
    def _inner():
        from addons.birim.models import Birim
        return [(str(b.id), f"{b.kod} — {b.ad}") for b in Birim.query.filter_by(aktif=True).all()]
    return _inner


STOK_FORM = FormView(
    baslik='Stok Kartı',
    alanlar=[
        Alan('kod',          'Stok Kodu',    zorunlu=True, genislik=3),
        Alan('tip',          'Tip',          tip='select', zorunlu=True, genislik=3,
             secenekler=[('MALZEME','Malzeme'),('HIZMET','Hizmet')]),
        Alan('ad',           'Stok Adı',     zorunlu=True, genislik=6),
        Alan('birim_id',     'Birim',        tip='select', zorunlu=True, genislik=3,
             secenekler=_birim_secenekler()),
        Alan('kullanim_tipi','Kullanım',     tip='select', genislik=3,
             secenekler=[('SATIS','Satış'),('ALIS','Alış'),('HER_IKISI','Her İkisi')]),
        Alan('kdv_orani',    'KDV %',        tip='number', genislik=2, adim='1',
             varsayilan=20),
        Alan('satis_fiyati', 'Satış Fiyatı', tip='money',  genislik=3, adim='0.0001'),
        Alan('alis_fiyati',  'Alış Fiyatı',  tip='money',  genislik=3, adim='0.0001'),
        Alan('min_stok',     'Min. Stok',    tip='number', genislik=2, adim='0.0001'),
        Alan('barkod_ean13', 'EAN-13',                     genislik=4),
        Alan('barkod_ean8',  'EAN-8',                      genislik=4),
        Alan('aciklama',     'Açıklama',     tip='textarea',genislik=12),
    ],
    submit_etiket='Kaydet',
)

STOK_LISTE = ListView(
    baslik='Stok Kartları',
    kolonlar=[
        ListeKolon('kod',          'Kod',          genislik='80px'),
        ListeKolon('ad',           'Stok Adı'),
        ListeKolon('tip',          'Tip',          genislik='90px'),
        ListeKolon('satis_fiyati', 'Satış Fiyatı', para_birimi=True, genislik='110px'),
        ListeKolon('kdv_orani',    'KDV %',        genislik='70px'),
    ],
    yeni_etiket='Yeni Stok Kartı',
    arama_alanlari=['kod', 'ad', 'barkod_ean13'],
    filtreler=[
        {'ad': 'tip', 'etiket': 'Tip',
         'secenekler': [('MALZEME','Malzeme'),('HIZMET','Hizmet')]},
    ],
)
