"""addons/cari/views.py — Cari modülü ekran konfigürasyonları"""
from core.views import Alan, FormView, ListeKolon, ListView
from core.tipler import KullaniciRol


def _sehir_secenekler():
    return [
        ('Adana','Adana'),('Ankara','Ankara'),('Antalya','Antalya'),
        ('Bursa','Bursa'),('Diyarbakır','Diyarbakır'),('Eskişehir','Eskişehir'),
        ('Gaziantep','Gaziantep'),('İstanbul','İstanbul'),('İzmir','İzmir'),
        ('Kayseri','Kayseri'),('Kocaeli','Kocaeli'),('Konya','Konya'),
        ('Mersin','Mersin'),('Sakarya','Sakarya'),('Samsun','Samsun'),
        ('Trabzon','Trabzon'),('Diğer','Diğer'),
    ]


CARI_TIP_SECENEKLER = [
    ('ALICI','Alıcı'),('SATICI','Satıcı'),
    ('HER_IKISI','Alıcı + Satıcı'),('PERSONEL','Personel'),
]

CARI_FORM = FormView(
    baslik='Cari Hesap',
    alanlar=[
        Alan('kod',           'Cari Kodu',     zorunlu=True,  genislik=3),
        Alan('tip',           'Cari Tipi',     tip='select',
             secenekler=CARI_TIP_SECENEKLER,  zorunlu=True,  genislik=3),
        Alan('unvan',         'Unvan / Ad',    zorunlu=True,  genislik=6),
        Alan('vergi_no',      'Vergi No',                     genislik=4),
        Alan('vergi_dairesi', 'Vergi Dairesi',                genislik=4),
        Alan('telefon',       'Telefon',                      genislik=4,
             placeholder='0212 000 00 00'),
        Alan('email',         'E-posta',                      genislik=4,
             placeholder='ornek@sirket.com'),
        Alan('sehir',         'Şehir',         tip='select',
             secenekler=_sehir_secenekler,                    genislik=4),
        Alan('website',       'Website',                      genislik=4,
             placeholder='https://'),
        Alan('adres',         'Adres',         tip='textarea',genislik=12),
    ],
    submit_etiket='Kaydet',
)

CARI_LISTE = ListView(
    baslik='Cari Hesaplar',
    kolonlar=[
        ListeKolon('kod',   'Kod',      genislik='80px'),
        ListeKolon('unvan', 'Unvan'),
        ListeKolon('tip',   'Tip',      badge=False, genislik='120px'),
        ListeKolon('telefon','Telefon', genislik='130px'),
        ListeKolon('sehir', 'Şehir',   genislik='100px'),
    ],
    yeni_etiket='Yeni Cari',
    arama_alanlari=['unvan', 'kod', 'vergi_no'],
    filtreler=[
        {'ad': 'tip', 'etiket': 'Tip', 'secenekler': CARI_TIP_SECENEKLER},
    ],
)
