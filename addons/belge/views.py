"""
addons/belge/views.py — Belge modülü ekran konfigürasyonları

YENİ MODÜL EKLEMEKTEKİ FARK:
    Eski CariMatik'te her belge tipi için ayrı route + ayrı template
    yazılırdı. Burada TÜM belge tipleri (TALEP, SİPARİŞ, İRSALİYE,
    FATURA) için tek bir _form.html ve _liste.html çalışır.
    Fark sadece bu dosyadaki konfigürasyondan kaynaklanır.
"""
from core.views import Alan, SatirAlani, FormView, ListeKolon, ListView
from core.tipler import BelgeTip, CariTip, BelgeDurum


def _cari_secenekler(cari_tip='SATIS'):
    """Seçenek listesi runtime'da DB'den okunur (lazy callable)."""
    def _inner():
        from addons.cari.models import Cari
        from core.context import aktif_sirket_id
        tip = 'ALICI' if cari_tip == 'SATIS' else 'SATICI'
        return [
            (str(c.id), c.unvan)
            for c in Cari.query.filter_by(
                aktif=True, sirket_id=aktif_sirket_id(), tip=tip
            ).order_by(Cari.unvan).all()
        ]
    return _inner


def _depo_secenekler():
    def _inner():
        from addons.sirket.models import Depo
        from core.context import aktif_sirket_id
        return [
            (str(d.id), d.ad)
            for d in Depo.query.filter_by(
                aktif=True, sirket_id=aktif_sirket_id()
            ).all()
        ]
    return _inner


def _stok_secenekler():
    def _inner():
        from addons.stok.models import StokKarti
        from core.context import aktif_sirket_id
        return [
            (str(s.id), f"{s.kod} — {s.ad}")
            for s in StokKarti.query.filter_by(
                aktif=True, sirket_id=aktif_sirket_id()
            ).order_by(StokKarti.ad).all()
        ]
    return _inner


def _birim_secenekler():
    def _inner():
        from addons.birim.models import Birim
        return [(str(b.id), b.ad) for b in Birim.query.filter_by(aktif=True).all()]
    return _inner


def _durum_secenekler():
    return [(d, d) for d in BelgeDurum.TUMU]


# ════════════════════════════════════════════════════════════
#  FORM VIEWS — her belge tipi için
# ════════════════════════════════════════════════════════════

def belge_form_view(belge_tip: str, cari_tip: str = 'SATIS') -> FormView:
    """Belge tipine göre dinamik FormView döner.

    Tek template (_form.html), ama:
    - FATURA → cari zorunlu, vade tarihi var, satır tablosu var
    - TALEP  → cari opsiyonel, vade yok
    - İRSALİYE → evrak no var (sipariş no referansı)
    """
    tip_adi = BelgeTip.ADLAR.get(belge_tip, belge_tip)
    cari_adi = 'Müşteri' if cari_tip == 'SATIS' else 'Tedarikçi'

    temel_alanlar = [
        Alan('belge_tip', 'Belge Tipi', tip='hidden', varsayilan=belge_tip),
        Alan('cari_tip',  'Cari Tipi',  tip='hidden', varsayilan=cari_tip),

        Alan('belge_no', 'Belge No', readonly=True, genislik=4,
             yardim='Otomatik oluşturulur'),
        Alan('tarih', 'Tarih', tip='date', zorunlu=True, genislik=4),
        Alan('durum', 'Durum', tip='hidden', varsayilan=BelgeDurum.ACIK),
    ]

    # Cari — faturada zorunlu, diğerlerinde opsiyonel
    temel_alanlar.append(
        Alan('cari_id', cari_adi,
             tip='select',
             secenekler=_cari_secenekler(cari_tip),
             zorunlu=(belge_tip == BelgeTip.FATURA),
             genislik=8)
    )

    # Vade tarihi — sadece faturada
    if belge_tip == BelgeTip.FATURA:
        temel_alanlar.append(
            Alan('vade_tarihi', 'Vade Tarihi', tip='date', genislik=4)
        )

    # Evrak no — irsaliye ve faturada (referans belge)
    if belge_tip in (BelgeTip.IRSALIYE, BelgeTip.FATURA):
        temel_alanlar.append(
            Alan('evrak_no', 'Evrak / Ref No', genislik=4,
                 placeholder='İlgili belge numarası')
        )

    temel_alanlar += [
        Alan('depo_id', 'Depo', tip='select',
             secenekler=_depo_secenekler(), genislik=4),
        Alan('aciklama', 'Açıklama', tip='textarea', genislik=12),
    ]

    # Satır kolonları
    satir_alanlari = [
        SatirAlani('stok_id',     'Stok / Hizmet', tip='select',
                   secenekler=_stok_secenekler(), genislik='200px'),
        SatirAlani('aciklama',    'Açıklama',       tip='text',   genislik='150px'),
        SatirAlani('miktar',      'Miktar',          tip='number', genislik='80px',  adim='0.0001'),
        SatirAlani('birim_id',    'Birim',           tip='select',
                   secenekler=_birim_secenekler(), genislik='80px'),
        SatirAlani('birim_fiyat', 'Birim Fiyat',    tip='money',  genislik='100px', adim='0.0001'),
        SatirAlani('iskonto_oran','İsk %',           tip='number', genislik='60px',  adim='0.01'),
        SatirAlani('kdv_orani',   'KDV %',           tip='number', genislik='60px',  adim='0.01'),
        SatirAlani('donusum_carpan', 'Çarpan', tip='hidden', genislik='0'),
    ]

    return FormView(
        baslik=f"{tip_adi} {'Satışı' if cari_tip == 'SATIS' else 'Alışı'}",
        alanlar=temel_alanlar,
        satir_alanlari=satir_alanlari,
        cok_satirli=True,
        submit_etiket='Kaydet',
        iptal_url='',  # routes.py dolduracak
    )


# ════════════════════════════════════════════════════════════
#  LIST VIEWS — her belge tipi için
# ════════════════════════════════════════════════════════════

def belge_liste_view(belge_tip: str, cari_tip: str = 'SATIS') -> ListView:
    tip_adi = BelgeTip.ADLAR.get(belge_tip, belge_tip)
    return ListView(
        baslik=f"{tip_adi} Listesi",
        kolonlar=[
            ListeKolon('belge_no',      'Belge No',     genislik='120px'),
            ListeKolon('tarih',         'Tarih',         tarih=True, genislik='100px'),
            ListeKolon('vade_tarihi',   'Vade',          tarih=True, genislik='100px'),
            ListeKolon('cari',          'Cari',          siralanable=False,
                       renderer=lambda k: k.cari.unvan if k.cari else '—'),
            ListeKolon('toplam_kdvli',  'Toplam',        para_birimi=True, genislik='120px'),
            ListeKolon('durum',         'Durum',         badge=True, genislik='100px'),
        ],
        yeni_url='',  # routes.py dolduracak
        yeni_etiket=f'Yeni {tip_adi}',
        arama_alanlari=['belge_no', 'cari'],
        filtreler=[
            {'ad': 'durum', 'etiket': 'Durum', 'secenekler': [
                (BelgeDurum.TASLAK,    'Taslak'),
                (BelgeDurum.ACIK,      'Açık'),
                (BelgeDurum.ONAYLANDI, 'Onaylandı'),
                (BelgeDurum.IPTAL,     'İptal'),
            ]},
        ],
    )
