"""addons/finans/routes.py — Kasa ve Banka HTTP katmanı"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy import func
from core.auth import login_gerekli, yazma_gerekli
from core.context import aktif_sirket_id, aktif_sirket_al
from core.extensions import db
from addons.finans.models import Kasa, KasaHareket, Banka, BankaHareket
from addons.finans.views import (
    KASA_FORM, KASA_HAREKET_FORM, KASA_LISTE, KASA_HAREKET_LISTE,
    BANKA_FORM, BANKA_HAREKET_FORM, BANKA_LISTE,
)

bp = Blueprint('finans', __name__, url_prefix='/finans', template_folder='templates')


def _kasa_bakiye(kasa_id):
    """Kasa bakiyesini giriş - çıkış olarak hesaplar."""
    giris = db.session.query(func.coalesce(func.sum(KasaHareket.tutar), 0))\
                      .filter_by(kasa_id=kasa_id, hareket_tipi='GIRIS').scalar()
    cikis = db.session.query(func.coalesce(func.sum(KasaHareket.tutar), 0))\
                      .filter_by(kasa_id=kasa_id, hareket_tipi='CIKIS').scalar()
    return float(giris) - float(cikis)


def _banka_bakiye(banka_id):
    giris = db.session.query(func.coalesce(func.sum(BankaHareket.tutar), 0))\
                      .filter_by(banka_id=banka_id, hareket_tipi='GIRIS').scalar()
    cikis = db.session.query(func.coalesce(func.sum(BankaHareket.tutar), 0))\
                      .filter_by(banka_id=banka_id, hareket_tipi='CIKIS').scalar()
    return float(giris) - float(cikis)


# ════════════════════════════════════════════════════════════
#  KASA
# ════════════════════════════════════════════════════════════

@bp.route('/kasa')
@login_gerekli
def kasa_liste():
    sirket = aktif_sirket_al()
    kasalar = Kasa.query.filter_by(aktif=True, sirket_id=sirket.id if sirket else None).all()
    bakiyeler = {k.id: _kasa_bakiye(k.id) for k in kasalar}
    liste_v = KASA_LISTE
    liste_v.yeni_url = url_for('finans.kasa_form')

    def detay_url(kayit):
        return url_for('finans.kasa_detay', kasa_id=kayit.id)

    return render_template('_liste.html',
                           satirlar=kasalar, liste_view=liste_v,
                           detay_url=detay_url, bakiyeler=bakiyeler)


@bp.route('/kasa/yeni', methods=['GET', 'POST'])
@bp.route('/kasa/<int:kasa_id>/duzenle', methods=['GET', 'POST'])
@login_gerekli
@yazma_gerekli
def kasa_form(kasa_id=None):
    nesne = db.session.get(Kasa, kasa_id) if kasa_id else None

    if request.method == 'POST':
        if not nesne:
            nesne = Kasa(sirket_id=aktif_sirket_id())
            db.session.add(nesne)
        nesne.kod          = request.form.get('kod', '').strip().upper()
        nesne.ad           = request.form.get('ad', '').strip()
        nesne.para_birimi  = request.form.get('para_birimi', 'TRY')
        try:
            db.session.commit()
            flash(f"Kasa [{nesne.ad}] kaydedildi.", 'success')
            return redirect(url_for('finans.kasa_detay', kasa_id=nesne.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Kayıt hatası: {e}", 'danger')

    return render_template('_form.html',
                           form_view=KASA_FORM, nesne=nesne,
                           form_action=url_for('finans.kasa_form', kasa_id=kasa_id)
                                        if kasa_id else url_for('finans.kasa_form'))


@bp.route('/kasa/<int:kasa_id>')
@login_gerekli
def kasa_detay(kasa_id):
    kasa = db.session.get(Kasa, kasa_id)
    if not kasa:
        flash('Kasa bulunamadı.', 'danger')
        return redirect(url_for('finans.kasa_liste'))
    hareketler = KasaHareket.query.filter_by(kasa_id=kasa_id)\
                     .order_by(KasaHareket.tarih.desc()).limit(100).all()
    bakiye = _kasa_bakiye(kasa_id)
    hareket_liste_v = KASA_HAREKET_LISTE
    hareket_liste_v.yeni_url = url_for('finans.kasa_hareket_form', kasa_id=kasa_id)

    def detay_url(kayit):
        return '#'

    return render_template('finans/kasa_detay.html',
                           kasa=kasa, hareketler=hareketler, bakiye=bakiye,
                           liste_view=hareket_liste_v, detay_url=detay_url)


@bp.route('/kasa/<int:kasa_id>/hareket/yeni', methods=['GET', 'POST'])
@login_gerekli
@yazma_gerekli
def kasa_hareket_form(kasa_id):
    kasa = db.session.get(Kasa, kasa_id)
    if not kasa:
        flash('Kasa bulunamadı.', 'danger')
        return redirect(url_for('finans.kasa_liste'))

    if request.method == 'POST':
        from datetime import date as _date
        try:
            tarih_str = request.form.get('tarih')
            hareket = KasaHareket(
                kasa_id=kasa_id,
                tarih=_date.fromisoformat(tarih_str) if tarih_str else _date.today(),
                belge_no=request.form.get('belge_no', '').strip() or None,
                hareket_tipi=request.form.get('hareket_tipi', 'GIRIS'),
                tutar=float(request.form.get('tutar') or 0),
                cari_id=int(request.form['cari_id']) if request.form.get('cari_id') else None,
                aciklama=request.form.get('aciklama', '').strip() or None,
            )
            db.session.add(hareket)
            db.session.commit()
            flash("Kasa hareketi kaydedildi.", 'success')
            return redirect(url_for('finans.kasa_detay', kasa_id=kasa_id))
        except Exception as e:
            db.session.rollback()
            flash(f"Kayıt hatası: {e}", 'danger')

    # Formu kasa seçili olarak aç
    class _Nesne:
        pass
    nesne = _Nesne()
    nesne.kasa_id = kasa_id

    return render_template('_form.html',
                           form_view=KASA_HAREKET_FORM, nesne=nesne,
                           form_action=url_for('finans.kasa_hareket_form', kasa_id=kasa_id))


# ════════════════════════════════════════════════════════════
#  BANKA
# ════════════════════════════════════════════════════════════

@bp.route('/banka')
@login_gerekli
def banka_liste():
    sirket = aktif_sirket_al()
    bankalar = Banka.query.filter_by(aktif=True, sirket_id=sirket.id if sirket else None).all()
    bakiyeler = {b.id: _banka_bakiye(b.id) for b in bankalar}
    liste_v = BANKA_LISTE
    liste_v.yeni_url = url_for('finans.banka_form')

    def detay_url(kayit):
        return url_for('finans.banka_detay', banka_id=kayit.id)

    return render_template('_liste.html',
                           satirlar=bankalar, liste_view=liste_v,
                           detay_url=detay_url, bakiyeler=bakiyeler)


@bp.route('/banka/yeni', methods=['GET', 'POST'])
@bp.route('/banka/<int:banka_id>/duzenle', methods=['GET', 'POST'])
@login_gerekli
@yazma_gerekli
def banka_form(banka_id=None):
    nesne = db.session.get(Banka, banka_id) if banka_id else None

    if request.method == 'POST':
        if not nesne:
            nesne = Banka(sirket_id=aktif_sirket_id())
            db.session.add(nesne)
        nesne.banka_adi   = request.form.get('banka_adi', '').strip()
        nesne.sube_adi    = request.form.get('sube_adi', '').strip() or None
        nesne.para_birimi = request.form.get('para_birimi', 'TRY')
        nesne.iban        = request.form.get('iban', '').strip().replace(' ', '') or None
        nesne.hesap_no    = request.form.get('hesap_no', '').strip() or None
        try:
            db.session.commit()
            flash(f"Banka [{nesne.banka_adi}] kaydedildi.", 'success')
            return redirect(url_for('finans.banka_detay', banka_id=nesne.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Kayıt hatası: {e}", 'danger')

    return render_template('_form.html',
                           form_view=BANKA_FORM, nesne=nesne,
                           form_action=url_for('finans.banka_form', banka_id=banka_id)
                                        if banka_id else url_for('finans.banka_form'))


@bp.route('/banka/<int:banka_id>')
@login_gerekli
def banka_detay(banka_id):
    banka = db.session.get(Banka, banka_id)
    if not banka:
        flash('Banka hesabı bulunamadı.', 'danger')
        return redirect(url_for('finans.banka_liste'))
    hareketler = BankaHareket.query.filter_by(banka_id=banka_id)\
                     .order_by(BankaHareket.tarih.desc()).limit(100).all()
    bakiye = _banka_bakiye(banka_id)
    return render_template('finans/banka_detay.html',
                           banka=banka, hareketler=hareketler, bakiye=bakiye)


@bp.route('/banka/<int:banka_id>/hareket/yeni', methods=['GET', 'POST'])
@login_gerekli
@yazma_gerekli
def banka_hareket_form(banka_id):
    banka = db.session.get(Banka, banka_id)
    if not banka:
        flash('Banka hesabı bulunamadı.', 'danger')
        return redirect(url_for('finans.banka_liste'))

    if request.method == 'POST':
        from datetime import date as _date
        try:
            tarih_str = request.form.get('tarih')
            hareket = BankaHareket(
                banka_id=banka_id,
                tarih=_date.fromisoformat(tarih_str) if tarih_str else _date.today(),
                belge_no=request.form.get('belge_no', '').strip() or None,
                hareket_tipi=request.form.get('hareket_tipi', 'GIRIS'),
                tutar=float(request.form.get('tutar') or 0),
                cari_id=int(request.form['cari_id']) if request.form.get('cari_id') else None,
                aciklama=request.form.get('aciklama', '').strip() or None,
            )
            db.session.add(hareket)
            db.session.commit()
            flash("Banka hareketi kaydedildi.", 'success')
            return redirect(url_for('finans.banka_detay', banka_id=banka_id))
        except Exception as e:
            db.session.rollback()
            flash(f"Kayıt hatası: {e}", 'danger')

    class _Nesne:
        pass
    nesne = _Nesne()
    nesne.banka_id = banka_id

    return render_template('_form.html',
                           form_view=BANKA_HAREKET_FORM, nesne=nesne,
                           form_action=url_for('finans.banka_hareket_form', banka_id=banka_id))
