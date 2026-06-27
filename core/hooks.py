"""
core/hooks.py — Hafif olay/sinyal sistemi (ERPNext'in before_save / on_submit'i)

NEDEN BU MODÜL VAR?
    CariMatik'te (eski app.py) "Fatura kaydedilince stok hareketi oluştur" gibi
    yan etkiler, ilgili route fonksiyonunun İÇİNE doğrudan yazılıydı. Bu, iki
    soruna yol açıyordu:

    1. addons/belge servisi, addons/stok ve addons/finans modellerini DOĞRUDAN
       import etmek zorunda kalıyordu → modüller arası sıkı bağımlılık (coupling).
       Üretim modülü eklendiğinde (üretim onayı da stok hareketi yaratıyor),
       aynı mantığın bir kopyası tekrar yazıldı (bkz. eski app.py
       uretim_fisi_onayla_islemi — satir_hesapla ve StokHareket oluşturma
       mantığının neredeyse aynısı).
    2. Yan etkiyi test etmek için ana işlemi de test etmek gerekiyordu.

    ERPNext bu sorunu `hooks.py` + doctype olayları (before_insert, on_submit,
    on_cancel...) ile çözer: bir doctype'ın yaşam döngüsü olayına, başka bir
    modül kod ekleyebilir — doctype'ın kendisi o modülü hiç bilmez.

    Bu modül, aynı prensibi minimal bir "sinyal" (publish/subscribe) deseniyle
    uygular. Tam bir event-bus / message-queue DEĞİLDIR — senkron, in-process,
    aynı DB transaction'ı içinde çalışan basit bir çağrı zinciridir.

KULLANIM:
    # addons/stok/listeners.py içinde — belge onaylanınca stok hareketi üret:
    from core.hooks import on

    @on('belge.onaylandi')
    def stok_hareketi_olustur(belge, **kwargs):
        ...

    # addons/belge/services.py içinde — belge onaylandığında olayı yayınla:
    from core.hooks import emit
    emit('belge.onaylandi', belge=baslik)

ÖNEMLİ SINIRLAMA:
    Dinleyiciler (listener) AYNI DB transaction'ı içinde çalışır. Bir dinleyici
    exception fırlatırsa, tüm transaction (ana işlem dahil) rollback olur. Bu
    BİLİNÇLİ bir tercih: "fatura kaydedildi ama stok hareketi oluşmadı" gibi
    tutarsız durumları engeller. Asenkron/kuyruk tabanlı hook'lar (örn. mail
    gönderimi) bu sistemin kapsamı DIŞINDADIR — onlar için after_commit
    kullanılır (bkz. aşağıdaki AFTER_COMMIT_OLAYLARI).
"""
from collections import defaultdict
from typing import Callable, DefaultDict, List

_dinleyiciler: DefaultDict[str, List[Callable]] = defaultdict(list)

# after_commit olayları — DB commit BAŞARILI olduktan sonra çalışır (mail,
# webhook, dış API bildirimi gibi "geri alınması gerekmeyen" yan etkiler için).
_commit_sonrasi_dinleyiciler: DefaultDict[str, List[Callable]] = defaultdict(list)


def on(olay_adi: str):
    """Decorator — bir olaya dinleyici (listener) kaydeder.

    Örnek:
        @on('belge.onaylandi')
        def fn(belge, **kwargs): ...
    """
    def kaydet(fn: Callable) -> Callable:
        _dinleyiciler[olay_adi].append(fn)
        return fn
    return kaydet


def on_commit(olay_adi: str):
    """Decorator — commit SONRASI çalışacak bir dinleyici kaydeder."""
    def kaydet(fn: Callable) -> Callable:
        _commit_sonrasi_dinleyiciler[olay_adi].append(fn)
        return fn
    return kaydet


def emit(olay_adi: str, **kwargs):
    """Bir olayı yayınlar — kayıtlı tüm dinleyicileri SIRAYLA, SENKRON çağırır.

    Bir dinleyici hata fırlatırsa yayılır (propagate) — bu kasıtlıdır, çağıran
    servis db.session.rollback() yapabilsin diye.
    """
    for fn in _dinleyiciler.get(olay_adi, []):
        fn(**kwargs)


def emit_after_commit(olay_adi: str, **kwargs):
    """Commit sonrası çalışacak dinleyicileri tetikler.

    Servis katmanı db.session.commit() çağrısından SONRA bunu çağırmalıdır.
    Buradaki hatalar ana işlemi etkilememeli — bu yüzden çağıran taraf
    (genellikle routes.py) bunu try/except ile sarmalı ve sadece loglamalı.
    """
    for fn in _commit_sonrasi_dinleyiciler.get(olay_adi, []):
        fn(**kwargs)


def dinleyicileri_temizle():
    """Test izolasyonu için — testlerde her test öncesi/sonrası çağrılabilir."""
    _dinleyiciler.clear()
    _commit_sonrasi_dinleyiciler.clear()
