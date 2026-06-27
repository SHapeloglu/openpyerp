# OpenPyERP — Geliştirici komutları
# PostgreSQL bağlantısı için önce ortam değişkenini ayarla:
#   export DATABASE_URL=postgresql+psycopg2://openpyerp_user:sifre@localhost/openpyerp
#
# İlk kurulum:
#   make kurulum
#   make db-olustur
#   make seed
#   make calistir

.PHONY: kurulum db-olustur db-migrate db-geri-al seed calistir test temizle

# ── Kurulum ────────────────────────────────────────────────────────────────
kurulum:
	pip install -r requirements.txt
	@echo "✓ Bağımlılıklar kuruldu"

# ── Veritabanı ─────────────────────────────────────────────────────────────
db-olustur:
	@echo "→ Migration uygulanıyor..."
	alembic upgrade head
	@echo "✓ Veritabanı şeması oluşturuldu"

db-migrate:
	@read -p "Migration açıklaması: " msg; \
	alembic revision --autogenerate -m "$$msg"
	@echo "✓ Migration dosyası oluşturuldu → migrations/versions/"

db-geri-al:
	alembic downgrade -1
	@echo "✓ Bir adım geri alındı"

db-tarihce:
	alembic history --verbose

db-mevcut:
	alembic current

# ── Başlangıç verisi ────────────────────────────────────────────────────────
seed:
	python seed.py

# ── Uygulama ────────────────────────────────────────────────────────────────
calistir:
	FLASK_APP=app.py FLASK_DEBUG=1 flask run --port 5000

calistir-prod:
	gunicorn "app:create_app()" --workers 4 --bind 0.0.0.0:8000

# ── Test ────────────────────────────────────────────────────────────────────
test:
	pytest tests/ -v

test-unit:
	pytest tests/unit/ -v

test-entegrasyon:
	pytest tests/integration/ -v

test-kapsam:
	pytest tests/ --cov=. --cov-report=html
	@echo "✓ Kapsam raporu → htmlcov/index.html"

# ── Temizlik ────────────────────────────────────────────────────────────────
temizle:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "✓ Cache temizlendi"

# ── Tam sıfırlama (dikkat!) ─────────────────────────────────────────────────
sifirla-db:
	@echo "⚠  Bu işlem tüm veritabanını siler!"
	@read -p "Devam etmek için 'evet' yazın: " onay; \
	if [ "$$onay" = "evet" ]; then \
		alembic downgrade base && alembic upgrade head && python seed.py; \
	else \
		echo "İptal edildi."; \
	fi
