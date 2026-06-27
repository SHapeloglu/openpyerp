"""addons/ayarlar/routes.py — Giriş/çıkış ve kullanıcı yönetimi"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from addons.ayarlar.models import Kullanici

bp = Blueprint('ayarlar', __name__, url_prefix='/ayarlar', template_folder='templates')

@bp.route('/giris', methods=['GET', 'POST'])
def giris():
    if request.method == 'POST':
        k = Kullanici.query.filter_by(email=request.form.get('email'), aktif=True).first()
        if k and k.sifre_dogru_mu(request.form.get('sifre', '')):
            session['kullanici_id'] = k.id
            session['kullanici_ad'] = k.ad_soyad
            return redirect(request.args.get('next') or url_for('dashboard.index'))
        flash('E-posta veya şifre hatalı.', 'danger')
    return render_template('ayarlar/giris.html')

@bp.route('/cikis')
def cikis():
    session.clear()
    return redirect(url_for('ayarlar.giris'))
