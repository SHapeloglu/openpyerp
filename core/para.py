"""
core/para.py — Parasal ve miktar hassasiyeti yardımcıları

SAF DOMAIN MANTIĞI: Flask, SQLAlchemy ya da herhangi bir framework'e bağımlı
değildir. Bu yüzden hiçbir import'u core.extensions veya addons.* içermez.
Bu dosya, unit test ile Flask app context'i kurmadan doğrudan test edilebilir
— örn: `assert para(10.005) == Decimal('10.01')` gibi bir testte sunucu
ayağa kaldırmaya gerek yoktur.

Eski app.py'deki para()/miktar_d() fonksiyonlarının taşınmış hali — davranış
birebir korunmuştur (ROUND_HALF_UP, aynı hassasiyetler).
"""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation


def para(deger, hassasiyet='0.01') -> Decimal:
    """Değeri Decimal'e çevirip parasal hassasiyette yuvarlar.

    Muhasebe hesaplamalarında float yerine bu kullanılmalıdır — float'ın
    ikili (binary) temsili kuruş hatalarına yol açabilir (örn. 0.1 + 0.2 != 0.3).
    """
    try:
        if deger is None:
            return Decimal('0')
        return Decimal(str(deger)).quantize(Decimal(hassasiyet), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return Decimal('0')


def miktar_d(deger) -> Decimal:
    """Miktar değerini Decimal'e çevirir (6 hane hassasiyet — birim dönüşümü için)."""
    try:
        if deger is None:
            return Decimal('0')
        return Decimal(str(deger)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return Decimal('0')
