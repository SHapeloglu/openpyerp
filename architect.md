# architect.md — OpenPyERP Mimari Referansı

Bu dosya, `GELISTIRME_DOKUMANI.md`'nin mimari bölümlerinin hızlı-referans özetidir. Detaylı gerekçeler ve örnek kodlar için o dosyaya bakın.

## Katmanlar
[Tarayıcı]
│
▼
routes.py → HTTP, form okuma, yönlendirme, commit BURADA yapılır
│
▼
core/context.py → aktif şirket/cari kimliğini session'dan çeker
│
▼
services.py → iş mantığı, DB'ye yazar, COMMIT YAPMAZ
│
▼
core/workflow.py → (varsa) durum geçişi: guard → action → audit olayı
│
▼
core/hooks.py → emit ile diğer addon'ları haberdar eder
│
▼
routes.py → db.session.commit(), flash + redirect

**Neden servis katmanı commit yapmaz?** Bir istek birden fazla servis fonksiyonunu sırayla çağırabilir (fatura → cari hareketi → stok hareketi). Hepsi tek transaction'da olmalı; ortada hata olursa hepsi rollback edilmeli. Commit kararı yalnızca en üstteki `routes.py`'nindir.

## Core Bileşenleri

| Dosya | Görev |
|---|---|
| `core/extensions.py` | Tekil `db` (SQLAlchemy) ve `csrf` nesneleri |
| `core/registry.py` | Addon yükleme motoru + şema genişletme (`extend_model`) |
| `core/hooks.py` | Olay yayınlama/dinleme (`on`/`emit`, `on_commit`/`emit_after_commit`) |
| `core/workflow.py` | Durum makinesi (`Workflow`, `Gecis`) |
| `core/auth.py` | `login_gerekli`, `admin_gerekli`, `yazma_gerekli` decorator'ları |
| `core/tipler.py` | Sabit setler (`BelgeTip`, `Durum`, `Rol`...) |
| `core/para.py` | Decimal tabanlı parasal yuvarlama (framework'ten bağımsız) |
| `core/context.py` | Session bağlamlı sorgular (aktif şirket/cari/stok) |
| `core/views.py` | Generic `FormView` / `ListView` ekran konfigürasyonu |

**Tek yönlü kural:** `core/` asla `addons/*`'ı import etmez. Addon'lar core'u kullanır, core addon'ları bilmez (istisna: `core/auth.py`, `core/context.py` — session/request bağlamlı yardımcılar).

## Addon Anatomisi
addons/<modul>/
manifest.py → ad, açıklama, bağımlılıklar, sürüm
models.py → SQLAlchemy modelleri
services.py → iş mantığı (commit YOK)
routes.py → Flask Blueprint + endpoint'ler
views.py → FormView/ListView konfigürasyonu
workflow.py → (varsa) durum makinesi tanımı
extends.py → (varsa) başka addon modelini genişletme
listeners.py → (varsa) hook dinleyicileri
migrations/ → (varsa) addon'a özel Alembic migration'ları
templates/<modul>/→ addon'a özel HTML şablonları

Yükleme sırası `core/registry.py` tarafından **topolojik sıralama** ile belirlenir (bağımlılık önce yüklenir). Her addon için sıra: `extends.py` → `routes.py` (`bp` blueprint kaydı) → `listeners.py`.

## Mevcut Addon'lar ve Bağımlılıkları

| Addon | İş Alanı | Not |
|---|---|---|
| `sirket` | Çok şirketli yapı, depo, numara serisi, dönem kilidi | Temel bağımlılık |
| `birim` | Ortak birim tanımları | Temel bağımlılık |
| `cari` | Alıcı/satıcı bakiye, adres, iletişim | |
| `stok` | Malzeme/hizmet kartları, giriş-çıkış | |
| `belge` | Talep → Sipariş → İrsaliye → Fatura zinciri | `sirket`, `birim`, `cari`, `stok`'a bağımlı |
| `finans` | Kasa, banka, çek/senet | |
| `uretim` | Üretim fişi, reçete | |
| `personel` | Personel, izin, puantaj | |
| `rapor` | Gelir/gider, cari bakiye, vade analizi, stok durumu | |
| `eticaret` | WooCommerce/Trendyol entegrasyonu, platform ID, QR barkod | `stok`'u `extend_model()` ile genişletir |
| `ayarlar` | Kullanıcı, rol, sistem ayarları | |
| `dashboard` | Özet panel | |

## Genişletme Mekanizması

Bir addon başka bir addon'un modeline kolon eklemek isterse (Odoo'daki `_inherit` karşılığı):

```python
extend_model(StokKarti, StokKartiEticaretMixin)
```

⚠️ Bu sadece Python tarafını günceller — DB'de fiziksel kolon için ayrıca Alembic migration şart. İkisi birlikte gereklidir.

## Durum Makinesi Akışı

1. Geçiş tanımlı mı? → değilse `GecersizGecisHatasi`
2. `guard` çalışır → iş kuralına uymuyorsa `GuardReddiHatasi`, **DB'ye hiçbir şey yazılmaz**
3. Durum alanı güncellenir
4. `action` çalışır (yan etkiler: stok/cari hareketi vb.)
5. `workflow.gecis` olayı yayınlanır (audit/bildirim)

Guard = sadece kontrol. Action = yazma + yan etki. Karıştırılmamalı.

