"""addons/uretim/workflow.py — Üretim fişi durum makinesi

TASLAK → BASLAMIS → TAMAMLANDI → IPTAL

Üretim tamamlandığında:
    - Hammadde stoktan ÇIKIŞ hareketi oluşur
    - Mamul stoka GİRİŞ hareketi oluşur
Bu iki yan etki _action_tamamla içinde, aynı transaction'da gerçekleşir.
"""
from core.workflow import Workflow, Gecis, GuardReddiHatasi
from core.tipler import BelgeDurum


def _guard_baslat(fis, **ctx):
    if not fis.satirlar:
        raise GuardReddiHatasi('Üretim fişinde hammadde satırı yok.', kod='SATIR_EKSIK')


def _action_tamamla(fis, **ctx):
    """Hammadde çıkış + mamul giriş stok hareketleri."""
    from addons.stok.services import stok_hareketi_olustur, negatif_stok_kontrol, YetersizStokHatasi
    from core.workflow import GuardReddiHatasi

    for satir in fis.satirlar:
        cevrilen = float(satir.cevrilen_miktar or satir.miktar)
        if satir.stok.tip == 'MALZEME':
            try:
                negatif_stok_kontrol(satir.stok, cevrilen)
            except YetersizStokHatasi as e:
                raise GuardReddiHatasi(str(e), kod='YETERSIZ_STOK') from e
        stok_hareketi_olustur(
            stok_id=satir.stok_id, tarih=fis.tarih, hareket_tipi='CIKIS',
            miktar=float(satir.miktar), cevrilen_miktar=cevrilen,
            birim_id=satir.birim_id, belge_no=fis.fis_no,
            aciklama=f"Üretim: {fis.fis_no}",
        )
    # Mamul girişi
    stok_hareketi_olustur(
        stok_id=fis.mamul_stok_id, tarih=fis.tarih, hareket_tipi='GIRIS',
        miktar=float(fis.uretilecek_miktar), cevrilen_miktar=float(fis.uretilecek_miktar),
        belge_no=fis.fis_no, aciklama=f"Üretim çıktısı: {fis.fis_no}",
    )
    fis.uretilen_miktar = fis.uretilecek_miktar


def _action_iptal(fis, **ctx):
    from addons.stok.services import kaynak_hareketlerini_sil as stok_sil
    stok_sil(belge_no=fis.fis_no)


URETIM_WF = Workflow(
    durumlar=['TASLAK', 'BASLAMIS', 'TAMAMLANDI', 'IPTAL'],
    gecisler=[
        Gecis('TASLAK',    'BASLAMIS',    isim='Başlat',     guard=_guard_baslat),
        Gecis('BASLAMIS',  'TAMAMLANDI',  isim='Tamamla',    action=_action_tamamla),
        Gecis('BASLAMIS',  'IPTAL',       isim='İptal Et',   action=_action_iptal),
        Gecis('TASLAK',    'IPTAL',       isim='İptal Et'),
    ],
    baslangic='TASLAK',
    durum_alani='durum',
)
