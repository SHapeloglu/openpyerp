"""
addons/cari/services.py — Cari modülü domain servisleri

toplu_cari_bakiyeleri(): eski app.py'deki global fonksiyonun taşınmış hali.
N+1 sorgu sorununu önlemek için birden fazla cari'nin bakiyesini 2 sorguda
hesaplar (liste ekranlarında her satır için ayrı sorgu yapmamak için).
"""
from sqlalchemy import func

from core.extensions import db
from addons.cari.models import CariHareket


def toplu_cari_bakiyeleri(cari_idler):
    """Birden fazla cari için bakiyeyi tek sorguda hesaplar.

    Döner: {cari_id: bakiye}
    """
    if not cari_idler:
        return {}

    borclar = db.session.query(
        CariHareket.cari_id, func.sum(CariHareket.tutar).label('toplam')
    ).filter(
        CariHareket.cari_id.in_(cari_idler), CariHareket.hareket_tipi == 'BORC'
    ).group_by(CariHareket.cari_id).all()

    alacaklar = db.session.query(
        CariHareket.cari_id, func.sum(CariHareket.tutar).label('toplam')
    ).filter(
        CariHareket.cari_id.in_(cari_idler), CariHareket.hareket_tipi == 'ALACAK'
    ).group_by(CariHareket.cari_id).all()

    borc_map = {r.cari_id: float(r.toplam or 0) for r in borclar}
    alacak_map = {r.cari_id: float(r.toplam or 0) for r in alacaklar}

    return {cid: borc_map.get(cid, 0) - alacak_map.get(cid, 0) for cid in cari_idler}


def cari_hareket_olustur(cari_id, tarih, tutar, hareket_tipi, belge_no=None,
                          aciklama=None, kaynak_tip=None, kaynak_id=None):
    """Yeni bir CariHareket kaydı oluşturur (commit YAPMAZ — çağıran transaction'a katar).

    Bu fonksiyon, addons/belge servislerinin "fatura kaydedilince cari hareketi
    oluştur" iş kuralını uygularken çağırdığı tek giriş noktasıdır — ileride
    örn. KDV stopajı gibi ek mantık eklenmek istendiğinde SADECE burası
    değiştirilir, her çağıran modülü tek tek bulmaya gerek kalmaz.
    """
    hareket = CariHareket(
        cari_id=cari_id, tarih=tarih, tutar=tutar, hareket_tipi=hareket_tipi,
        belge_no=belge_no, aciklama=aciklama, kaynak_tip=kaynak_tip, kaynak_id=kaynak_id,
    )
    db.session.add(hareket)
    return hareket


def kaynak_hareketlerini_sil(kaynak_tip, kaynak_id):
    """Belirli bir kaynak belgeye ait tüm cari hareketlerini siler.

    Belge güncellendiğinde (örn. fatura satırları değiştiğinde) eski hareketler
    silinip yeniden oluşturulur — eski app.py'deki
    `CariHareket.query.filter_by(kaynak_tip='FATURA', kaynak_id=baslik.id).delete()`
    deseninin servis katmanına taşınmış hali.
    """
    CariHareket.query.filter_by(kaynak_tip=kaynak_tip, kaynak_id=kaynak_id).delete()
