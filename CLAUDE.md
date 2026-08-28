# CLAUDE.md

Bu dosya, bu repo üzerinde çalışırken Claude'un (Claude Code dahil) izlemesi gereken proje bağlamını ve kurallarını içerir.

## Proje

**OpenPyERP** — Türkçe, modüler, açık kaynak bir ERP sistemi. Flask + SQLAlchemy + PostgreSQL üzerine, Odoo'nun addon mimarisinden ilham alınarak geliştirilmiştir. Eski tek dosyalık bir uygulamanın (`app.py`, ~11.600 satır, kod içinde "CariMatik") modüler mimariye refactor edilmiş halidir.

## Teknoloji Yığını

- Flask 3.x, Flask-SQLAlchemy, Flask-WTF
- PostgreSQL + psycopg2
- Alembic (migration)
- Gunicorn (production)
- pytest (test)

## Dizin Yapısı (özet)
- app.py → Flask app factory (create_app)
- config.py → ortam değişkenlerinden okunan Config
- core/ → framework katmanı, addons/*'a bağımlı DEĞİL
- addons/<modul>/ → her iş alanı: models.py, services.py, routes.py, views.py, manifest.py
- migrations/ → ana Alembic zinciri
- templates/ → ortak Jinja şablonları
- tests/ → unit + integration
- deploy/ → systemd, nginx, kurulum script'i

## Kesin Kurallar (bunlara uymadan kod yazma)

1. **Commit sadece `routes.py`'de yapılır.** `services.py` asla `db.session.commit()` çağırmaz — sadece `db.session.add()` ile hazırlar.
2. **Para hesaplamalarında float kullanma.** `core/para.py` içindeki `para()` / `miktar_d()` fonksiyonlarını kullan (Decimal tabanlı).
3. **Yeni addon eklerken `core/registry.py` → `KAYITLI_ADDONLAR` listesine mutlaka ekle.** Unutulursa addon sessizce yüklenmez, hata da vermez — en sık yapılan hata budur.
4. **`services.py` içinde `from flask import session` kullanma.** Session/request bağlamı sadece `routes.py`'de okunur, servise parametre olarak geçirilir.
5. **`extend_model()` kullanıyorsan mutlaka eşlik eden bir Alembic migration da yaz.** Biri diğeri olmadan eksik kalır (Python'da alan var, DB'de kolon yok).
6. **Native DB ENUM kullanma.** `VARCHAR` + `core/tipler.py` içinde Python sabiti tercih edilir.
7. **Workflow guard'ları DB'ye yazmaz**, sadece kontrol edip exception fırlatır. Yazma işi `action` fonksiyonundadır.
8. **Yeni ekranlarda manuel HTML form yazma.** `core/views.py`'deki `FormView` / `ListView` mekanizmasını kullan.

## Sık Kullanılan Komutlar

```bash
make kurulum            # bağımlılıkları kur
make db-olustur          # alembic upgrade head
make db-migrate           # yeni migration oluştur
make seed                   # başlangıç verisi
make calistir                 # geliştirme sunucusu
make test                         # tüm testler
make test-kapsam                   # coverage raporu
```

## Güvenlik Notları

- Gerçek `SECRET_KEY` ve `DATABASE_URL` kodda/repoda ASLA yer almaz — `/etc/openpyerp.env` üzerinden yüklenir.
- `whatsapp_bi/env` dosyası gerçek anahtar/token içeriyorsa repoya girmemeli; sadece `.env.example` şablonları commit edilir.
- Repoya her yeni dosya eklerken `.gitignore`'ın `venv/`, `__pycache__/`, `*.pyc`, `*.env` (example hariç), `htmlcov/` kalemlerini kapsadığından emin ol.

## Detaylı Mimari

Veri akışı, hook sistemi, workflow motoru ve adım adım "yeni addon ekleme" rehberi için bkz. `GELISTIRME_DOKUMANI.md` ve `architect.md`.
