# OpenPyERP

Türkçe, modüler ve açık kaynak bir ERP (Kurumsal Kaynak Planlama) sistemi. Flask + PostgreSQL üzerine, Odoo'nun addon mantığından esinlenerek geliştirilmiştir: her iş alanı (stok, cari, finans, üretim...) bağımsız bir addon olarak yaşar ve birbirine bağımlılık bildirerek doğru sırada yüklenir.

## Özellikler

- **Modüler addon mimarisi** — her modül kendi `__manifest__.py`'ı ile bağımlılıklarını bildirir, `core/registry.py` bunları doğru sırayla yükler.
- **Çok şirketli yapı** (`sirket`) — şirket, depo, numara serisi, dönem kilidi.
- **Cari hesap yönetimi** (`cari`) — alıcı/satıcı bakiye, adres, iletişim.
- **Stok** (`stok`) — malzeme/hizmet kartları, giriş-çıkış hareketleri.
- **Belge zinciri** (`belge`) — Talep → Sipariş → İrsaliye → Fatura dönüşüm akışı.
- **Finans** (`finans`) — kasa, banka, çek/senet yönetimi.
- **Üretim** (`uretim`) — üretim fişi ve reçete.
- **Personel** (`personel`) — personel, izin, puantaj.
- **Raporlama** (`rapor`) — gelir/gider, cari bakiye, vade analizi, stok durumu.
- **E-Ticaret entegrasyonu** (`eticaret`) — WooCommerce / Trendyol, stok kartına platform ID ve QR barkod desteği.
- **Dashboard** — özet panel.
- **Ayarlar** (`ayarlar`) — kullanıcı, rol, sistem ayarları.

## Mimari

```
app.py              → Flask uygulama fabrikası (create_app)
core/                → addon yükleme, auth, workflow, ortak tipler
addons/<modul>/      → her iş alanı kendi modeli, route'u, şablonuyla
migrations/          → Alembic veritabanı migrationları
templates/           → ortak Jinja şablonları (liste, form, base)
tests/               → unit ve entegrasyon testleri
deploy/              → systemd, nginx, kurulum script'i
```

Her addon klasörü kendi `__manifest__.py` dosyasında adını, açıklamasını ve bağımlı olduğu diğer addon'ları bildirir. Örneğin `belge` addon'u; `sirket`, `birim`, `cari`, `stok` addon'ları yüklenmeden çalışmaz.

## Teknoloji

- **Flask** 3.x — web framework
- **Flask-SQLAlchemy** — ORM
- **Flask-WTF** — form/CSRF koruması
- **PostgreSQL** + **psycopg2** — veritabanı
- **Alembic** — migration yönetimi
- **Gunicorn** — production WSGI sunucusu
- **pytest** — test

## Kurulum (geliştirme ortamı)

```bash
git clone https://github.com/SHapeloglu/openpyerp.git
cd openpyerp

python3 -m venv venv
source venv/bin/activate
make kurulum          # pip install -r requirements.txt

export DATABASE_URL=postgresql+psycopg2://openpyerp_user:sifre@localhost/openpyerp

make db-olustur        # alembic upgrade head
make seed              # başlangıç verisi
make calistir          # flask run --port 5000
```

Uygulama `http://localhost:5000` üzerinden erişilebilir.

## Production Kurulumu (Contabo / Ubuntu)

`deploy/kurulum.sh` script'i; sistem paketlerini, virtualenv'i, veritabanı migration'larını, systemd servisini ve nginx konfigürasyonunu otomatik kurar.

```bash
sudo cp deploy/openpyerp.env.example /etc/openpyerp.env
sudo nano /etc/openpyerp.env     # gerçek SECRET_KEY ve DATABASE_URL'i gir
sudo chmod +x deploy/kurulum.sh
sudo ./deploy/kurulum.sh
```

> ⚠️ `/etc/openpyerp.env` dosyasını asla repoya commit etmeyin. Sadece `.example` uzantılı şablon dosyası repodadır.

Servis durumu ve loglar:
```bash
systemctl status openpyerp
journalctl -u openpyerp -f
tail -f /var/log/openpyerp/error.log
```

## Geliştirici komutları (Makefile)

| Komut | Açıklama |
|---|---|
| `make kurulum` | Bağımlılıkları kurar |
| `make db-olustur` | Migration'ları uygular |
| `make db-migrate` | Yeni migration dosyası oluşturur |
| `make db-geri-al` | Bir migration adımını geri alır |
| `make seed` | Başlangıç verisini yükler |
| `make calistir` | Geliştirme sunucusunu başlatır |
| `make calistir-prod` | Gunicorn ile production modda çalıştırır |
| `make test` | Tüm testleri çalıştırır |
| `make test-unit` / `make test-entegrasyon` | Unit / entegrasyon testleri |
| `make test-kapsam` | Coverage raporu (`htmlcov/index.html`) |
| `make temizle` | `__pycache__` ve `.pyc` dosyalarını siler |

## Test

```bash
make test
# veya
pytest tests/ -v
```

## Lisans

Bu projenin lisans bilgisi henüz belirtilmemiştir.
