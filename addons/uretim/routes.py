"""addons/uretim/routes.py — Üretim fişi HTTP katmanı"""
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from core.auth import login_gerekli, yazma_gerekli
from core.context import aktif_sirket_id, aktif_sirket_al
from core.extensions import db
from core.workflow import GecersizGecisHatasi, GuardReddiHatasi
from addons.uretim.models import UretimFis, UretimFisSatir
from addons.uretim.workflow import URETIM_WF
from addons.uretim.views import URETIM_FORM, URETIM_LISTE

bp = Blueprint('uretim', __name__, url_prefix='/uretim', template_folder='templates')


def _yeni_fis_no(sirket_id):
    from addons.sirket.services import yeni_belge_no
    return yeni_belge_no('URETIM', 'SATIS', sirket_id)


@bp.route('/')
@login_gerekli
def uretim_liste():
    sirket = aktif_sirket_al()
    q = UretimFis.query
    if sirket:
        q = q.filter_by(sirket_id=sirket.id)

    durum = request.args.get('durum')
    if durum:
        q = q.filter_by(durum=durum)

    satirlar = q.order_by(UretimFis.tarih.desc(), UretimFis.id.desc()).all()
    liste_v = URETIM_LISTE
    liste_v.yeni_url = url_for('uretim.uretim_form')

    def detay_url(kayit):
        return url_for('uretim.uretim_form', fis_id=kayit.id)

    if request.headers.get('HX-Request'):
        return render_template('_liste_satirlar.html',
                               satirlar=satirlar, liste_view=liste_v, detay_url=detay_url)
    return render_template('_liste.html',
                           satirlar=satirlar, liste_view=liste_v, detay_url=detay_url)


@bp.route('/yeni', methods=['GET', 'POST'])
@bp.route('/<int:fis_id>/duzenle', methods=['GET', 'POST'])
@login_gerekli
@yazma_gerekli
def uretim_form(fis_id=None):
    nesne = db.session.get(UretimFis, fis_id) if fis_id else None

    if request.method == 'POST':
        sid = aktif_sirket_id()
        if not nesne:
            nesne = UretimFis(
                sirket_id=sid,
                fis_no=_yeni_fis_no(sid),
                durum='TASLAK',
            )
            db.session.add(nesne)
            db.session.flush()

        tarih_str = request.form.get('tarih')
        nesne.tarih             = date.fromisoformat(tarih_str) if tarih_str else date.today()
        nesne.mamul_stok_id     = int(request.form['mamul_stok_id']) if request.form.get('mamul_stok_id') else None
        nesne.uretilecek_miktar = float(request.form.get('uretilecek_miktar') or 0)
        nesne.depo_id           = int(request.form['depo_id']) if request.form.get('depo_id') else None
        nesne.aciklama          = request.form.get('aciklama', '').strip() or None

        # Satırları yeniden oluştur
        UretimFisSatir.query.filter_by(fis_id=nesne.id).delete()
        stok_idler  = request.form.getlist('stok_id[]')
        miktarlar   = request.form.getlist('miktar[]')
        birim_idler = request.form.getlist('birim_id[]')
        for i in range(len(stok_idler)):
            try:
                miktar = float(miktarlar[i] or 0)
            except ValueError:
                continue
            if miktar <= 0 or not stok_idler[i]:
                continue
            db.session.add(UretimFisSatir(
                fis_id=nesne.id,
                stok_id=int(stok_idler[i]),
                miktar=miktar,
                cevrilen_miktar=miktar,
                birim_id=int(birim_idler[i]) if i < len(birim_idler) and birim_idler[i] else None,
            ))
        try:
            db.session.commit()
            flash(f"Üretim fişi [{nesne.fis_no}] kaydedildi.", 'success')
            return redirect(url_for('uretim.uretim_form', fis_id=nesne.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Kayıt hatası: {e}", 'danger')

    form_v = URETIM_FORM
    form_v.iptal_url = url_for('uretim.uretim_liste')
    form_action = url_for('uretim.uretim_form', fis_id=fis_id) if fis_id \
        else url_for('uretim.uretim_form')

    return render_template('_form.html',
                           form_view=form_v, nesne=nesne,
                           form_action=form_action,
                           satirlar=nesne.satirlar if nesne else [])


@bp.route('/<int:fis_id>/gecis/<hedef_durum>', methods=['POST'])
@login_gerekli
@yazma_gerekli
def uretim_gecis(fis_id, hedef_durum):
    fis = db.session.get(UretimFis, fis_id)
    if not fis:
        flash('Üretim fişi bulunamadı.', 'danger')
        return redirect(url_for('uretim.uretim_liste'))
    try:
        URETIM_WF.gecer(fis, hedef_durum)
        db.session.commit()
        flash(f"Durum '{hedef_durum}' olarak güncellendi.", 'success')
    except (GuardReddiHatasi, GecersizGecisHatasi) as e:
        db.session.rollback()
        flash(str(e), 'danger')
    return redirect(url_for('uretim.uretim_form', fis_id=fis_id))
