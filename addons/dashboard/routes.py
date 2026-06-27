"""addons/dashboard/routes.py — Ana ekran özet verileri"""
from flask import Blueprint, render_template
from core.auth import login_gerekli
from core.context import aktif_sirket_al

bp = Blueprint('dashboard', __name__, url_prefix='/dashboard', template_folder='templates')

@bp.route('/')
@bp.route('')
@login_gerekli
def index():
    from addons.belge.models import BelgeBaslik
    from addons.cari.models import CariHareket
    from addons.stok.models import StokKarti
    from core.tipler import BelgeTip, BelgeDurum
    from sqlalchemy import func
    from core.extensions import db
    from datetime import date

    sirket = aktif_sirket_al()
    sid = sirket.id if sirket else None

    bugun = date.today()
    ay_basi = bugun.replace(day=1)

    ozet = {}

    # Bu ay fatura toplamı
    ozet['ay_fatura'] = db.session.query(
        func.coalesce(func.sum(BelgeBaslik.toplam_kdvli), 0)
    ).filter(
        BelgeBaslik.sirket_id == sid,
        BelgeBaslik.belge_tip == BelgeTip.FATURA,
        BelgeBaslik.cari_tip == 'SATIS',
        BelgeBaslik.durum == BelgeDurum.ONAYLANDI,
        BelgeBaslik.tarih >= ay_basi,
    ).scalar() or 0

    # Açık sipariş sayısı
    ozet['acik_siparis'] = BelgeBaslik.query.filter_by(
        sirket_id=sid, belge_tip=BelgeTip.SIPARIS, durum=BelgeDurum.ACIK
    ).count()

    # Aktif stok kartı sayısı
    ozet['stok_kart_sayisi'] = StokKarti.query.filter_by(
        sirket_id=sid, aktif=True
    ).count()

    return render_template('dashboard/index.html', ozet=ozet, sirket=sirket)
