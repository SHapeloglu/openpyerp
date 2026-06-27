"""
addons/birim/services.py — Birim çevirme domain servisi

birim_donustur() ve birim_cevirme_bul(): eski app.py'deki global fonksiyonların
taşınmış hali. SAF DOMAIN MANTIĞI — sadece Birim/BirimDonusum modellerini
sorgular, hiçbir HTTP/session bağımlılığı yoktur.

Çevrim önceliği (README'de belirtilen, davranış korunmuştur):
    1. Aynı birim → 1.0
    2. BirimDonusum tablosunda açık kayıt
    3. Ters yön açık kayıt (1 / carpan)
    4. Aynı grup, katsayi üzerinden otomatik hesap
"""
from addons.birim.models import Birim, BirimDonusum


def birim_cevirme_bul(kaynak_id, hedef_id):
    """kaynak-hedef çevrim katsayısını döner. Bulunamazsa None.

    Öncelik: BirimDonusum tablosundaki açık kayıt > ters yön kayıt > grup katsayısı.
    """
    if kaynak_id == hedef_id:
        return 1.0

    d = BirimDonusum.query.filter_by(
        kaynak_birim_id=kaynak_id, hedef_birim_id=hedef_id, aktif=True
    ).first()
    if d:
        return float(d.carpan)

    d = BirimDonusum.query.filter_by(
        kaynak_birim_id=hedef_id, hedef_birim_id=kaynak_id, aktif=True
    ).first()
    if d and float(d.carpan) != 0:
        return 1.0 / float(d.carpan)

    kaynak = Birim.query.get(kaynak_id)
    hedef = Birim.query.get(hedef_id)
    if kaynak and hedef and kaynak.grup_id == hedef.grup_id:
        return kaynak.cevirme_katsayisi(hedef)

    return None


def birim_donustur(miktar, kaynak_birim_id, hedef_birim_id):
    """Verilen miktarı kaynak birimden hedef birime çevirir.

    Dönüşüm bulunamazsa None döner. Örn: 500 gr → kg = 500 * 0.001 = 0.5 kg
    """
    if kaynak_birim_id == hedef_birim_id:
        return float(miktar)

    d = BirimDonusum.query.filter_by(
        kaynak_birim_id=kaynak_birim_id, hedef_birim_id=hedef_birim_id, aktif=True
    ).first()
    if d:
        return float(miktar) * float(d.carpan)

    d = BirimDonusum.query.filter_by(
        kaynak_birim_id=hedef_birim_id, hedef_birim_id=kaynak_birim_id, aktif=True
    ).first()
    if d and float(d.carpan) != 0:
        return float(miktar) / float(d.carpan)

    kaynak = Birim.query.get(kaynak_birim_id)
    hedef = Birim.query.get(hedef_birim_id)
    if kaynak and hedef and kaynak.grup_id == hedef.grup_id:
        katsayi = kaynak.cevirme_katsayisi(hedef)
        if katsayi is not None:
            return float(miktar) * katsayi

    return None
