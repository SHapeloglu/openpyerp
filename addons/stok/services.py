"""
addons/stok/services.py — Stok modülü domain servisleri

Bu dosya, eski app.py'de belge_form() route'unun İÇİNE gömülü olan stok
hareketi oluşturma ve negatif stok kontrolü mantığını barındırır. Artık
addons/belge/services.py, bu servisleri ÇAĞIRIR — stok tablosuna doğrudan
yazmaz. Bu, stok hareketi oluşturma kuralının (örn. ileride "depo bazlı
negatif stok izni" gibi bir kural eklenirse) SADECE burada değişmesini sağlar.
"""
from sqlalchemy import func, case

from core.extensions import db
from addons.stok.models import StokKarti, StokHareket


def toplu_stok_miktarlari(stok_idler):
    """Birden fazla stok için cevrilen_miktar'ı tek sorguda hesaplar.

    Döner: {stok_id: miktar}
    """
    if not stok_idler:
        return {}

    girisler = db.session.query(
        StokHareket.stok_id,
        func.sum(case((StokHareket.cevrilen_miktar.isnot(None), StokHareket.cevrilen_miktar),
                       else_=StokHareket.miktar)).label('toplam')
    ).filter(
        StokHareket.stok_id.in_(stok_idler), StokHareket.hareket_tipi == 'GIRIS'
    ).group_by(StokHareket.stok_id).all()

    cikislar = db.session.query(
        StokHareket.stok_id,
        func.sum(case((StokHareket.cevrilen_miktar.isnot(None), StokHareket.cevrilen_miktar),
                       else_=StokHareket.miktar)).label('toplam')
    ).filter(
        StokHareket.stok_id.in_(stok_idler), StokHareket.hareket_tipi == 'CIKIS'
    ).group_by(StokHareket.stok_id).all()

    giris_map = {r.stok_id: float(r.toplam or 0) for r in girisler}
    cikis_map = {r.stok_id: float(r.toplam or 0) for r in cikislar}

    return {sid: giris_map.get(sid, 0) - cikis_map.get(sid, 0) for sid in stok_idler}


class YetersizStokHatasi(Exception):
    """Satış/çıkış hareketinde mevcut stok yetersiz olduğunda fırlatılır.

    Eski app.py'de bu durum doğrudan flash() + redirect() ile ele alınıyordu
    (route fonksiyonunun içinde). Artık servis katmanı sadece bu exception'ı
    fırlatır; HTTP'ye nasıl çevrileceğine (flash mesajı, redirect, JSON hata
    yanıtı) routes.py karar verir. Bu ayrım, aynı kontrolün API tarafında da
    (FastAPI) farklı bir hata formatıyla kullanılabilmesini sağlar.
    """
    def __init__(self, stok_kodu, stok_adi, mevcut, gereken, birim_kod=''):
        self.stok_kodu = stok_kodu
        self.stok_adi = stok_adi
        self.mevcut = mevcut
        self.gereken = gereken
        self.birim_kod = birim_kod
        super().__init__(
            f"Yetersiz stok: {stok_adi} — Mevcut: {mevcut:.4f} {birim_kod}, "
            f"Gereken: {gereken:.4f} {birim_kod}"
        )


def negatif_stok_kontrol(stok: StokKarti, gereken_miktar: float):
    """Bir stok kartının çıkış için yeterli miktarda olup olmadığını kontrol eder.

    Yetersizse YetersizStokHatasi fırlatır. HIZMET tipli kartlar için kontrol
    atlanır (stok takibi yapılmaz).
    """
    if stok.tip == 'HIZMET':
        return
    mevcut = stok.stok_miktari() or 0
    if mevcut < gereken_miktar:
        raise YetersizStokHatasi(
            stok_kodu=stok.kod, stok_adi=stok.ad, mevcut=mevcut,
            gereken=gereken_miktar, birim_kod=stok.birim.kod if stok.birim else '',
        )


def stok_hareketi_olustur(stok_id, tarih, hareket_tipi, miktar, cevrilen_miktar,
                           birim_id=None, birim_fiyat=None, belge_no=None,
                           aciklama=None, depo_id=None):
    """Yeni bir StokHareket kaydı oluşturur (commit YAPMAZ).

    addons/belge ve addons/uretim servislerinin stok hareketi yaratmak için
    çağırdığı TEK giriş noktası — eski app.py'de bu mantık belge_form() ve
    uretim_fisi_onayla_islemi() içinde iki kere ayrı ayrı yazılmıştı.
    """
    hareket = StokHareket(
        stok_id=stok_id, tarih=tarih, hareket_tipi=hareket_tipi,
        miktar=miktar, cevrilen_miktar=cevrilen_miktar, birim_id=birim_id,
        birim_fiyat=birim_fiyat, belge_no=belge_no, aciklama=aciklama, depo_id=depo_id,
    )
    db.session.add(hareket)
    return hareket


def kaynak_hareketlerini_sil(belge_no, stok_id=None):
    """Belirli bir belge numarasına (ve isteğe bağlı stok'a) ait stok hareketlerini siler.

    Belge güncellendiğinde eski hareketler silinip yeniden oluşturulur.
    """
    q = StokHareket.query.filter_by(belge_no=belge_no)
    if stok_id is not None:
        q = q.filter_by(stok_id=stok_id)
    q.delete()
