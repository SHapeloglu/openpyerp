# OpenPyERP — Geliştirme Dokümanı

Bu doküman OpenPyERP'e yeni katılan bir geliştiricinin (junior dahil) projeyi anlayıp, kod yazmaya, test eklemeye ve yeni bir modül (addon) oluşturmaya başlayabilmesi için yazılmıştır. Mimari kararların **neden** öyle alındığını da anlatır, çünkü "neden" bilmeden "nasıl"ı doğru uygulamak zordur.

---

## 1. Büyük Resim — Bu Proje Ne Yapıyor?

OpenPyERP, Türkçe bir ERP (Kurumsal Kaynak Planlama) sistemidir. Flask + SQLAlchemy + PostgreSQL üzerine kuruludur ve **Odoo'nun addon mimarisinden** ilham almıştır: her iş alanı (stok, cari, finans...) kendi kendine yeten bir "addon" (modül) olarak yaşar, bağımlılıklarını açıkça bildirir, ve bir registry bunları doğru sırayla yükler.

Proje, eskiden tek dosyaya yazılmış (`app.py`, ~11.600 satır) bir uygulamanın (kod içinde "CariMatik" olarak anılıyor) modüler bir mimariye **refactor edilmiş** halidir. Yorumlarda sık sık "eski app.py'de şöyleydi" gibi notlar göreceksiniz — bunlar kasıtlı bırakılmış, çünkü neden bu yapıya geçildiğini anlamak ileride benzer hatalara düşmemenizi sağlar.

### Temel felsefe: "Açık ama sihirsiz"

Projenin her köşesinde tekrar eden bir tercih var: Odoo/Tryton/ERPNext gibi olgun ERP'lerin yaptığı şeyi yapmak (modülerlik, durum makinesi, olay sistemi, şema genişletme) ama bunu **metaclass büyüsü veya gizli ORM hilesi olmadan**, sade Python ile yapmak. Bu, IDE desteğinin tam çalışması, hata ayıklamanın kolay olması ve testlerin Flask app'i ayağa kaldırmadan çalışabilmesi için tercih edilmiş.

---

## 2. Dizin Yapısı

```
app.py                  → Flask uygulama fabrikası (create_app)
config.py               → Config sınıfı, ortam değişkenlerinden okur
core/                    → Framework katmanı — HİÇBİR addon'a bağımlı değil
  extensions.py          → tek db (SQLAlchemy) ve csrf nesnesi
  registry.py            → addon yükleme motoru + şema extend mekanizması
  hooks.py               → olay/sinyal sistemi (publish/subscribe)
  workflow.py            → durum makinesi (Workflow/Gecis sınıfları)
  auth.py                → login_gerekli / admin_gerekli / yazma_gerekli decorator'ları
  tipler.py              → sabit setler (BelgeTip, Durum, Rol...) + kolon tipi kısayolları
  para.py                → Decimal tabanlı parasal yuvarlama (framework'e bağımsız, saf)
  context.py             → aktif şirket/cari/stok gibi session bağlamlı sorgular
  views.py               → generic form/liste ekran konfigürasyon sınıfları
addons/<modul>/          → her iş alanı
  __init__.py
  __manifest__.py         → ad, açıklama, bağımlılıklar, sürüm
  models.py               → SQLAlchemy modelleri
  services.py             → iş mantığı (DB yazar ama commit YAPMAZ)
  routes.py               → Flask Blueprint + HTTP endpoint'leri
  views.py                → FormView/ListView ekran konfigürasyonu
  workflow.py              → (varsa) durum makinesi tanımı
  extends.py               → (varsa) başka addon'un modelini genişletme
  migrations/               → (varsa) addon'a özel Alembic migration'ları
  templates/<modul>/         → addon'a özel HTML şablonları
migrations/              → ana Alembic migration zinciri
templates/                → ortak şablonlar (_form.html, _liste.html, base.html...)
tests/
  conftest.py             → pytest fixture'ları (app, db, client, sirket, cari...)
  unit/                    → framework'süz / hızlı testler
  integration/              → DB + Flask context gerektiren testler
deploy/                  → systemd servisi, nginx config, kurulum script'i
```

**Kural:** `core/` hiçbir zaman `addons/*`'ı import etmez (tek istisna: `core/auth.py` ve `core/context.py`, çünkü bunlar session/request bağlamlı yardımcılardır, saf framework kodu değildir — bkz. bölüm 4.6). Bu yön tek taraflıdır: addon'lar core'u kullanır, core addon'ları bilmez.

---

## 3. Veri Akışı — Bir İsteğin Yolculuğu

Tarayıcıdan gelen bir isteğin nasıl işlendiğini bilmek, her katmanın görevini anlamanın en hızlı yolu:

```
[Tarayıcı] → routes.py (HTTP, form okuma, yönlendirme)
                │
                ▼
           core/context.py (aktif şirket/cari kimliğini session'dan çek)
                │
                ▼
           services.py (iş mantığı, DB yazma — commit ETMEZ)
                │
                ▼
           core/workflow.py (varsa, durum geçişi: guard → action → audit olayı)
                │
                ▼
           core/hooks.py (emit ile başka addon'ları haberdar et)
                │
                ▼
           routes.py (db.session.commit(), kullanıcıya flash + redirect)
```

**Neden servis katmanı commit yapmaz?** Çünkü bir HTTP isteği birden fazla servis fonksiyonunu sırayla çağırabilir (örn. fatura kaydet → cari hareketi oluştur → stok hareketi oluştur). Hepsi TEK transaction'da olmalı: ortada bir hata olursa hepsi geri alınmalı (rollback). Commit kararını sadece en üstteki `routes.py` verir.

---

## 4. Temel Kavramlar (Core Katmanı)

### 4.1 Addon Registry (`core/registry.py`)

Her addon `__manifest__.py` dosyasında bağımlılıklarını bildirir:

```python
MANIFEST = {
    'ad': 'Finans',
    'aciklama': 'Kasa, banka, çek/senet yönetimi.',
    'bagimliliklar': ['sirket', 'cari'],
    'surum': '1.0.0',
}
```

`register_addons(app)` şu sırayla çalışır:
1. Tüm addon'ların manifest'lerini okur, bağımlılık haritası çıkarır.
2. **Topolojik sıralama** yapar (bağımlılık olan addon önce yüklenir).
3. Her addon için: önce `extends.py` (varsa, başka modelleri genişletme), sonra `routes.py`'deki `bp` Blueprint'i `app.register_blueprint()` ile kaydeder, sonra `listeners.py` (varsa, hook dinleyicileri) import edilir.

Yeni bir addon eklediğinizde **mutlaka** `core/registry.py` içindeki `KAYITLI_ADDONLAR` listesine adını eklemeniz gerekir, aksi halde addon hiç yüklenmez.

### 4.2 Şema Genişletme — `extend_model()`

Bir addon, başka bir addon'un modeline yeni kolon eklemek isterse (Odoo'daki `_inherit` karşılığı), `extend_model()` kullanılır:

```python
# addons/eticaret/models.py
class StokKartiEticaretMixin:
    barkod_qr = db.Column(db.String(200), nullable=True)

# addons/eticaret/extends.py
from core.registry import extend_model
from addons.stok.models import StokKarti
from addons.eticaret.models import StokKartiEticaretMixin
extend_model(StokKarti, StokKartiEticaretMixin)
```

⚠️ **Bu SADECE Python tarafını günceller.** Veritabanında fiziksel kolonun oluşması için `addons/eticaret/migrations/` altında ayrıca bir Alembic migration dosyası yazmanız gerekir. İkisi birlikte gereklidir — biri olmadan diğeri eksik kalır.

### 4.3 Hook Sistemi — Olay Yayınlama (`core/hooks.py`)

Modüller arası sıkı bağımlılığı (coupling) önlemek için kullanılır. Örnek: bir fatura onaylandığında stok hareketi oluşturulmalı ama `belge` addon'u `stok` addon'unun modelini doğrudan bilmek zorunda kalmamalı.

```python
# addons/stok/listeners.py — DİNLEYİCİ taraf
from core.hooks import on

@on('belge.onaylandi')
def stok_hareketi_olustur(belge, **kwargs):
    ...

# addons/belge/services.py — YAYINCI taraf
from core.hooks import emit
emit('belge.onaylandi', belge=baslik)
```

İki tür olay var:
- **`on` / `emit`** — AYNI DB transaction'ı içinde, senkron çalışır. Bir dinleyici hata fırlatırsa **tüm işlem** (ana işlem dahil) rollback olur. Bu bilinçli bir tercih: "fatura kaydedildi ama stok hareketi oluşmadı" gibi tutarsız durumları önler.
- **`on_commit` / `emit_after_commit`** — Commit BAŞARILI olduktan SONRA çalışır. Mail gönderme, webhook tetikleme gibi "geri alınması gerekmeyen" yan etkiler için kullanılır. Buradaki hatalar ana işlemi etkilememeli, çağıran taraf try/except ile loglamalıdır.

### 4.4 Workflow / Durum Makinesi (`core/workflow.py`)

Bir belgenin TASLAK → ACIK → ONAYLANDI → İPTAL gibi durumlar arası geçişini yöneten motor. Tryton'dan ilham alınmıştır ama geçiş tetiklemesi **bilinçli ve açık** — ORM otomasyonu yok.

```python
BELGE_WF = Workflow(
    durumlar=['TASLAK', 'ACIK', 'ONAYLANDI', 'IPTAL'],
    gecisler=[
        Gecis('ACIK', 'ONAYLANDI', isim='Onayla',
              guard=_guard_onay, action=_action_onay),
        Gecis('ACIK', 'IPTAL', isim='İptal Et', action=_action_iptal),
    ],
    baslangic='TASLAK',
    durum_alani='durum',
)

# servis katmanında kullanım:
BELGE_WF.gecer(belge, 'ONAYLANDI', kullanici_id=g.kullanici_id)
```

Her geçiş şu sırayı izler: (1) geçiş tanımlı mı kontrol et → tanımsızsa `GecersizGecisHatasi`, (2) `guard` fonksiyonunu çalıştır → iş kuralı uymuyorsa `GuardReddiHatasi` fırlatır ve **DB'ye hiçbir şey yazılmaz**, (3) durum alanını güncelle, (4) `action` fonksiyonunu çalıştır (yan etkiler — stok/cari hareketi gibi), (5) `workflow.gecis` olayını yayınla (audit/bildirim için).

**Guard ile Action'ı karıştırmayın:** Guard sadece kontrol eder, DB'ye yazmaz, exception fırlatabilir. Action yan etkiyi gerçekleştirir, exception fırlatmamalıdır (fırlatırsa zaten durum güncellenmiş olabilir, tutarsızlık riski).

### 4.5 Tip Sabitleri (`core/tipler.py`)

Durumlar, belge tipleri, roller gibi sabit kümeler **veritabanı ENUM'u olarak değil**, `VARCHAR + Python sabiti` olarak tutulur. Sebep: native ENUM (PostgreSQL `CREATE TYPE`) yeni değer eklemeyi zorlaştırır ve production'da kilitlenmeye sebep olabilir. Yeni bir durum eklemek istediğinizde sadece `core/tipler.py`'a sabit eklersiniz, migration gerekmez.

```python
class BelgeTip:
    TALEP = 'TALEP'
    SIPARIS = 'SIPARIS'
    TUMU = {TALEP, SIPARIS, ...}
    STOK_ETKILI = {IRSALIYE, FATURA}   # hangi tipler stok hareketi yaratır
    DONUSUM = {TALEP: SIPARIS, ...}     # dönüşüm zinciri
```

`D` sınıfı da sık kullanılan kolon tiplerini kısayol olarak sunar (`D.STR_30`, `D.PARA` = `Numeric(15,2)`, `D.MIKTAR` = `Numeric(15,4)`).

### 4.6 Para Hesaplama (`core/para.py`)

**Asla float ile parasal hesaplama yapmayın** — float'ın ikili temsili kuruş hatalarına yol açar (`0.1 + 0.2 != 0.3` problemi). Her zaman:

```python
from core.para import para, miktar_d
toplam = para(satir_tutari)        # Decimal, 0.01 hassasiyet, ROUND_HALF_UP
miktar = miktar_d(donusturulen)    # Decimal, 0.000001 hassasiyet (birim çevrimi için)
```

Bu modül framework'e bağımsızdır (Flask/SQLAlchemy import etmez) — bu sayede Flask app context kurmadan saf unit test yazılabilir.

### 4.7 İstek Bağlamı (`core/context.py`)

`session`'a bağımlı yardımcı fonksiyonlar burada yaşar (`aktif_sirket_al()`, `aktif_sirket_id()`, `sirketli_cariler()`...). **Kural:** `services.py` dosyaları `core.context`'i ASLA import etmez — `session`'ı bilmemelidir. Akış şöyle olmalı:

```
routes.py  → core.context'ten aktif_sirket_id() okur → services fonksiyonuna PARAMETRE olarak geçirir
services.py → session'ı hiç bilmez, sadece sirket_id (int) parametresi alır
```

Bu ayrım sayesinde servis fonksiyonları bir CLI script'inden veya testten, HTTP isteği olmadan da çağrılabilir.

### 4.8 Auth (`core/auth.py`)

Üç decorator: `login_gerekli` (giriş kontrolü), `admin_gerekli` (sadece ADMIN rolü), `yazma_gerekli` (SADECE_OKUMA rolünü engeller). Her addon route'u bunları kullanır:

```python
from core.auth import login_gerekli, yazma_gerekli

@bp.route('/yeni', methods=['GET', 'POST'])
@login_gerekli
@yazma_gerekli
def form(): ...
```

### 4.9 Generic View Konfigürasyonu (`core/views.py`)

Form ve liste ekranları **HTML şablonuyla değil, Python dataclass konfigürasyonuyla** tanımlanır. Yeni bir modül eklerken genelde `templates/` altına yeni dosya yazmanıza gerek kalmaz — `_form.html` ve `_liste.html` ortak şablonları bu konfigürasyonu okuyup formu otomatik render eder.

```python
CARI_FORM = FormView(
    baslik='Cari Hesap',
    alanlar=[
        Alan('kod', 'Cari Kodu', zorunlu=True, genislik=3),
        Alan('tip', 'Cari Tipi', tip='select', secenekler=CARI_TIP_SECENEKLER, genislik=3),
    ],
)
```

Desteklenen alan tipleri: `text`, `number`, `date`, `select`, `textarea`, `hidden`, `readonly`, `money`, `satir` (belge satır tablosu için özel bileşen).

---

## 5. Sıfırdan Yeni Bir Addon Oluşturma — Adım Adım

Diyelim ki **"Teklif"** adında yeni bir modül ekliyorsunuz (müşteriye fiyat teklifi oluşturma).

### Adım 1 — Klasör ve manifest

```bash
mkdir -p addons/teklif/templates/teklif
touch addons/teklif/__init__.py
```

```python
# addons/teklif/__manifest__.py
MANIFEST = {
    'ad': 'Teklif',
    'aciklama': 'Müşteriye fiyat teklifi oluşturma ve takip.',
    'bagimliliklar': ['sirket', 'cari', 'stok'],   # neye ihtiyacın varsa
    'surum': '1.0.0',
}
```

### Adım 2 — Modeli yaz (`addons/teklif/models.py`)

```python
from datetime import datetime
from core.extensions import db   # HER ZAMAN core.extensions'tan, app.py'den DEĞİL

class Teklif(db.Model):
    __tablename__ = 'teklif'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sirket_id = db.Column(db.Integer, db.ForeignKey('sirket.id', ondelete='RESTRICT'))
    cari_id = db.Column(db.Integer, db.ForeignKey('cari.id', ondelete='RESTRICT'))
    durum = db.Column(db.String(20), nullable=False, default='TASLAK')
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.now)
```

### Adım 3 — Migration yaz

```bash
export DATABASE_URL=postgresql+psycopg2://...
make db-migrate
# "Migration açıklaması: teklif tablosu eklendi" yazıp Enter'a basın
```

Bu, `migrations/versions/` altına otomatik bir dosya üretir. **Mutlaka açıp gözden geçirin** — autogenerate her zaman doğru tahmin etmeyebilir, özellikle index/constraint isimlerinde.

### Adım 4 — Servis katmanı (`addons/teklif/services.py`)

```python
from core.extensions import db
from addons.teklif.models import Teklif

def teklif_olustur(sirket_id, cari_id):
    t = Teklif(sirket_id=sirket_id, cari_id=cari_id)
    db.session.add(t)
    return t   # commit YAPMA — çağıran routes.py yapacak
```

### Adım 5 — Ekran konfigürasyonu (`addons/teklif/views.py`)

```python
from core.views import Alan, FormView, ListeKolon, ListView

TEKLIF_FORM = FormView(baslik='Teklif', alanlar=[
    Alan('cari_id', 'Müşteri', tip='select', zorunlu=True, genislik=6),
])
TEKLIF_LISTE = ListView(baslik='Teklifler', kolonlar=[
    ListeKolon('durum', 'Durum', badge=True, genislik='120px'),
])
```

### Adım 6 — Route'lar (`addons/teklif/routes.py`)

`addons/cari/routes.py`'yi şablon olarak kullanın — liste, form (yeni+düzenle birleşik), detay, sil (soft delete) deseni projede standarttır:

```python
from flask import Blueprint
from core.auth import login_gerekli, yazma_gerekli

bp = Blueprint('teklif', __name__, url_prefix='/teklif', template_folder='templates')

@bp.route('/')
@login_gerekli
def teklif_liste():
    ...
```

### Adım 7 — `core/registry.py`'ye ekle

```python
KAYITLI_ADDONLAR = [
    'sirket', 'birim', 'ayarlar',
    'cari', 'stok', 'finans',
    'belge', 'uretim', 'personel',
    'rapor', 'dashboard',
    'teklif',   # ← EKLENDİ
]
```

Bunu unutursanız addon hiç yüklenmez, hata da almazsınız — sessizce yok sayılır. **En sık yapılan hata budur.**

### Adım 8 — `app.py`'de modeli import et (gerekiyorsa)

Eğer modeliniz başka bir modelden `db.relationship` ile referans alınıyorsa, modelin mapper tarafından bilinmesi için `app.py` içindeki `_tum_modelleri_import_et()` fonksiyonuna ekleyin:

```python
def _tum_modelleri_import_et():
    ...
    import addons.teklif.models  # noqa
```

### Adım 9 — Test yazın

```python
# tests/unit/test_teklif.py
def test_teklif_olustur(db, sirket, cari):
    from addons.teklif.services import teklif_olustur
    t = teklif_olustur(sirket.id, cari.id)
    db.session.commit()
    assert t.durum == 'TASLAK'
```

---

## 6. Test Stratejisi

### 6.1 Katmanlar

- **`tests/unit/`** — Framework'e bağımsız saf mantık (örn. `core/para.py`, `core/workflow.py`). Flask app context'i gerektirmeyebilir.
- **`tests/integration/`** — DB + Flask context gerektiren akışlar (servis fonksiyonları, route'lar).

### 6.2 Fixture'lar (`tests/conftest.py`)

| Fixture | Açıklama |
|---|---|
| `app` | Session boyunca tek Flask app (SQLite in-memory ile) |
| `db` | Her test öncesi tüm tabloları temizler |
| `client` | HTTP endpoint testleri için Flask test client |
| `sirket`, `cari`, `birim`, `stok_karti` | Hazır temel veri fixture'ları |
| `hook_temizle` | Her testten sonra otomatik — hook dinleyicilerini sıfırlar (autouse) |

```python
def test_cari_bakiye(db, sirket):
    from addons.cari.models import Cari
    c = Cari(sirket_id=sirket.id, kod='C1', unvan='Test', tip='ALICI')
    db.session.add(c)
    db.session.commit()
    assert c.bakiye() == 0
```

### 6.3 Çalıştırma

```bash
make test                  # tüm testler
make test-unit              # sadece unit
make test-entegrasyon        # sadece entegrasyon
make test-kapsam              # coverage raporu → htmlcov/index.html
```

**Kural:** Yeni bir servis fonksiyonu veya guard yazdığınızda, en az happy-path + bir hata senaryosu (guard reddi gibi) test edin. Workflow guard'ları özellikle test edilmeli — para ile ilgili hata burada en pahalıya patlar.

---

## 7. Sık Yapılan Hatalar ve Kaçınma Yolları

| Hata | Neden sorun | Doğrusu |
|---|---|---|
| `services.py` içinde `db.session.commit()` çağırmak | İşlem yarıda kesilirse tutarsız veri kalır | Commit'i her zaman `routes.py`'de, en üst seviyede yap |
| Float ile para hesaplamak | Kuruş hataları (`0.1+0.2 != 0.3`) | `core.para.para()` / `miktar_d()` kullan |
| Yeni addon'u `KAYITLI_ADDONLAR`'a eklemeyi unutmak | Addon sessizce yüklenmez, hata da vermez | Adım 7'yi (bölüm 5) her addon için kontrol listesi yap |
| `services.py` içinde `from flask import session` yapmak | Servis fonksiyonu artık HTTP isteği dışında çağrılamaz, test edilemez | `core.context`'i sadece `routes.py`'de kullan, servise parametre geçir |
| `extend_model()` çağırıp migration yazmamak | Python'da alan var ama DB'de kolon yok → çalışma zamanı hatası | İkisini birlikte yap: `extend_model()` + Alembic migration |
| Native DB ENUM kullanmak | Yeni değer eklemek özel ALTER TABLE gerektirir | `VARCHAR` + `core/tipler.py`'da Python sabiti |
| Workflow guard'ı içinde DB'ye yazmak | Guard sadece kontrol katmanıdır, sızdırma riski | Guard sadece kontrol/raise yapar; yazma işini `action`'a bırak |
| Yeni modülde manuel HTML form yazmak | Var olan `_form.html`/`_liste.html` mekanizması atlanır | `core/views.py`'deki `FormView`/`ListView`'i kullan |

---

## 8. Geliştirici Komutları Özeti

```bash
make kurulum            # bağımlılıkları kur
make db-olustur          # alembic upgrade head
make db-migrate           # yeni migration oluştur (otomatik tespit)
make db-geri-al            # bir migration adımını geri al
make seed                   # başlangıç verisini yükle
make calistir                 # geliştirme sunucusu (flask run, debug açık)
make calistir-prod              # gunicorn ile production modda
make test                         # tüm testler
make temizle                       # __pycache__ / .pyc temizle
```

---

## 9. Production'a Dair Notlar

- Gerçek `SECRET_KEY` ve `DATABASE_URL` **kodda asla** yer almaz — `/etc/openpyerp.env` dosyasında tutulur, systemd bu dosyayı yükler. Repodaki `deploy/openpyerp.env.example` sadece şablondur, placeholder değerler içerir.
- `deploy/kurulum.sh`, sistem paketlerinden nginx konfigürasyonuna kadar tüm kurulumu otomatikleştirir. İlk kurulumda admin şifresi varsayılan olarak gelir — **hemen değiştirilmelidir** (script çıktısında bu uyarı zaten var).
- Loglar: `journalctl -u openpyerp -f` ve `/var/log/openpyerp/error.log` / `access.log`.
- Health check endpoint'i: `GET /health` — DB bağlantısını ve yüklenmiş addon listesini döner, monitoring için kullanılabilir.

---

## 10. Daha Fazla Bilgi İçin

Kodun kendisi en iyi dokümantasyondur — her `core/*.py` dosyasının başında, o tasarım kararının **neden** öyle alındığını anlatan uzun bir docstring vardır (genellikle Odoo/Tryton/ERPNext ile karşılaştırmalı). Bir kavramı tam anlamadıysanız önce ilgili dosyanın docstring'ine bakın; oradaki gerekçeler genellikle "bunu neden bu şekilde yapmadık" sorusuna da cevap verir.
