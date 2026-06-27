"""addons/rapor/routes.py — Raporlar HTTP katmanı"""
from datetime import date, timedelta
from flask import Blueprint, render_template, request
from sqlalchemy import func, case
from core.auth import login_gerekli
from core.context import aktif_sirket_al
from core.extensions import db
from core.tipler import BelgeTip, BelgeDurum, CariTip
from addons.belge.models import BelgeBaslik
from addons.cari.models import Cari, CariHareket
from addons.stok.models import StokKarti, StokHareket

bp = Blueprint('rapor', __name__, url_prefix='/rapor', template_folder='templates')


def _tarih_aralik():
    """Request'ten başlangıç/bitiş tarihi okur, varsayılan: bu ay."""
    bugun = date.today()
    baslangic_str = request.args.get('baslangic')
    bitis_str     = request.args.get('bitis')
    baslangic = date.fromisoformat(baslangic_str) if baslangic_str \
        else bugun.replace(day=1)
    bitis = date.fromisoformat(bitis_str) if bitis_str else bugun
    return baslangic, bitis


@bp.route('/')
@login_gerekli
def rapor_ana():
    return render_template('rapor/ana.html')


@bp.route('/gelir-gider')
@login_gerekli
def gelir_gider():
    """Onaylı satış/alış faturalarını aylık olarak özetler."""
    sirket = aktif_sirket_al()
    sid = sirket.id if sirket else None
    baslangic, bitis = _tarih_aralik()

    satis = db.session.query(
        func.coalesce(func.sum(BelgeBaslik.toplam_kdvli), 0)
    ).filter(
        BelgeBaslik.sirket_id == sid,
        BelgeBaslik.belge_tip == BelgeTip.FATURA,
        BelgeBaslik.cari_tip  == CariTip.SATIS,
        BelgeBaslik.durum     == BelgeDurum.ONAYLANDI,
        BelgeBaslik.tarih.between(baslangic, bitis),
    ).scalar() or 0

    alis = db.session.query(
        func.coalesce(func.sum(BelgeBaslik.toplam_kdvli), 0)
    ).filter(
        BelgeBaslik.sirket_id == sid,
        BelgeBaslik.belge_tip == BelgeTip.FATURA,
        BelgeBaslik.cari_tip  == CariTip.ALIS,
        BelgeBaslik.durum     == BelgeDurum.ONAYLANDI,
        BelgeBaslik.tarih.between(baslangic, bitis),
    ).scalar() or 0

    # Aylık detay
    aylik = db.session.query(
        func.year(BelgeBaslik.tarih).label('yil'),
        func.month(BelgeBaslik.tarih).label('ay'),
        BelgeBaslik.cari_tip,
        func.sum(BelgeBaslik.toplam_kdvli).label('toplam'),
    ).filter(
        BelgeBaslik.sirket_id == sid,
        BelgeBaslik.belge_tip == BelgeTip.FATURA,
        BelgeBaslik.durum     == BelgeDurum.ONAYLANDI,
        BelgeBaslik.tarih.between(baslangic, bitis),
    ).group_by('yil', 'ay', BelgeBaslik.cari_tip)\
     .order_by('yil', 'ay').all()

    return render_template('rapor/gelir_gider.html',
                           satis=float(satis), alis=float(alis),
                           kar=float(satis) - float(alis),
                           aylik=aylik,
                           baslangic=baslangic, bitis=bitis)


@bp.route('/cari-bakiye')
@login_gerekli
def cari_bakiye():
    """Tüm carilerin bakiyesini tek sorguda hesaplar."""
    sirket = aktif_sirket_al()
    sid = sirket.id if sirket else None
    tip = request.args.get('tip')

    q = Cari.query.filter_by(aktif=True, sirket_id=sid)
    if tip:
        q = q.filter_by(tip=tip)
    cariler = q.order_by(Cari.unvan).all()

    from addons.cari.services import toplu_cari_bakiyeleri
    bakiyeler = toplu_cari_bakiyeleri([c.id for c in cariler])

    # Sadece bakiyesi sıfır olmayanları göster
    sadece_bakiyeli = request.args.get('sadece_bakiyeli') == '1'
    if sadece_bakiyeli:
        cariler = [c for c in cariler if abs(bakiyeler.get(c.id, 0)) > 0.001]

    return render_template('rapor/cari_bakiye.html',
                           cariler=cariler, bakiyeler=bakiyeler,
                           tip=tip, sadece_bakiyeli=sadece_bakiyeli)


@bp.route('/vade-analizi')
@login_gerekli
def vade_analizi():
    """Vadesi geçmiş / yaklaşan faturaları gruplar."""
    sirket = aktif_sirket_al()
    sid = sirket.id if sirket else None
    bugun = date.today()

    bekleyen = BelgeBaslik.query.filter(
        BelgeBaslik.sirket_id == sid,
        BelgeBaslik.belge_tip == BelgeTip.FATURA,
        BelgeBaslik.cari_tip  == CariTip.SATIS,
        BelgeBaslik.durum     == BelgeDurum.ONAYLANDI,
        BelgeBaslik.vade_tarihi.isnot(None),
    ).order_by(BelgeBaslik.vade_tarihi).all()

    gecmis, bu_hafta, gelecek = [], [], []
    for b in bekleyen:
        fark = (b.vade_tarihi - bugun).days
        if fark < 0:
            gecmis.append((b, abs(fark)))
        elif fark <= 7:
            bu_hafta.append((b, fark))
        else:
            gelecek.append((b, fark))

    return render_template('rapor/vade_analizi.html',
                           gecmis=gecmis, bu_hafta=bu_hafta,
                           gelecek=gelecek, bugun=bugun)


@bp.route('/stok-durumu')
@login_gerekli
def stok_durumu():
    """Stok kartlarını mevcut miktarlarıyla listeler, min stok uyarısı gösterir."""
    sirket = aktif_sirket_al()
    sid = sirket.id if sirket else None

    stoklar = StokKarti.query.filter_by(
        aktif=True, sirket_id=sid, tip='MALZEME'
    ).order_by(StokKarti.ad).all()

    from addons.stok.services import toplu_stok_miktarlari
    miktarlar = toplu_stok_miktarlari([s.id for s in stoklar])

    uyari_listesi = [
        s for s in stoklar
        if s.min_stok and miktarlar.get(s.id, 0) < float(s.min_stok)
    ]

    return render_template('rapor/stok_durumu.html',
                           stoklar=stoklar, miktarlar=miktarlar,
                           uyari_listesi=uyari_listesi)
