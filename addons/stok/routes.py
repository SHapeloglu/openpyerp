"""addons/stok/routes.py — Stok HTTP katmanı"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from core.auth import login_gerekli, yazma_gerekli
from core.context import aktif_sirket_id, aktif_sirket_al
from core.extensions import db
from addons.stok.models import StokKarti, StokHareket
from addons.stok.views import STOK_FORM, STOK_LISTE

bp = Blueprint('stok', __name__, url_prefix='/stok', template_folder='templates')


@bp.route('/')
@login_gerekli
def stok_liste():
    sirket = aktif_sirket_al()
    q = StokKarti.query.filter_by(aktif=True)
    if sirket:
        q = q.filter_by(sirket_id=sirket.id)

    tip = request.args.get('tip')
    if tip:
        q = q.filter_by(tip=tip)

    arama = request.args.get('q', '').strip()
    if arama:
        q = q.filter(db.or_(
            StokKarti.ad.ilike(f'%{arama}%'),
            StokKarti.kod.ilike(f'%{arama}%'),
            StokKarti.barkod_ean13.ilike(f'%{arama}%'),
        ))

    satirlar = q.order_by(StokKarti.ad).all()
    liste_v = STOK_LISTE
    liste_v.yeni_url = url_for('stok.stok_form')

    def detay_url(kayit):
        return url_for('stok.stok_form', stok_id=kayit.id)

    if request.headers.get('HX-Request'):
        return render_template('_liste_satirlar.html',
                               satirlar=satirlar, liste_view=liste_v,
                               detay_url=detay_url)

    return render_template('_liste.html',
                           satirlar=satirlar, liste_view=liste_v,
                           detay_url=detay_url)


@bp.route('/yeni', methods=['GET', 'POST'])
@bp.route('/<int:stok_id>/duzenle', methods=['GET', 'POST'])
@login_gerekli
@yazma_gerekli
def stok_form(stok_id=None):
    nesne = db.session.get(StokKarti, stok_id) if stok_id else None

    if request.method == 'POST':
        if not nesne:
            nesne = StokKarti(sirket_id=aktif_sirket_id())
            db.session.add(nesne)

        nesne.kod           = request.form.get('kod','').strip().upper()
        nesne.ad            = request.form.get('ad','').strip()
        nesne.tip           = request.form.get('tip','MALZEME')
        nesne.kullanim_tipi = request.form.get('kullanim_tipi','HER_IKISI')
        nesne.birim_id      = int(request.form['birim_id']) if request.form.get('birim_id') else None
        nesne.kdv_orani     = float(request.form.get('kdv_orani') or 20)
        nesne.satis_fiyati  = float(request.form.get('satis_fiyati') or 0)
        nesne.alis_fiyati   = float(request.form.get('alis_fiyati') or 0)
        nesne.min_stok      = float(request.form.get('min_stok')) if request.form.get('min_stok') else None
        nesne.barkod_ean13  = request.form.get('barkod_ean13','').strip() or None
        nesne.barkod_ean8   = request.form.get('barkod_ean8','').strip() or None
        nesne.aciklama      = request.form.get('aciklama','').strip() or None

        try:
            db.session.commit()
            flash(f"Stok kartı [{nesne.ad}] kaydedildi.", 'success')
            return redirect(url_for('stok.stok_detay', stok_id=nesne.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Kayıt hatası: {e}", 'danger')

    return render_template('_form.html',
                           form_view=STOK_FORM, nesne=nesne,
                           sil_url=url_for('stok.stok_sil', stok_id=stok_id) if stok_id else None,
                           form_action=url_for('stok.stok_form', stok_id=stok_id) if stok_id
                                        else url_for('stok.stok_form'))


@bp.route('/<int:stok_id>')
@login_gerekli
def stok_detay(stok_id):
    stok = db.session.get(StokKarti, stok_id)
    if not stok:
        flash('Stok kartı bulunamadı.', 'danger')
        return redirect(url_for('stok.stok_liste'))

    miktar   = stok.stok_miktari()
    hareketler = StokHareket.query.filter_by(stok_id=stok_id)\
                     .order_by(StokHareket.tarih.desc()).limit(50).all()

    return render_template('stok/detay.html',
                           stok=stok, miktar=miktar, hareketler=hareketler)


@bp.route('/<int:stok_id>/sil', methods=['POST'])
@login_gerekli
@yazma_gerekli
def stok_sil(stok_id):
    stok = db.session.get(StokKarti, stok_id)
    if stok:
        stok.aktif = False  # Soft delete
        db.session.commit()
        flash(f"Stok kartı [{stok.ad}] pasife alındı.", 'success')
    return redirect(url_for('stok.stok_liste'))
