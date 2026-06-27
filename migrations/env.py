"""
migrations/env.py — Alembic ortam konfigürasyonu

NEDEN BU DOSYA KRİTİK?
    Alembic'in `--autogenerate` özelliği (mevcut model sınıflarını okuyup
    gereken ALTER TABLE komutlarını otomatik üretme) çalışabilmesi için
    SQLAlchemy metadata'yı burada bulması gerekir.

    Flask-Migrate (flask_migrate paketi) bunu otomatik yapar ama biz
    bağımlılıkları minimumda tutmak için doğrudan Alembic kullanıyoruz.
    Bu dosya Flask-Migrate'in yaptığını elle gerçekleştiriyor:
        1. Flask app context'i oluştur
        2. Tüm modelleri import et (metadata'nın dolu olması için)
        3. db.metadata'yı Alembic'e ver
        4. Alembic migration'ı çalıştır

KULLANIM:
    # İlk kurulum — tüm tabloları oluşturan migration:
    alembic revision --autogenerate -m "ilk_kurulum"
    alembic upgrade head

    # Model değişikliği sonrası:
    alembic revision --autogenerate -m "belge_baslik_sevk_durumu_eklendi"
    alembic upgrade head

    # Addon'a özgü migration (eticaret gibi):
    # addons/eticaret/migrations/ altındaki dosyayı el ile yazın
    # (bkz. addons/eticaret/migrations/0001_stok_karti_eticaret_alanlari.py)
"""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Proje kökünü Python yoluna ekle ─────────────────────────────────────────
# Bu olmadan `from core.extensions import db` çalışmaz
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ── Alembic config nesnesi ───────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Flask app + modelleri yükle ──────────────────────────────────────────────
# NEDEN BURADA?: Alembic autogenerate için SQLAlchemy'nin tüm model
# sınıflarını tanımış olması gerekir. Bunu garantilemenin tek yolu
# app factory'yi çalıştırmak — o da _tum_modelleri_import_et() çağırır.
from app import create_app
from core.extensions import db

flask_app = create_app({
    'SQLALCHEMY_DATABASE_URI': os.environ.get(
        'DATABASE_URL', 'mysql+pymysql://root:@localhost/openpyerp'
    ),
    'TESTING': False,
    'WTF_CSRF_ENABLED': False,
})

# Alembic'e metadata'yı ver — tüm tablolar burada tanımlı
target_metadata = db.metadata


# ── Offline mod (DB bağlantısı olmadan SQL üret) ─────────────────────────────
def run_migrations_offline() -> None:
    """SQL komutlarını DB'ye bağlanmadan dosyaya yazar.

    Kullanım: `alembic upgrade head --sql > migration.sql`
    Üretim ortamlarında DBA'nın onayından geçirmek için idealdir.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # MariaDB/MySQL için batch mode — ALTER TABLE desteği
        render_as_batch=True,
        compare_type=True,      # Kolon tipi değişikliklerini algıla
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mod (DB'ye doğrudan bağlan ve uygula) ─────────────────────────────
def run_migrations_online() -> None:
    """Gerçek DB bağlantısıyla migration'ları çalıştırır.

    `pool_pre_ping=True`: Ölü bağlantıları migration öncesi tespit eder.
    `poolclass=NullPool`: Migration için connection pool gereksiz.
    """
    with flask_app.app_context():
        connectable = db.engine

        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                render_as_batch=False,     # PostgreSQL native ALTER TABLE destekler
                compare_type=True,         # VARCHAR(20) → VARCHAR(30) gibi değişiklikleri algıla
                compare_server_default=True,
                # Alembic'in takip etmemesi gereken tablolar (ör. dış sistemden gelen)
                # exclude_tables=['log_table', 'temp_table'],
            )
            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
