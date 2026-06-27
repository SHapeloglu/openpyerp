"""
core/auth.py — Kimlik doğrulama ve yetkilendirme decorator'ları

Eski app.py'deki login_gerekli/admin_gerekli/yazma_gerekli fonksiyonlarının
taşınmış hali. Davranış AYNI — sadece konum değişti. Tüm addon route'ları
artık şu şekilde import eder:

    from core.auth import login_gerekli, admin_gerekli, yazma_gerekli
"""
from functools import wraps
from flask import session, redirect, url_for, flash, request

from addons.ayarlar.models import Kullanici  # noqa: kullanici rolü kontrolü için


def aktif_kullanici_al():
    """Session'daki kullanici_id ile Kullanici nesnesini döner. Oturum yoksa None."""
    uid = session.get('kullanici_id')
    return Kullanici.query.get(uid) if uid else None


def login_gerekli(f):
    """Giriş yapmamış kullanıcıları /giris sayfasına yönlendiren decorator."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('kullanici_id'):
            return redirect(url_for('ayarlar.giris', next=request.path))
        return f(*args, **kwargs)
    return decorated


def admin_gerekli(f):
    """Sadece ADMIN rolündeki kullanıcılara izin verir."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('kullanici_id'):
            return redirect(url_for('ayarlar.giris', next=request.path))
        k = aktif_kullanici_al()
        if not k or k.rol != 'ADMIN':
            flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


def yazma_gerekli(f):
    """SADECE_OKUMA rolündeki kullanıcıları engeller."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('kullanici_id'):
            return redirect(url_for('ayarlar.giris', next=request.path))
        k = aktif_kullanici_al()
        if k and k.rol == 'SADECE_OKUMA':
            flash('Bu işlem için yazma yetkiniz yok.', 'warning')
            return redirect(request.referrer or url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated
