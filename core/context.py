"""
core/context.py — İstek bağlamı (request context) yardımcıları

Bu fonksiyonlar saf iş mantığı DEĞİLDİR — Flask `session`'ına bağımlıdır,
yani sadece bir HTTP isteği sırasında anlamlıdır. Bu yüzden bilinçli olarak
core/services/ klasörüne değil buraya konuldu: domain servisleri test
edilirken Flask request/session mock'lamak zorunda kalınmasın.

Kullanım kalıbı:
    routes.py  -> core.context'ten aktif şirketi okur, domain servisine
                  sirket_id parametresi olarak GEÇİRİR.
    services.py -> session'ı asla bilmez, sadece sirket_id (int) alır.

Bu ayrım, eski app.py'de servis benzeri fonksiyonların (örn. sirketli_cariler)
ortasında `from flask import session` yapmasını önler — o pattern, fonksiyonu
HTTP isteği dışında (örneğin bir CLI script veya testte) çağrılamaz hale
getiriyordu.
"""
from flask import session

from core.extensions import db
from addons.sirket.models import Sirket
from addons.cari.models import Cari
from addons.stok.models import StokKarti


def aktif_sirket_al():
    """Session'dan aktif şirketi döner; yoksa ilk aktif şirketi seçer ve session'a yazar."""
    sid = session.get('sirket_id')
    if sid:
        s = db.session.get(Sirket, sid)
        if s and s.aktif:
            return s
    s = Sirket.query.filter_by(aktif=True).first()
    if s:
        session['sirket_id'] = s.id
    return s


def aktif_sirket_id():
    """Sadece id döner — servis katmanına geçirilecek değer genelde bu olmalı."""
    s = aktif_sirket_al()
    return s.id if s else None


def sirketli_stoklar(sadece_aktif=True):
    """Aktif şirkete göre filtrelenmiş StokKarti sorgusu döner."""
    sirket = aktif_sirket_al()
    q = StokKarti.query
    if sadece_aktif:
        q = q.filter_by(aktif=True)
    if sirket:
        q = q.filter_by(sirket_id=sirket.id)
    return q


def sirketli_cariler(sadece_aktif=True, tip=None):
    """Aktif şirkete göre filtrelenmiş Cari sorgusu döner."""
    sirket = aktif_sirket_al()
    q = Cari.query
    if sadece_aktif:
        q = q.filter_by(aktif=True)
    if sirket:
        q = q.filter_by(sirket_id=sirket.id)
    if tip:
        if isinstance(tip, list):
            q = q.filter(Cari.tip.in_(tip))
        else:
            q = q.filter_by(tip=tip)
    return q
