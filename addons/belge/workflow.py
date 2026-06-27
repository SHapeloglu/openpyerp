"""
addons/belge/workflow.py — Belge yaşam döngüsü durum makinesi

Tüm durum geçişleri (guard + action) burada tanımlıdır.
services.py artık durum'u doğrudan yazmaz — BELGE_WF.gecer() çağırır.

Durum diyagramı:

         ┌──────────┐
    ──▶  │  TASLAK  │ ──▶ (kullanıcı Kaydet'e basınca)
         └──────────┘
               │  aç()
               ▼
         ┌──────────┐
         │   ACIK   │ ──────────────────────┐
         └──────────┘                       │
               │  onayla()                  │ iptal_et()
               ▼                            ▼
         ┌──────────┐              ┌──────────────┐
         │ONAYLANDI │──iptal_et()─▶│    IPTAL     │
         └──────────┘              └──────────────┘

Guard'lar exception fırlatırsa geçiş gerçekleşmez — DB'ye yazılmaz.
Action'lar geçiş gerçekleştikten SONRA çağrılır — commit YAPMAZ.
"""
from core.workflow import Workflow, Gecis, GuardReddiHatasi
from core.tipler import BelgeDurum, BelgeTip, CariTip


# ════════════════════════════════════════════════════════════
#  GUARD FONKSİYONLARI — geçiş öncesi iş kuralı kontrolü
# ════════════════════════════════════════════════════════════

def _guard_onay(belge, **ctx):
    """ACIK → ONAYLANDI geçişi için iş kuralı kontrolleri.

    Fatura onayında stok ve cari hareketleri oluşacak — ön koşullar sağlanmalı.
    Dönem kilidi, stok yeterliliği ve zorunlu alan kontrolleri burada.
    """
    from addons.sirket.services import donem_kilitli_mi

    # 1) Dönem kilidi
    if belge.sirket_id and donem_kilitli_mi(belge.sirket_id, belge.tarih):
        raise GuardReddiHatasi(
            f"{belge.tarih.strftime('%B %Y')} dönemi kilitli — onay yapılamaz.",
            kod='DONEM_KILITLI',
        )

    # 2) Faturada cari zorunlu
    if belge.belge_tip == BelgeTip.FATURA and not belge.cari_id:
        raise GuardReddiHatasi('Fatura onayı için cari seçilmeli.', kod='CARI_EKSIK')

    # 3) En az bir satır zorunlu
    if not belge.satirlar:
        raise GuardReddiHatasi('Onaylanacak belgede en az bir satır olmalı.', kod='SATIR_EKSIK')

    # 4) Fatura + satış → stok yeterliliği
    if belge.belge_tip == BelgeTip.FATURA and belge.cari_tip == CariTip.SATIS:
        from addons.stok.services import negatif_stok_kontrol, YetersizStokHatasi
        for satir in belge.satirlar:
            if satir.stok and satir.stok.tip == 'MALZEME':
                try:
                    negatif_stok_kontrol(satir.stok, float(satir.cevrilen_miktar or satir.miktar))
                except YetersizStokHatasi as e:
                    raise GuardReddiHatasi(str(e), kod='YETERSIZ_STOK') from e


def _guard_iptal(belge, **ctx):
    """ONAYLANDI → IPTAL için kontrol — türetilmiş aktif belge varsa engelle."""
    if belge.belge_tip in BelgeTip.DONUSUM:
        hedef_tip = BelgeTip.DONUSUM[belge.belge_tip]
        from addons.belge.models import BelgeBaslik
        from core.extensions import db
        aktif_turetilmis = db.session.query(BelgeBaslik).filter_by(
            kaynak_belge_id=belge.id, belge_tip=hedef_tip,
        ).filter(
            BelgeBaslik.durum.notin_([BelgeDurum.IPTAL, BelgeDurum.TASLAK])
        ).count()
        if aktif_turetilmis:
            hedef_ad = BelgeTip.ADLAR.get(hedef_tip, hedef_tip)
            raise GuardReddiHatasi(
                f"Bu belgeden türetilmiş {aktif_turetilmis} aktif {hedef_ad} var. "
                f"Önce {hedef_ad.lower()}(leri) iptal edin.",
                kod='TURETILMIS_VAR',
            )


# ════════════════════════════════════════════════════════════
#  ACTION FONKSİYONLARI — geçiş sonrası yan etkiler
# ════════════════════════════════════════════════════════════

def _action_onayla(belge, **ctx):
    """ONAYLANDI action — fatura onayında cari + stok hareketi oluşturur.

    İrsaliye onayında sadece sevk durumunu günceller (stok hareketi yoktur —
    stok etkisi fatura onayında gerçekleşir, bu tercih belge_tip'e göre
    değiştirilebilir: bazı şirketler irsaliyede stok düşmek ister).
    """
    if belge.belge_tip == BelgeTip.FATURA:
        _fatura_hareketleri_olustur(belge)
    elif belge.belge_tip == BelgeTip.IRSALIYE:
        from addons.belge.services import sevk_durumu_hesapla
        sevk_durumu_hesapla(belge)

    # Kaynak belgeyi ONAYLANDI yap (TASLAK dönüşüm faturası → kaynak sipariş onaylanır)
    if belge.kaynak_belge_id and belge.durum == BelgeDurum.TASLAK:
        from addons.belge.models import BelgeBaslik
        from core.extensions import db
        kaynak = db.session.get(BelgeBaslik, belge.kaynak_belge_id)
        if kaynak and kaynak.durum == BelgeDurum.ACIK:
            kaynak.durum = BelgeDurum.ONAYLANDI


def _action_iptal(belge, **ctx):
    """IPTAL action — cari ve stok hareketlerini geri alır."""
    from addons.cari.services import kaynak_hareketlerini_sil as cari_sil
    from addons.stok.services import kaynak_hareketlerini_sil as stok_sil
    cari_sil('FATURA', belge.id)
    stok_sil(belge_no=belge.belge_no)


def _fatura_hareketleri_olustur(belge):
    """Fatura onayında cari borç/alacak + stok giriş/çıkış hareketleri oluşturur."""
    from addons.cari.services import cari_hareket_olustur, kaynak_hareketlerini_sil as cari_sil
    from addons.stok.services import stok_hareketi_olustur, kaynak_hareketlerini_sil as stok_sil
    from core.tipler import CariTip

    # Önce eski hareketleri temizle (güncelleme senaryosu)
    cari_sil('FATURA', belge.id)
    stok_sil(belge_no=belge.belge_no)

    # Cari hareketi
    if belge.cari_id:
        hareket_tipi = CariTip.CARI_HAREKET[belge.cari_tip]
        cari_hareket_olustur(
            cari_id=belge.cari_id,
            tarih=belge.tarih,
            tutar=belge.toplam_kdvli,
            hareket_tipi=hareket_tipi,
            belge_no=belge.belge_no,
            aciklama=f"Fatura: {belge.belge_no}",
            kaynak_tip='FATURA',
            kaynak_id=belge.id,
        )

    # Stok hareketleri
    stok_hareket_tipi = CariTip.STOK_HAREKET[belge.cari_tip]
    for satir in belge.satirlar:
        if not satir.stok or satir.stok.tip != 'MALZEME':
            continue
        cevrilen = float(satir.cevrilen_miktar or satir.miktar)
        stok_hareketi_olustur(
            stok_id=satir.stok_id,
            tarih=belge.tarih,
            hareket_tipi=stok_hareket_tipi,
            miktar=float(satir.miktar),
            cevrilen_miktar=cevrilen,
            birim_id=satir.birim_id,
            birim_fiyat=float(satir.birim_fiyat),
            belge_no=belge.belge_no,
            aciklama=f"Fatura: {belge.belge_no}",
        )


# ════════════════════════════════════════════════════════════
#  WORKFLOW TANIMI — tüm geçişler burada kayıtlı
# ════════════════════════════════════════════════════════════

BELGE_WF = Workflow(
    durumlar=[
        BelgeDurum.TASLAK,
        BelgeDurum.ACIK,
        BelgeDurum.ONAYLANDI,
        BelgeDurum.IPTAL,
    ],
    gecisler=[
        Gecis(
            kaynak=BelgeDurum.TASLAK,
            hedef=BelgeDurum.ACIK,
            isim='Aç',
        ),
        Gecis(
            kaynak=BelgeDurum.ACIK,
            hedef=BelgeDurum.ONAYLANDI,
            isim='Onayla',
            guard=_guard_onay,
            action=_action_onayla,
        ),
        Gecis(
            kaynak=BelgeDurum.ACIK,
            hedef=BelgeDurum.IPTAL,
            isim='İptal Et',
            action=_action_iptal,
        ),
        Gecis(
            kaynak=BelgeDurum.ONAYLANDI,
            hedef=BelgeDurum.IPTAL,
            isim='İptal Et',
            guard=_guard_iptal,
            action=_action_iptal,
        ),
    ],
    baslangic=BelgeDurum.TASLAK,
    durum_alani='durum',
)
