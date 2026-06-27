"""
addons/belge/services.py — Belge modülü uygulama servisleri (workflow sonrası)

WORKFLOW SONRASI DEĞİŞİKLİKLER:
    Önceki versiyonda BelgeKaydetServisi.kaydet() şunları yapıyordu:
        - Dönem kilidi kontrolü (guard'a taşındı)
        - TASLAK→ACIK geçişi (workflow.gecer'e taşındı)
        - Cari/stok hareketi üretimi (action'a taşındı)
        - Stok yeterliliği kontrolü (guard'a taşındı)
        - Sevk durumu hesaplama (action'a taşındı)

    Şimdi kaydet() sadece şunu yapar:
        1. Başlık oluştur/getir
        2. Alanları güncelle
        3. Satırları yeniden oluştur + toplamları hesapla
        4. Durum geçişi varsa BELGE_WF.gecer() çağır
        5. Commit

    İş kuralları services.py'den workflow.py'a taşındı — her katman
    tek bir şeyden sorumlu oldu.
"""
from decimal import Decimal, ROUND_HALF_UP

from core.extensions import db
from core.para import para, miktar_d
from core.hooks import emit
from core.tipler import BelgeDurum
from core.workflow import GecersizGecisHatasi, GuardReddiHatasi
from addons.belge.models import BelgeBaslik, BelgeSatir


# ════════════════════════════════════════════════════════════
#  SAF HESAPLAMA (DB'siz, framework'süz)
# ════════════════════════════════════════════════════════════

def satir_hesapla(miktar, birim_fiyat, iskonto_oran, kdv_orani):
    """Satır tutarlarını Decimal hassasiyetiyle hesaplar.

    Döner: (kdvsiz_tutar, kdv_tutar, kdvli_tutar) — float.
    """
    m    = miktar_d(miktar)
    bf   = para(birim_fiyat)
    isk  = para(iskonto_oran)
    kdvo = para(kdv_orani)

    brut  = m * bf
    kd    = brut - (brut * isk / Decimal('100'))
    kdv   = kd * kdvo / Decimal('100')
    kdvli = kd + kdv

    yuvarla = lambda x: float(x.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    return yuvarla(kd), yuvarla(kdv), yuvarla(kdvli)


def baslik_toplamla(baslik: BelgeBaslik):
    """Başlık toplamlarını ilişkili satırlardan hesaplar. Commit yapmaz."""
    tk = td = tl = Decimal('0')
    for s in baslik.satirlar:
        tk += para(s.kdvsiz_tutar)
        td += para(s.kdv_tutar)
        tl += para(s.kdvli_tutar)
    yuvarla = lambda x: float(x.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    baslik.toplam_kdvsiz = yuvarla(tk)
    baslik.toplam_kdv    = yuvarla(td)
    baslik.toplam_kdvli  = yuvarla(tl)


def sevk_durumu_hesapla(irsaliye: BelgeBaslik):
    """İrsaliyenin sevk durumunu kaynak sipariş ile karşılaştırarak günceller."""
    from core.tipler import SevkDurum
    if not irsaliye.kaynak_belge_id:
        irsaliye.sevk_durumu = SevkDurum.SEVK_EDILMEDI
        return

    kaynak = db.session.get(BelgeBaslik, irsaliye.kaynak_belge_id)
    if not kaynak:
        irsaliye.sevk_durumu = SevkDurum.SEVK_EDILMEDI
        return

    kaynak_miktarlar = {s.stok_id: float(s.miktar) for s in kaynak.satirlar if s.stok_id}
    if not kaynak_miktarlar:
        irsaliye.sevk_durumu = SevkDurum.TUMU_SEVK_EDILDI
        return

    esit = sum(
        1 for s in irsaliye.satirlar
        if s.stok_id in kaynak_miktarlar
        and abs(float(s.miktar) - kaynak_miktarlar[s.stok_id]) < 0.0001
    )
    if esit == len(kaynak_miktarlar):
        irsaliye.sevk_durumu = SevkDurum.TUMU_SEVK_EDILDI
    else:
        irsaliye.sevk_durumu = SevkDurum.KISMI_SEVK


# ════════════════════════════════════════════════════════════
#  BELGE KAYDET SERVİSİ
# ════════════════════════════════════════════════════════════

class BelgeKaydetServisi:
    """Belge oluşturma ve güncelleme use case'i.

    Workflow entegrasyonu sonrası bu servis sadece veri yazma işini yapar.
    İş kuralı kontrolü (guard) ve yan etkiler (action) BELGE_WF içinde.
    """

    def kaydet(self, girdi) -> 'BelgeKaydetSonuc':
        from addons.belge.dto import BelgeKaydetSonuc
        from addons.sirket.services import yeni_belge_no
        from addons.belge.workflow import BELGE_WF

        belge_tip = girdi.belge_tip.upper()

        # ── 1) Başlık oluştur / getir ────────────────────────────────
        baslik = db.session.get(BelgeBaslik, girdi.baslik_id) if girdi.baslik_id else None
        yeni_belge = baslik is None
        if yeni_belge:
            baslik = BelgeBaslik(
                belge_tip=belge_tip,
                belge_no=yeni_belge_no(belge_tip, girdi.cari_tip, girdi.sirket_id),
                durum=BelgeDurum.TASLAK,
            )
            db.session.add(baslik)
            db.session.flush()

        # ── 2) Alanları güncelle ─────────────────────────────────────
        baslik.cari_tip    = girdi.cari_tip
        baslik.tarih       = girdi.tarih
        baslik.vade_tarihi = girdi.vade_tarihi
        baslik.cari_id     = girdi.cari_id
        baslik.aciklama    = (girdi.aciklama or '').strip()
        baslik.evrak_no    = (girdi.evrak_no or '').strip() or None
        baslik.depo_id     = girdi.depo_id
        baslik.sirket_id   = girdi.sirket_id

        # ── 3) Satırları yeniden oluştur ─────────────────────────────
        BelgeSatir.query.filter_by(baslik_id=baslik.id).delete()
        db.session.flush()

        for i, sg in enumerate(girdi.satirlar):
            if sg.miktar == 0 and sg.birim_fiyat == 0:
                continue
            kdvsiz, kdv, kdvli = satir_hesapla(sg.miktar, sg.birim_fiyat,
                                                sg.iskonto_oran, sg.kdv_orani)
            db.session.add(BelgeSatir(
                baslik_id=baslik.id, sira_no=i + 1, stok_id=sg.stok_id,
                aciklama=sg.aciklama, miktar=sg.miktar, birim_id=sg.birim_id,
                birim_fiyat=sg.birim_fiyat, iskonto_oran=sg.iskonto_oran,
                kdv_orani=sg.kdv_orani, donusum_carpan=sg.donusum_carpan,
                cevrilen_miktar=round(sg.miktar * sg.donusum_carpan, 4),
                kdvsiz_tutar=kdvsiz, kdv_tutar=kdv, kdvli_tutar=kdvli,
            ))

        db.session.flush()
        baslik_toplamla(baslik)

        # ── 4) Durum geçişi — TASLAK → ACIK (workflow ile) ──────────
        hedef_durum = girdi.durum or BelgeDurum.ACIK
        try:
            if BELGE_WF.gecis_gecerli_mi(baslik, hedef_durum):
                BELGE_WF.gecer(baslik, hedef_durum)
        except GuardReddiHatasi as e:
            db.session.rollback()
            return BelgeKaydetSonuc(basarili=False, hata_kodu=e.kod, hata_mesaji=str(e))
        except GecersizGecisHatasi as e:
            db.session.rollback()
            return BelgeKaydetSonuc(basarili=False, hata_kodu='GECERSIZ_GECIS', hata_mesaji=str(e))

        # ── 5) Commit ────────────────────────────────────────────────
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return BelgeKaydetSonuc(basarili=False, hata_kodu='DB_HATASI', hata_mesaji=str(e))

        emit('belge.kaydedildi', belge=baslik)
        return BelgeKaydetSonuc(basarili=True, belge_id=baslik.id, belge_no=baslik.belge_no)


# ════════════════════════════════════════════════════════════
#  BELGE DÖNÜŞTÜR SERVİSİ
# ════════════════════════════════════════════════════════════

class BelgeDonusturHatasi(Exception):
    pass


class BelgeDonusturServisi:
    """Belgeyi zincirde bir üst tipe dönüştürür (TALEP→SİPARİŞ→İRSALİYE→FATURA).

    Kaynak ONAYLANDI olmalı — bu kontrolü workflow guard değil, dönüşüm mantığı yapar
    çünkü kaynak belgenin durumu değişiyor, hedef belge yeni oluşuyor.
    """

    def donustur(self, kaynak_id: int, hedef_tip: str) -> BelgeBaslik:
        from addons.sirket.services import yeni_belge_no
        from datetime import date as _date

        kaynak = db.session.get(BelgeBaslik, kaynak_id)
        if not kaynak:
            raise BelgeDonusturHatasi('Kaynak belge bulunamadı.')

        hedef_tip = hedef_tip.upper()
        if kaynak.durum != BelgeDurum.ONAYLANDI:
            kaynak_ad = BelgeBaslik.TIP_ADLARI.get(kaynak.belge_tip, kaynak.belge_tip)
            raise BelgeDonusturHatasi(
                f"{kaynak_ad} [{kaynak.belge_no}] henüz onaylanmamış."
            )

        yeni = BelgeBaslik(
            belge_tip=hedef_tip,
            belge_no=yeni_belge_no(hedef_tip, kaynak.cari_tip, kaynak.sirket_id),
            tarih=_date.today(), cari_id=kaynak.cari_id, cari_tip=kaynak.cari_tip,
            aciklama=kaynak.aciklama, durum=BelgeDurum.TASLAK,
            kaynak_belge_id=kaynak.id, depo_id=kaynak.depo_id, sirket_id=kaynak.sirket_id,
        )
        db.session.add(yeni)
        db.session.flush()

        from core.tipler import BelgeTip
        if kaynak.belge_tip == BelgeTip.SIPARIS and hedef_tip == BelgeTip.IRSALIYE:
            eklenen = self._bekleyen_satirlari_kopyala(kaynak, yeni)
            if eklenen == 0:
                db.session.delete(yeni)
                db.session.commit()
                raise BelgeDonusturHatasi(f"{kaynak.belge_no} siparişi tamamen sevk edilmiş.")
        else:
            for s in kaynak.satirlar:
                db.session.add(BelgeSatir(
                    baslik_id=yeni.id, sira_no=s.sira_no, stok_id=s.stok_id,
                    aciklama=s.aciklama, miktar=s.miktar, birim_id=s.birim_id,
                    birim_fiyat=s.birim_fiyat, iskonto_oran=s.iskonto_oran,
                    kdv_orani=s.kdv_orani, kdvsiz_tutar=s.kdvsiz_tutar,
                    kdv_tutar=s.kdv_tutar, kdvli_tutar=s.kdvli_tutar,
                ))

        yeni.evrak_no = kaynak.belge_no
        baslik_toplamla(yeni)
        db.session.commit()
        return yeni

    @staticmethod
    def _bekleyen_satirlari_kopyala(kaynak: BelgeBaslik, yeni: BelgeBaslik) -> int:
        onceki = BelgeBaslik.query.filter_by(
            kaynak_belge_id=kaynak.id, belge_tip='IRSALIYE'
        ).filter(BelgeBaslik.durum.notin_([BelgeDurum.IPTAL, BelgeDurum.TASLAK])).all()

        sevk = {}
        for irs in onceki:
            for s in irs.satirlar:
                if s.stok_id:
                    sevk[s.stok_id] = sevk.get(s.stok_id, 0) + float(s.miktar)

        eklenen = 0
        for s in kaynak.satirlar:
            bekleyen = round(float(s.miktar) - sevk.get(s.stok_id, 0), 4)
            if bekleyen <= 0:
                continue
            db.session.add(BelgeSatir(
                baslik_id=yeni.id, sira_no=s.sira_no, stok_id=s.stok_id,
                aciklama=s.aciklama, miktar=bekleyen, birim_id=s.birim_id,
                birim_fiyat=s.birim_fiyat, iskonto_oran=s.iskonto_oran,
                kdv_orani=s.kdv_orani, kdvsiz_tutar=0, kdv_tutar=0, kdvli_tutar=0,
            ))
            eklenen += 1
        return eklenen


# ════════════════════════════════════════════════════════════
#  BELGE ÇOĞALT
# ════════════════════════════════════════════════════════════

def belge_cogalt(kaynak_id: int, sirket_id_varsayilan: int = None) -> BelgeBaslik:
    from addons.sirket.services import yeni_belge_no
    from datetime import date as _date

    kaynak = db.session.get(BelgeBaslik, kaynak_id)
    if not kaynak:
        raise ValueError('Kaynak belge bulunamadı.')

    sid = kaynak.sirket_id or sirket_id_varsayilan
    yeni = BelgeBaslik(
        belge_tip=kaynak.belge_tip, belge_no=yeni_belge_no(kaynak.belge_tip, kaynak.cari_tip, sid),
        cari_tip=kaynak.cari_tip, cari_id=kaynak.cari_id, tarih=_date.today(),
        aciklama=kaynak.aciklama, depo_id=kaynak.depo_id, sirket_id=sid,
        durum=BelgeDurum.ACIK, kaynak_belge_id=None,
    )
    db.session.add(yeni)
    db.session.flush()

    for s in kaynak.satirlar:
        db.session.add(BelgeSatir(
            baslik_id=yeni.id, sira_no=s.sira_no, stok_id=s.stok_id, aciklama=s.aciklama,
            miktar=s.miktar, birim_id=s.birim_id, birim_fiyat=s.birim_fiyat,
            iskonto_oran=s.iskonto_oran, kdv_orani=s.kdv_orani,
            kdvsiz_tutar=s.kdvsiz_tutar, kdv_tutar=s.kdv_tutar, kdvli_tutar=s.kdvli_tutar,
        ))

    baslik_toplamla(yeni)
    db.session.commit()
    return yeni


# ════════════════════════════════════════════════════════════
#  BELGE SİL SERVİSİ
# ════════════════════════════════════════════════════════════

class BelgeSilHatasi(Exception):
    def __init__(self, mesaj, kod):
        self.kod = kod
        super().__init__(mesaj)


class BelgeSilServisi:
    """Belgeyi siler — workflow guard'larını BYPASS EDER çünkü silme workflow'un dışında.

    Silme, iptal ile farklıdır: iptal durum geçişidir (ONAYLANDI→IPTAL),
    silme ise kaydın fiziksel olarak kaldırılmasıdır (sadece TASLAK/ACIK için).
    """

    def sil(self, belge_id: int):
        from addons.sirket.services import donem_kilitli_mi
        from addons.stok.services import kaynak_hareketlerini_sil as stok_sil
        from addons.cari.services import kaynak_hareketlerini_sil as cari_sil

        b = db.session.get(BelgeBaslik, belge_id)
        if not b:
            raise BelgeSilHatasi('Belge bulunamadı.', 'BULUNAMADI')

        if b.durum not in BelgeDurum.SILINEBILIR:
            raise BelgeSilHatasi(
                f"'{b.durum}' durumundaki belge silinemez — önce iptal edin.",
                'SILINEMEZ_DURUM',
            )

        if b.sirket_id and b.tarih and donem_kilitli_mi(b.sirket_id, b.tarih):
            raise BelgeSilHatasi(
                f"{b.tarih.strftime('%B %Y')} dönemi kilitli — belge silinemez.",
                'DONEM_KILITLI',
            )

        from core.tipler import BelgeTip
        if b.belge_tip in BelgeTip.DONUSUM:
            hedef_tip = BelgeTip.DONUSUM[b.belge_tip]
            hedef_ad  = BelgeTip.ADLAR[hedef_tip]
            turetilmis = BelgeBaslik.query.filter_by(
                kaynak_belge_id=belge_id, belge_tip=hedef_tip
            ).filter(BelgeBaslik.durum.notin_([BelgeDurum.IPTAL, BelgeDurum.TASLAK])).count()
            if turetilmis:
                raise BelgeSilHatasi(
                    f"{turetilmis} aktif {hedef_ad} var — önce onları silin/iptal edin.",
                    'TURETILMIS_VAR',
                )

        cari_sil('FATURA', belge_id)
        stok_sil(belge_no=b.belge_no)
        db.session.delete(b)
        db.session.commit()


# ════════════════════════════════════════════════════════════
#  İRSALİYE BİRLEŞTİRME
# ════════════════════════════════════════════════════════════

def irsaliye_fatura_birlestir(irsaliye_idler: list, sirket_id_varsayilan: int = None) -> BelgeBaslik:
    from addons.sirket.services import yeni_belge_no
    from datetime import date as _date

    irsaliyeler = BelgeBaslik.query.filter(
        BelgeBaslik.id.in_(irsaliye_idler),
        BelgeBaslik.durum == BelgeDurum.ONAYLANDI,
    ).all()
    if not irsaliyeler:
        raise ValueError('Geçerli irsaliye bulunamadı.')

    k0 = irsaliyeler[0]
    fatura = BelgeBaslik(
        belge_tip='FATURA', belge_no=yeni_belge_no('FATURA', k0.cari_tip, k0.sirket_id),
        tarih=_date.today(), cari_id=k0.cari_id, cari_tip=k0.cari_tip,
        aciklama=', '.join(i.belge_no for i in irsaliyeler),
        durum=BelgeDurum.TASLAK, kaynak_belge_id=k0.id,
        depo_id=k0.depo_id, sirket_id=k0.sirket_id,
    )
    db.session.add(fatura)
    db.session.flush()

    sira = 1
    for irs in irsaliyeler:
        for s in irs.satirlar:
            db.session.add(BelgeSatir(
                baslik_id=fatura.id, sira_no=sira, stok_id=s.stok_id,
                aciklama=f"{irs.belge_no}: {s.aciklama or (s.stok.ad if s.stok else '')}",
                miktar=s.miktar, birim_id=s.birim_id, birim_fiyat=s.birim_fiyat,
                iskonto_oran=s.iskonto_oran, kdv_orani=s.kdv_orani,
                kdvsiz_tutar=s.kdvsiz_tutar, kdv_tutar=s.kdv_tutar, kdvli_tutar=s.kdvli_tutar,
            ))
            sira += 1

    fatura.evrak_no = ', '.join(i.belge_no for i in irsaliyeler)
    baslik_toplamla(fatura)
    db.session.commit()
    return fatura
