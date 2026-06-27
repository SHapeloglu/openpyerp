"""addons/belge/routes.py — Belge HTTP katmanı (generic view kullanan ince controller)"""
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from core.auth import login_gerekli, yazma_gerekli
from core.context import aktif_sirket_id, aktif_sirket_al
from core.extensions import db
from addons.belge.dto import BelgeKaydetGirdi, BelgeSatirGirdi
from addons.belge.models import BelgeBaslik
from addons.belge.views import belge_form_view, belge_liste_view
from addons.belge.services import (
    BelgeKaydetServisi, BelgeDonusturServisi, BelgeDonusturHatasi,
    belge_cogalt, BelgeSilServisi, BelgeSilHatasi, irsaliye_fatura_birlestir,
)
from addons.belge.workflow import BELGE_WF
from core.workflow import GecersizGecisHatasi, GuardReddiHatasi
from addons.stok.models import StokKarti

bp = Blueprint('belge', __name__, url_prefix='/belge', template_folder='templates')


def _parse_tarih(v, varsayilan=None):
    try:
        return date.fromisoformat(v) if v else (varsayilan or date.today())
    except ValueError:
        return varsayilan or date.today()


def _form_satirlari_oku():
    stok_idler  = request.form.getlist('stok_id[]')
    miktarlar   = request.form.getlist('miktar[]')
    fiyatlar    = request.form.getlist('birim_fiyat[]')
    birim_idler = request.form.getlist('birim_id[]')
    iskontolar  = request.form.getlist('iskonto_oran[]')
    kdvler      = request.form.getlist('kdv_orani[]')
    aciklamalar = request.form.getlist('aciklama[]')
    carpanlar   = request.form.getlist('donusum_carpan[]')
    satirlar = []
    for i in range(len(miktarlar)):
        try:
            miktar = float(miktarlar[i] or 0)
            fiyat  = float(fiyatlar[i] if i < len(fiyatlar) else 0)
        except ValueError:
            continue
        if miktar == 0 and fiyat == 0:
            continue
        satirlar.append(BelgeSatirGirdi(
            stok_id=int(stok_idler[i]) if i < len(stok_idler) and stok_idler[i] else None,
            miktar=miktar, birim_fiyat=fiyat,
            birim_id=int(birim_idler[i]) if i < len(birim_idler) and birim_idler[i] else None,
            iskonto_oran=float(iskontolar[i]) if i < len(iskontolar) and iskontolar[i] else 0.0,
            kdv_orani=float(kdvler[i]) if i < len(kdvler) and kdvler[i] else 20.0,
            aciklama=aciklamalar[i] if i < len(aciklamalar) else '',
            donusum_carpan=float(carpanlar[i]) if i < len(carpanlar) and carpanlar[i] else 1.0,
        ))
    return satirlar


# ── Liste ─────────────────────────────────────────────────────────────────
@bp.route('/liste/<belge_tip>/<cari_tip>')
@login_gerekli
def belge_liste(belge_tip='FATURA', cari_tip='SATIS'):
    sirket = aktif_sirket_al()
    q = BelgeBaslik.query.filter_by(belge_tip=belge_tip.upper(), cari_tip=cari_tip.upper())
    if sirket:
        q = q.filter_by(sirket_id=sirket.id)

    filtre_durum = request.args.get('durum')
    if filtre_durum:
        q = q.filter_by(durum=filtre_durum)

    arama = request.args.get('q', '').strip()
    if arama:
        q = q.filter(BelgeBaslik.belge_no.ilike(f'%{arama}%'))

    satirlar = q.order_by(BelgeBaslik.tarih.desc(), BelgeBaslik.id.desc()).all()
    liste_v = belge_liste_view(belge_tip, cari_tip)
    liste_v.yeni_url = url_for('belge.belge_form',
                                belge_tip=belge_tip, cari_tip=cari_tip)

    def detay_url(kayit):
        return url_for('belge.belge_form', baslik_id=kayit.id)

    # HTMX partial isteği — sadece tablo gövdesini döndür
    if request.headers.get('HX-Request'):
        return render_template('_liste_satirlar.html',
                               satirlar=satirlar, liste_view=liste_v,
                               detay_url=detay_url)

    return render_template('_liste.html',
                           satirlar=satirlar, liste_view=liste_v,
                           detay_url=detay_url)


# ── Form (Yeni / Düzenle) ─────────────────────────────────────────────────
@bp.route('/yeni/<belge_tip>/<cari_tip>', methods=['GET', 'POST'])
@bp.route('/<int:baslik_id>/duzenle', methods=['GET', 'POST'])
@login_gerekli
@yazma_gerekli
def belge_form(belge_tip='FATURA', cari_tip='SATIS', baslik_id=None):
    nesne = db.session.get(BelgeBaslik, baslik_id) if baslik_id else None
    if nesne:
        belge_tip = nesne.belge_tip
        cari_tip  = nesne.cari_tip

    if request.method == 'POST':
        girdi = BelgeKaydetGirdi(
            baslik_id=baslik_id,
            belge_tip=request.form.get('belge_tip', belge_tip),
            cari_tip=request.form.get('cari_tip', cari_tip),
            tarih=_parse_tarih(request.form.get('tarih')),
            vade_tarihi=_parse_tarih(request.form.get('vade_tarihi')) if request.form.get('vade_tarihi') else None,
            cari_id=int(request.form['cari_id']) if request.form.get('cari_id') else None,
            sirket_id=aktif_sirket_id(),
            depo_id=int(request.form['depo_id']) if request.form.get('depo_id') else None,
            evrak_no=request.form.get('evrak_no', ''),
            aciklama=request.form.get('aciklama', ''),
            durum=request.form.get('durum', 'ACIK'),
            satirlar=_form_satirlari_oku(),
        )
        sonuc = BelgeKaydetServisi().kaydet(girdi)
        if sonuc.basarili:
            flash(f"Belge [{sonuc.belge_no}] kaydedildi.", 'success')
            return redirect(url_for('belge.belge_form', baslik_id=sonuc.belge_id))
        else:
            flash(sonuc.hata_mesaji, 'danger')

    form_v = belge_form_view(belge_tip, cari_tip)
    form_v.iptal_url = url_for('belge.belge_liste', belge_tip=belge_tip, cari_tip=cari_tip)
    form_action = url_for('belge.belge_form', baslik_id=baslik_id) if baslik_id \
        else url_for('belge.belge_form', belge_tip=belge_tip, cari_tip=cari_tip)

    return render_template('_form.html',
                           form_view=form_v, nesne=nesne,
                           form_action=form_action,
                           satirlar=nesne.satirlar if nesne else [])


# ── HTMX: yeni satır partial'ı ────────────────────────────────────────────
@bp.route('/satir-ekle')
@login_gerekli
def satir_ekle_partial():
    """HTMX "Satır Ekle" butonunun çağırdığı endpoint — boş satır HTML döner."""
    belge_tip = request.args.get('belge_tip', 'FATURA')
    cari_tip  = request.args.get('cari_tip', 'SATIS')
    sira      = int(request.args.get('sira', 1))
    form_v    = belge_form_view(belge_tip, cari_tip)
    return render_template('_satir_satiri.html',
                           satir=None, sira=sira, form_view=form_v)


# ── Durum geçişi (workflow) ────────────────────────────────────────────────
@bp.route('/<int:baslik_id>/gecis/<hedef_durum>', methods=['POST'])
@login_gerekli
@yazma_gerekli
def belge_durum_gecis(baslik_id, hedef_durum):
    b = db.session.get(BelgeBaslik, baslik_id)
    if not b:
        flash('Belge bulunamadı.', 'danger')
        return redirect(url_for('dashboard.index'))
    try:
        BELGE_WF.gecer(b, hedef_durum)
        db.session.commit()
        flash(f"Belge '{hedef_durum}' durumuna geçirildi.", 'success')
    except (GuardReddiHatasi, GecersizGecisHatasi) as e:
        db.session.rollback()
        flash(str(e), 'danger')
    return redirect(url_for('belge.belge_form', baslik_id=baslik_id))


# ── Dönüştür ──────────────────────────────────────────────────────────────
@bp.route('/<int:baslik_id>/donustur/<hedef_tip>', methods=['POST'])
@login_gerekli
@yazma_gerekli
def belge_donustur(baslik_id, hedef_tip):
    try:
        yeni = BelgeDonusturServisi().donustur(baslik_id, hedef_tip)
        flash(f"{BelgeBaslik.TIP_ADLARI.get(hedef_tip, hedef_tip)} [{yeni.belge_no}] oluşturuldu.", 'success')
        return redirect(url_for('belge.belge_form', baslik_id=yeni.id))
    except BelgeDonusturHatasi as e:
        flash(str(e), 'danger')
        return redirect(url_for('belge.belge_form', baslik_id=baslik_id))


# ── Çoğalt ────────────────────────────────────────────────────────────────
@bp.route('/<int:baslik_id>/cogalt', methods=['POST'])
@login_gerekli
@yazma_gerekli
def belge_cogalt_view(baslik_id):
    try:
        yeni = belge_cogalt(baslik_id, sirket_id_varsayilan=aktif_sirket_id())
        flash(f"Belge kopyalandı → [{yeni.belge_no}]", 'success')
        return redirect(url_for('belge.belge_form', baslik_id=yeni.id))
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('belge.belge_form', baslik_id=baslik_id))


# ── Sil ───────────────────────────────────────────────────────────────────
@bp.route('/<int:baslik_id>/sil', methods=['POST'])
@login_gerekli
@yazma_gerekli
def belge_sil(baslik_id):
    b = db.session.get(BelgeBaslik, baslik_id)
    belge_tip = b.belge_tip if b else 'FATURA'
    cari_tip  = b.cari_tip  if b else 'SATIS'
    try:
        BelgeSilServisi().sil(baslik_id)
        flash('Belge silindi.', 'success')
        return redirect(url_for('belge.belge_liste', belge_tip=belge_tip, cari_tip=cari_tip))
    except BelgeSilHatasi as e:
        flash(str(e), 'danger')
        return redirect(url_for('belge.belge_form', baslik_id=baslik_id))


# ── İrsaliye birleştir ────────────────────────────────────────────────────
@bp.route('/irsaliye/birlestir', methods=['POST'])
@login_gerekli
@yazma_gerekli
def irsaliye_birlestir():
    idler = [int(i) for i in request.form.getlist('irsaliye_id[]') if i]
    if not idler:
        flash('En az bir irsaliye seçin.', 'warning')
        return redirect(url_for('belge.belge_liste', belge_tip='IRSALIYE', cari_tip='SATIS'))
    try:
        fatura = irsaliye_fatura_birlestir(idler, sirket_id_varsayilan=aktif_sirket_id())
        flash(f"{len(idler)} irsaliye → Fatura [{fatura.belge_no}] oluşturuldu.", 'success')
        return redirect(url_for('belge.belge_form', baslik_id=fatura.id))
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('belge.belge_liste', belge_tip='IRSALIYE', cari_tip='SATIS'))


# ── AJAX: stok fiyat ──────────────────────────────────────────────────────
@bp.route('/api/stok-fiyat/<int:stok_id>')
@login_gerekli
def stok_fiyat_al(stok_id):
    cari_tip = request.args.get('cari_tip', 'SATIS')
    stok = StokKarti.query.get_or_404(stok_id)
    return jsonify({
        'birim_id':  stok.birim_id,
        'birim_kod': stok.birim.kod if stok.birim else '',
        'kdv_orani': float(stok.kdv_orani or 20),
        'fiyat':     float(stok.satis_fiyati if cari_tip == 'SATIS' else stok.alis_fiyati or 0),
    })
