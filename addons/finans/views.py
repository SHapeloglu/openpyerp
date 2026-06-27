"""addons/finans/views.py — Kasa ve Banka ekran konfigürasyonları"""
from core.views import Alan, FormView, ListeKolon, ListView

PARA_BIRIMI_SECENEKLER = [('TRY','₺ TRY'),('USD','$ USD'),('EUR','€ EUR'),('GBP','£ GBP')]
HAREKET_TIP_SECENEKLER = [('GIRIS','Giriş'),('CIKIS','Çıkış')]


def _cari_secenekler():
    def _inner():
        from addons.cari.models import Cari
        from core.context import aktif_sirket_id
        return [(str(c.id), c.unvan) for c in
                Cari.query.filter_by(aktif=True, sirket_id=aktif_sirket_id())
                          .order_by(Cari.unvan).all()]
    return _inner


def _kasa_secenekler():
    def _inner():
        from addons.finans.models import Kasa
        from core.context import aktif_sirket_id
        return [(str(k.id), k.ad) for k in
                Kasa.query.filter_by(aktif=True, sirket_id=aktif_sirket_id()).all()]
    return _inner


def _banka_secenekler():
    def _inner():
        from addons.finans.models import Banka
        from core.context import aktif_sirket_id
        return [(str(b.id), b.banka_adi) for b in
                Banka.query.filter_by(aktif=True, sirket_id=aktif_sirket_id()).all()]
    return _inner


# ── Kasa ──────────────────────────────────────────────────────────────────
KASA_FORM = FormView(
    baslik='Kasa',
    alanlar=[
        Alan('kod',          'Kasa Kodu',    zorunlu=True, genislik=3),
        Alan('ad',           'Kasa Adı',     zorunlu=True, genislik=5),
        Alan('para_birimi',  'Para Birimi',  tip='select',
             secenekler=PARA_BIRIMI_SECENEKLER, genislik=4),
    ],
    submit_etiket='Kaydet',
)

KASA_HAREKET_FORM = FormView(
    baslik='Kasa Hareketi',
    alanlar=[
        Alan('kasa_id',      'Kasa',         tip='select',
             secenekler=_kasa_secenekler,    zorunlu=True, genislik=4),
        Alan('tarih',        'Tarih',        tip='date',   zorunlu=True, genislik=3),
        Alan('belge_no',     'Belge No',                   genislik=3),
        Alan('hareket_tipi', 'Hareket Tipi', tip='select',
             secenekler=HAREKET_TIP_SECENEKLER, zorunlu=True, genislik=3),
        Alan('tutar',        'Tutar',        tip='money',  zorunlu=True, genislik=3),
        Alan('cari_id',      'Cari',         tip='select',
             secenekler=_cari_secenekler,                  genislik=6),
        Alan('aciklama',     'Açıklama',     tip='textarea', genislik=12),
    ],
    submit_etiket='Kaydet',
)

KASA_LISTE = ListView(
    baslik='Kasalar',
    kolonlar=[
        ListeKolon('kod', 'Kod',   genislik='80px'),
        ListeKolon('ad',  'Kasa Adı'),
        ListeKolon('para_birimi', 'Para Birimi', genislik='100px'),
    ],
    yeni_etiket='Yeni Kasa',
)

KASA_HAREKET_LISTE = ListView(
    baslik='Kasa Hareketleri',
    kolonlar=[
        ListeKolon('tarih',        'Tarih',    tarih=True,      genislik='100px'),
        ListeKolon('belge_no',     'Belge No',                  genislik='120px'),
        ListeKolon('hareket_tipi', 'Tip',      badge=False,     genislik='80px'),
        ListeKolon('tutar',        'Tutar',    para_birimi=True,genislik='120px'),
        ListeKolon('aciklama',     'Açıklama'),
    ],
    yeni_etiket='Yeni Hareket',
    filtreler=[
        {'ad': 'hareket_tipi', 'etiket': 'Tip',
         'secenekler': HAREKET_TIP_SECENEKLER},
    ],
)

# ── Banka ─────────────────────────────────────────────────────────────────
BANKA_FORM = FormView(
    baslik='Banka Hesabı',
    alanlar=[
        Alan('banka_adi',   'Banka Adı',    zorunlu=True, genislik=5),
        Alan('sube_adi',    'Şube',                       genislik=4),
        Alan('para_birimi', 'Para Birimi',  tip='select',
             secenekler=PARA_BIRIMI_SECENEKLER,           genislik=3),
        Alan('iban',        'IBAN',                       genislik=6,
             placeholder='TR00 0000 0000 0000 0000 0000 00'),
        Alan('hesap_no',    'Hesap No',                   genislik=6),
    ],
    submit_etiket='Kaydet',
)

BANKA_HAREKET_FORM = FormView(
    baslik='Banka Hareketi',
    alanlar=[
        Alan('banka_id',     'Banka',        tip='select',
             secenekler=_banka_secenekler,   zorunlu=True, genislik=4),
        Alan('tarih',        'Tarih',        tip='date',   zorunlu=True, genislik=3),
        Alan('belge_no',     'Belge No',                   genislik=3),
        Alan('hareket_tipi', 'Hareket Tipi', tip='select',
             secenekler=HAREKET_TIP_SECENEKLER, zorunlu=True, genislik=3),
        Alan('tutar',        'Tutar',        tip='money',  zorunlu=True, genislik=3),
        Alan('cari_id',      'Cari',         tip='select',
             secenekler=_cari_secenekler,                  genislik=6),
        Alan('aciklama',     'Açıklama',     tip='textarea', genislik=12),
    ],
    submit_etiket='Kaydet',
)

BANKA_LISTE = ListView(
    baslik='Banka Hesapları',
    kolonlar=[
        ListeKolon('banka_adi',   'Banka'),
        ListeKolon('sube_adi',    'Şube',        genislik='150px'),
        ListeKolon('iban',        'IBAN',         genislik='250px'),
        ListeKolon('para_birimi', 'Para Birimi',  genislik='100px'),
    ],
    yeni_etiket='Yeni Banka Hesabı',
)
