"""addons/personel/views.py — Personel ekran konfigürasyonları"""
from core.views import Alan, FormView, ListeKolon, ListView

IZIN_TIP_SECENEKLER = [
    ('YILLIK','Yıllık İzin'), ('HASTALIK','Hastalık İzni'),
    ('UCRETSIZ','Ücretsiz İzin'), ('MAZERET','Mazeret İzni'),
    ('DIGER','Diğer'),
]

PERSONEL_FORM = FormView(
    baslik='Personel',
    alanlar=[
        Alan('sicil_no', 'Sicil No',   zorunlu=True, genislik=3),
        Alan('ad',       'Ad',         zorunlu=True, genislik=4),
        Alan('soyad',    'Soyad',      zorunlu=True, genislik=5),
        Alan('tc_kimlik','TC Kimlik',               genislik=4,
             placeholder='11 haneli TC kimlik numarası'),
        Alan('ise_giris','İşe Giriş',  tip='date', zorunlu=True, genislik=4),
        Alan('isten_cikis','İşten Çıkış', tip='date',            genislik=4),
    ],
    submit_etiket='Kaydet',
)

IZIN_FORM = FormView(
    baslik='İzin Talebi',
    alanlar=[
        Alan('izin_tipi',  'İzin Tipi',  tip='select',
             secenekler=IZIN_TIP_SECENEKLER, zorunlu=True, genislik=4),
        Alan('baslangic',  'Başlangıç',  tip='date', zorunlu=True, genislik=4),
        Alan('bitis',      'Bitiş',      tip='date', zorunlu=True, genislik=4),
        Alan('gun_sayisi', 'Gün Sayısı', tip='number', zorunlu=True, genislik=3, adim='1'),
        Alan('aciklama',   'Açıklama',   tip='textarea', genislik=12),
    ],
    submit_etiket='Talep Gönder',
)

PERSONEL_LISTE = ListView(
    baslik='Personel',
    kolonlar=[
        ListeKolon('sicil_no', 'Sicil',   genislik='80px'),
        ListeKolon('ad',       'Ad',      genislik='120px'),
        ListeKolon('soyad',    'Soyad',   genislik='120px'),
        ListeKolon('ise_giris','İşe Giriş', tarih=True, genislik='110px'),
    ],
    yeni_etiket='Yeni Personel',
    arama_alanlari=['ad', 'soyad', 'sicil_no'],
)
