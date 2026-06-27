"""
core/workflow.py — Formel durum makinesi motoru

TRYTON'DAN İLHAM, FLASK/SQLALCHEMY'YE UYARLANMIŞ:
    Tryton'da her model Workflow mixin'ini extend eder ve geçişleri
    sınıf düzeyinde bildirir:

        class Invoice(Workflow, ModelSQL):
            _transitions = {('draft', 'posted'), ('posted', 'cancelled')}

    Burada aynı prensibi daha açık, daha test edilebilir bir API ile
    kuruyoruz. Fark: Tryton'da geçiş kontrolü ORM katmanında otomatik
    tetiklenir; burada servis katmanı bilinçli olarak gecer() çağırır —
    "açık" ama "sihirsiz" tercih.

TEMEL KAVRAMLAR:
    Durum       — modelin o anki halini temsil eden string ('TASLAK', 'ACIK'...)
    Geçiş       — (kaynak_durum, hedef_durum) çifti + opsiyonel guard/action
    Guard       — geçişin izin verilip verilmediğini dönen fonksiyon
    Action      — geçiş gerçekleşince çağrılan yan etki (hook'a yayın dahil)
    Audit trail — kim, ne zaman, hangi geçişi yaptı — otomatik kaydedilir

KULLANIM:
    # addons/belge/workflow.py içinde tanımlanır:
    BELGE_WF = Workflow(
        durumlar=['TASLAK', 'ACIK', 'ONAYLANDI', 'IPTAL'],
        gecisler=[
            Gecis('TASLAK',    'ACIK',       isim='Aç'),
            Gecis('ACIK',      'ONAYLANDI',  isim='Onayla',
                  guard=fatura_onay_kontrolu, action=cari_stok_hareketi_olustur),
            Gecis('ACIK',      'IPTAL',      isim='İptal Et',
                  action=hareketleri_geri_al),
            Gecis('ONAYLANDI', 'IPTAL',      isim='İptal Et',
                  action=hareketleri_geri_al),
        ],
        baslangic='TASLAK',
        durum_alani='durum',   # model üzerindeki kolon adı
    )

    # services.py içinde kullanılır:
    BELGE_WF.gecer(belge, 'ONAYLANDI', kullanici_id=g.kullanici_id)
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List, Optional, Any


# ── İstisna sınıfları ──────────────────────────────────────────────────────

class GecersizGecisHatasi(Exception):
    """İzin verilmeyen durum geçişi talep edildiğinde fırlatılır."""
    def __init__(self, mevcut, hedef, izin_verilenler=None):
        self.mevcut = mevcut
        self.hedef = hedef
        mesaj = f"'{mevcut}' → '{hedef}' geçişi bu iş akışında tanımlı değil."
        if izin_verilenler:
            secenekler = ', '.join(f"'{d}'" for d in izin_verilenler)
            mesaj += f" '{mevcut}' durumundan izin verilenler: {secenekler}."
        super().__init__(mesaj)


class GuardReddiHatasi(Exception):
    """Guard fonksiyonu geçişi reddettiğinde fırlatılır."""
    def __init__(self, mesaj, kod=None):
        self.kod = kod
        super().__init__(mesaj)


# ── Geçiş tanımı ──────────────────────────────────────────────────────────

@dataclass
class Gecis:
    """Bir durum geçişinin tüm bilgisini taşıyan veri sınıfı.

    kaynak     — geçişin başladığı durum
    hedef      — geçişin ulaştığı durum
    isim       — kullanıcıya gösterilecek eylem adı ('Onayla', 'İptal Et'...)
    guard      — fn(nesne, **ctx) → None | raises GuardReddiHatasi
                 Geçiş öncesi iş kuralı kontrolü. None döndürürse geçiş devam
                 eder; GuardReddiHatasi fırlatırsa engellenir. DB'ye yazmaz.
    action     — fn(nesne, **ctx) → None
                 Geçiş gerçekleşince çağrılan yan etki. DB'ye yazabilir ama
                 commit YAPMAZ — çağıran transaction'a katılır.
    """
    kaynak: str
    hedef: str
    isim: str = ''
    guard: Optional[Callable] = None
    action: Optional[Callable] = None


# ── Audit kaydı ───────────────────────────────────────────────────────────

@dataclass
class DurumGecisKaydi:
    """Bir geçişin kim tarafından, ne zaman gerçekleştirildiğinin kaydı.

    Bu nesne DB'ye yazılmaz (henüz) — core/hooks.py üzerinden
    'workflow.gecis' olayına yayınlanır. İleride addons/audit/models.py
    eklenirse o addon bu olayı dinleyip tabloya yazabilir:

        @on('workflow.gecis')
        def audit_yaz(kayit: DurumGecisKaydi, **_):
            AuditLog(model=kayit.model_adi, ...).save()
    """
    model_adi: str
    nesne_id: Any
    eski_durum: str
    yeni_durum: str
    gecis_ismi: str
    kullanici_id: Optional[int]
    zaman: datetime = field(default_factory=datetime.now)


# ── Workflow motoru ────────────────────────────────────────────────────────

class Workflow:
    """Bir model için formel durum makinesi.

    Özellikler:
    - Geçerliliği önce doğrular (GecersizGecisHatasi), sonra guard çağırır
    - Guard başarılı olursa durum alanını günceller
    - Action çağırır (yan etkiler — stok, cari hareketi vb.)
    - 'workflow.gecis' olayını yayınlar (audit, bildirim vb. için)
    - Commit YAPMAZ — servis katmanı ne zaman commit yapacağına karar verir

    Tryton'dan fark: Tryton'da geçişler ORM üzerinde otomatik tetiklenir
    (@ModelView.button decorator). Burada servis katmanı bilinçli olarak
    wf.gecer() çağırır. Bu, test edilebilirliği artırır: geçişi test etmek
    için ORM mock'lamaya gerek yok, sadece wf.gecer(sahte_belge, 'ONAYLANDI').
    """

    def __init__(self, durumlar: List[str], gecisler: List[Gecis],
                 baslangic: str, durum_alani: str = 'durum'):
        self.durumlar = durumlar
        self.baslangic = baslangic
        self.durum_alani = durum_alani

        # Hızlı arama: (kaynak, hedef) → Gecis
        self._gecis_haritasi: dict[tuple, Gecis] = {}
        for g in gecisler:
            self._gecis_haritasi[(g.kaynak, g.hedef)] = g

        # Hızlı arama: kaynak → [hedef, ...] (UI butonları için)
        self._kaynak_hedefler: dict[str, List[str]] = {}
        for g in gecisler:
            self._kaynak_hedefler.setdefault(g.kaynak, []).append(g.hedef)

    # ── Durum okuma ───────────────────────────────────────────────────

    def mevcut_durum(self, nesne) -> str:
        return getattr(nesne, self.durum_alani)

    def mevcut_gecisler(self, nesne) -> List[Gecis]:
        """Nesnenin şu anki durumundan çıkabileceği geçişlerin listesi.

        UI katmanı bunu çağırarak hangi butonların gösterileceğini öğrenir —
        routes.py veya template'te durum string'i hardcode etmeye gerek kalmaz.
        """
        mevcut = self.mevcut_durum(nesne)
        hedefler = self._kaynak_hedefler.get(mevcut, [])
        return [self._gecis_haritasi[(mevcut, h)] for h in hedefler]

    def gecis_gecerli_mi(self, nesne, hedef_durum: str) -> bool:
        """Guard çalıştırmadan sadece geçişin tanımlı olup olmadığını kontrol eder."""
        mevcut = self.mevcut_durum(nesne)
        return (mevcut, hedef_durum) in self._gecis_haritasi

    # ── Geçiş motoru ──────────────────────────────────────────────────

    def gecer(self, nesne, hedef_durum: str,
              kullanici_id: Optional[int] = None, **ctx):
        """Nesneyi hedef_durum'a geçirir.

        Adımlar:
            1. Geçiş tanımlı mı? → GecersizGecisHatasi
            2. Guard başarılı mı? → GuardReddiHatasi
            3. Durum alanını güncelle
            4. Action çağır (yan etkiler)
            5. 'workflow.gecis' olayını yayınla (audit / bildirim)

        COMMIT YAPMAZ — çağıran servis kendi transaction'ını yönetir.
        """
        from core.hooks import emit

        mevcut = self.mevcut_durum(nesne)
        anahtar = (mevcut, hedef_durum)

        # ── 1) Geçiş tanımlı mı? ────────────────────────────────────
        if anahtar not in self._gecis_haritasi:
            izin_verilenler = self._kaynak_hedefler.get(mevcut, [])
            raise GecersizGecisHatasi(mevcut, hedef_durum, izin_verilenler)

        gecis = self._gecis_haritasi[anahtar]

        # ── 2) Guard kontrolü ────────────────────────────────────────
        if gecis.guard:
            gecis.guard(nesne, kullanici_id=kullanici_id, **ctx)

        # ── 3) Durum güncelle ────────────────────────────────────────
        setattr(nesne, self.durum_alani, hedef_durum)

        # ── 4) Action (yan etki) ─────────────────────────────────────
        if gecis.action:
            gecis.action(nesne, kullanici_id=kullanici_id, **ctx)

        # ── 5) Audit / bildirim olayı ────────────────────────────────
        kayit = DurumGecisKaydi(
            model_adi=type(nesne).__name__,
            nesne_id=getattr(nesne, 'id', None),
            eski_durum=mevcut,
            yeni_durum=hedef_durum,
            gecis_ismi=gecis.isim,
            kullanici_id=kullanici_id,
        )
        emit('workflow.gecis', kayit=kayit)
        return kayit
