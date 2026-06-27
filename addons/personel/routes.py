"""addons/personel/routes.py — Personel HTTP katmanı"""
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from core.auth import login_gerekli, yazma_gerekli
from core.context import aktif_sirket_id, aktif_sirket_al
from core.extensions import db
from addons.personel.models import Personel, PersonelIzin, Puantaj
from addons.personel.views import PERSONEL_FORM, IZIN_FORM, PERSONEL_LISTE

bp = Blueprint('personel', __name__, url_prefix='/personel', template_folder='templates')


@bp.route('/')
@login_gerekli
def personel_liste():
    sirket = aktif_sirket_al()
    q = Personel.query.filter_by(aktif=True)
    if sirket:
        q = q.filter_by(sirket_id=sirket.id)

    arama = request.args.get('q', '').strip()
    if arama:
        q = q.filter(db.or_(
            Personel.ad.ilike(f'%{arama}%'),
            Personel.soyad.ilike(f'%{arama}%'),
            Personel.sicil_no.ilike(f'%{arama}%'),
        ))

    satirlar = q.order_by(Personel.soyad, Personel.ad).all()
    liste_v = PERSONEL_LISTE
    liste_v.yeni_url = url_for('personel.personel_form')

    def detay_url(kayit):
        return url_for('personel.personel_detay', personel_id=kayit.id)

    if request.headers.get('HX-Request'):
        return render_template('_liste_satirlar.html',
                               satirlar=satirlar, liste_view=liste_v, detay_url=detay_url)
    return render_template('_liste.html',
                           satirlar=satirlar, liste_view=liste_v, detay_url=detay_url)


@bp.route('/yeni', methods=['GET', 'POST'])
@bp.route('/<int:personel_id>/duzenle', methods=['GET', 'POST'])
@login_gerekli
@yazma_gerekli
def personel_form(personel_id=None):
    nesne = db.session.get(Personel, personel_id) if personel_id else None

    if request.method == 'POST':
        if not nesne:
            nesne = Personel(sirket_id=aktif_sirket_id())
            db.session.add(nesne)

        nesne.sicil_no    = request.form.get('sicil_no', '').strip().upper()
        nesne.ad          = request.form.get('ad', '').strip()
        nesne.soyad       = request.form.get('soyad', '').strip()
        nesne.tc_kimlik   = request.form.get('tc_kimlik', '').strip() or None
        g_str = request.form.get('ise_giris')
        nesne.ise_giris   = date.fromisoformat(g_str) if g_str else date.today()
        c_str = request.form.get('isten_cikis')
        nesne.isten_cikis = date.fromisoformat(c_str) if c_str else None

        try:
            db.session.commit()
            flash(f"Personel [{nesne.tam_ad}] kaydedildi.", 'success')
            return redirect(url_for('personel.personel_detay', personel_id=nesne.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Kayıt hatası: {e}", 'danger')

    return render_template('_form.html',
                           form_view=PERSONEL_FORM, nesne=nesne,
                           form_action=url_for('personel.personel_form', personel_id=personel_id)
                                        if personel_id else url_for('personel.personel_form'))


@bp.route('/<int:personel_id>')
@login_gerekli
def personel_detay(personel_id):
    p = db.session.get(Personel, personel_id)
    if not p:
        flash('Personel bulunamadı.', 'danger')
        return redirect(url_for('personel.personel_liste'))
    izinler = PersonelIzin.query.filter_by(personel_id=personel_id)\
                  .order_by(PersonelIzin.baslangic.desc()).all()
    return render_template('personel/detay.html', personel=p, izinler=izinler)


@bp.route('/<int:personel_id>/izin/yeni', methods=['GET', 'POST'])
@login_gerekli
@yazma_gerekli
def izin_form(personel_id):
    p = db.session.get(Personel, personel_id)
    if not p:
        flash('Personel bulunamadı.', 'danger')
        return redirect(url_for('personel.personel_liste'))

    if request.method == 'POST':
        try:
            b_str = request.form.get('baslangic')
            e_str = request.form.get('bitis')
            izin = PersonelIzin(
                personel_id=personel_id,
                izin_tipi=request.form.get('izin_tipi', 'YILLIK'),
                baslangic=date.fromisoformat(b_str) if b_str else date.today(),
                bitis=date.fromisoformat(e_str) if e_str else date.today(),
                gun_sayisi=int(request.form.get('gun_sayisi') or 1),
                aciklama=request.form.get('aciklama', '').strip() or None,
                durum='BEKLEMEDE',
            )
            db.session.add(izin)
            db.session.commit()
            flash("İzin talebi oluşturuldu.", 'success')
            return redirect(url_for('personel.personel_detay', personel_id=personel_id))
        except Exception as e:
            db.session.rollback()
            flash(f"Kayıt hatası: {e}", 'danger')

    return render_template('_form.html',
                           form_view=IZIN_FORM, nesne=None,
                           form_action=url_for('personel.izin_form', personel_id=personel_id))
