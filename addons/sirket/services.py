"""
addons/sirket/services.py — Şirket modülü domain servisleri

donem_kilitli_mi(): Eski app.py'deki global fonksiyonun taşınmış hali.
Davranış birebir korunmuştur. Artık bir servis fonksiyonu olarak burada
yaşıyor çünkü "dönem kilidi" kontrolü, belge/finans/stok gibi BAŞKA
modüllerin de ihtiyaç duyduğu paylaşılan bir iş kuralı — addons/belge
servisleri bunu import edip kullanır, ama bağımlılık YÖNÜ tektir:
belge -> sirket (asla tersi değil).
"""
from addons.sirket.models import DonemKilidi


def donem_kilitli_mi(sirket_id, tarih) -> bool:
    """Verilen tarihin ait olduğu dönem kilitli mi kontrol eder.

    Kontrol sırası: önce aylık kilit, sonra (aylık kilit yoksa) yıllık kilit.
    """
    if not sirket_id or not tarih:
        return False

    aylik = DonemKilidi.query.filter_by(
        sirket_id=sirket_id, yil=tarih.year, ay=tarih.month, kilitli=True
    ).first()
    if aylik:
        return True

    yillik = DonemKilidi.query.filter_by(
        sirket_id=sirket_id, yil=tarih.year, ay=None, kilitli=True
    ).first()
    return bool(yillik)


def yeni_belge_no(belge_tip: str, cari_tip: str = 'SATIS', sirket_id: int = None) -> str:
    """Belge tipi + cari tipi + yıl kombinasyonuna göre sıradaki belge numarasını üretir.

    NumaraSira kaydı yoksa, modülün varsayılan prefix tablosuna göre otomatik
    oluşturulur (eski app.py'deki yeni_belge_no ile aynı davranış).
    """
    from datetime import date
    from core.extensions import db
    from core.context import aktif_sirket_id
    from addons.sirket.models import NumaraSira

    if sirket_id is None:
        sirket_id = aktif_sirket_id()

    yil = date.today().year
    varsayilan_prefix = {
        'TALEP': 'TLB', 'SIPARIS': 'SIP', 'IRSALIYE': 'IRS', 'FATURA': 'FAT',
        'CARI_FIS': 'CFS', 'BANKA': 'BNK', 'KASA': 'KSA',
        'CEK': 'CEK', 'SENET': 'SEN', 'STOK_FIS': 'SFS', 'URETIM': 'URE',
    }

    sira = NumaraSira.query.filter_by(
        sirket_id=sirket_id, belge_tip=belge_tip, cari_tip=cari_tip, yil=yil
    ).first()

    if not sira:
        sira = NumaraSira(
            sirket_id=sirket_id, belge_tip=belge_tip, cari_tip=cari_tip, yil=yil,
            prefix=varsayilan_prefix.get(belge_tip, belge_tip[:3].upper()),
            son_sayi=0, basamak=6,
        )
        db.session.add(sira)
        db.session.flush()

    return sira.sonraki_no()
