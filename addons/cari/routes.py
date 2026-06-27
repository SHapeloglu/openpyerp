"""addons/cari/routes.py — Cari HTTP katmanı"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from core.auth import login_gerekli, yazma_gerekli
from core.context import aktif_sirket_id, aktif_sirket_al
from core.extensions import db
from addons.cari.models import Cari, CariHareket
from addons.cari.services import toplu_cari_bakiyeleri
from addons.cari.views import CARI_FORM, CARI_LISTE

bp = Blueprint('cari', __name__, url_prefix='/cari', template_folder='templates')


@bp.route('/')
@login_gerekli
def cari_liste():
    sirket = aktif_sirket_al()
    q = Cari.query.filter_by(aktif=True)
    if sirket:
        q = q.filter_by(sirket_id=sirket.id)

    tip = request.args.get('tip')
    if tip:
        q = q.filter_by(tip=tip)

    arama = request.args.get('q', '').strip()
    if arama:
        q = q.filter(
            db.or_(Cari.unvan.ilike(f'%{arama}%'),
                   Cari.kod.ilike(f'%{arama}%'),
                   Cari.vergi_no.ilike(f'%{arama}%'))
        )

    satirlar = q.order_by(Cari.unvan).all()
    bakiyeler = toplu_cari_bakiyeleri([c.id for c in satirlar])

    liste_v = CARI_LISTE
    liste_v.yeni_url = url_for('cari.cari_form')

    def detay_url(kayit):
        return url_for('cari.cari_form', cari_id=kayit.id)

    if request.headers.get('HX-Request'):
        return render_template('_liste_satirlar.html',
                               satirlar=satirlar, liste_view=liste_v,
                               detay_url=detay_url, bakiyeler=bakiyeler)

    return render_template('_liste.html',
                           satirlar=satirlar, liste_view=liste_v,
                           detay_url=detay_url, bakiyeler=bakiyeler)


@bp.route('/yeni', methods=['GET', 'POST'])
@bp.route('/<int:cari_id>/duzenle', methods=['GET', 'POST'])
@login_gerekli
@yazma_gerekli
def cari_form(cari_id=None):
    nesne = db.session.get(Cari, cari_id) if cari_id else None

    if request.method == 'POST':
        if not nesne:
            nesne = Cari(sirket_id=aktif_sirket_id())
            db.session.add(nesne)

        nesne.kod           = request.form.get('kod', '').strip().upper()
        nesne.tip           = request.form.get('tip', 'ALICI')
        nesne.unvan         = request.form.get('unvan', '').strip()
        nesne.vergi_no      = request.form.get('vergi_no', '').strip() or None
        nesne.vergi_dairesi = request.form.get('vergi_dairesi', '').strip() or None
        nesne.telefon       = request.form.get('telefon', '').strip() or None
        nesne.email         = request.form.get('email', '').strip() or None
        nesne.sehir         = request.form.get('sehir', '').strip() or None
        nesne.website       = request.form.get('website', '').strip() or None
        nesne.adres         = request.form.get('adres', '').strip() or None

        try:
            db.session.commit()
            flash(f"Cari [{nesne.unvan}] kaydedildi.", 'success')
            return redirect(url_for('cari.cari_detay', cari_id=nesne.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Kayıt hatası: {e}", 'danger')

    return render_template('_form.html',
                           form_view=CARI_FORM, nesne=nesne,
                           sil_url=url_for('cari.cari_sil', cari_id=cari_id) if cari_id else None,
                           form_action=url_for('cari.cari_form', cari_id=cari_id) if cari_id
                                        else url_for('cari.cari_form'))


@bp.route('/<int:cari_id>')
@login_gerekli
def cari_detay(cari_id):
    cari = db.session.get(Cari, cari_id) or (None, None)[1]
    if not cari:
        flash('Cari bulunamadı.', 'danger')
        return redirect(url_for('cari.cari_liste'))

    hareketler = CariHareket.query.filter_by(cari_id=cari_id)\
                     .order_by(CariHareket.tarih.desc()).limit(50).all()
    bakiye = cari.bakiye()

    return render_template('cari/detay.html',
                           cari=cari, hareketler=hareketler, bakiye=bakiye)


@bp.route('/<int:cari_id>/sil', methods=['POST'])
@login_gerekli
@yazma_gerekli
def cari_sil(cari_id):
    cari = db.session.get(Cari, cari_id)
    if cari:
        cari.aktif = False   # Soft delete
        db.session.commit()
        flash(f"Cari [{cari.unvan}] pasife alındı.", 'success')
    return redirect(url_for('cari.cari_liste'))
