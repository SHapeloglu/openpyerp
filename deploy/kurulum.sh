#!/bin/bash
# deploy/kurulum.sh — Contabo sunucusuna OpenPyERP kurulumu
#
# Kullanım:
#   chmod +x deploy/kurulum.sh
#   sudo ./deploy/kurulum.sh
#
# Ön koşul: PostgreSQL kurulu ve çalışıyor,
#            /etc/openpyerp.env dosyası oluşturulmuş.

set -e  # Hata olursa dur

UYGULAMA_DIZINI="/var/www/openpyerp"
LOG_DIZINI="/var/log/openpyerp"
KULLANICI="www-data"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " OpenPyERP — Sunucu Kurulumu"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. Sistem bağımlılıkları ──────────────────────────────
echo "→ Sistem paketleri kuruluyor..."
apt-get update -q
apt-get install -y -q python3 python3-pip python3-venv \
    libpq-dev gcc nginx

# ── 2. Uygulama dizini ───────────────────────────────────
echo "→ Dizinler hazırlanıyor..."
mkdir -p "$UYGULAMA_DIZINI"
mkdir -p "$LOG_DIZINI"
chown -R "$KULLANICI:$KULLANICI" "$UYGULAMA_DIZINI"
chown -R "$KULLANICI:$KULLANICI" "$LOG_DIZINI"

# ── 3. Dosyaları kopyala ─────────────────────────────────
echo "→ Uygulama dosyaları kopyalanıyor..."
cp -r . "$UYGULAMA_DIZINI/"
chown -R "$KULLANICI:$KULLANICI" "$UYGULAMA_DIZINI"

# ── 4. Virtualenv + paketler ─────────────────────────────
echo "→ Python sanal ortamı kuruluyor..."
cd "$UYGULAMA_DIZINI"
python3 -m venv venv
venv/bin/pip install --upgrade pip -q
venv/bin/pip install -r requirements.txt -q
echo "✓ Python paketleri kuruldu"

# ── 5. Ortam dosyası kontrolü ────────────────────────────
if [ ! -f /etc/openpyerp.env ]; then
    echo ""
    echo "⚠  /etc/openpyerp.env bulunamadı!"
    echo "   deploy/openpyerp.env.example dosyasını kopyalayın:"
    echo "   sudo cp deploy/openpyerp.env.example /etc/openpyerp.env"
    echo "   sudo nano /etc/openpyerp.env  # ← gerçek değerleri girin"
    echo ""
    exit 1
fi
chmod 640 /etc/openpyerp.env
chown root:www-data /etc/openpyerp.env

# ── 6. Veritabanı migration ───────────────────────────────
echo "→ Veritabanı şeması oluşturuluyor..."
source /etc/openpyerp.env
cd "$UYGULAMA_DIZINI"
venv/bin/alembic upgrade head
echo "✓ Migration tamamlandı"

# ── 7. Başlangıç verisi ───────────────────────────────────
echo "→ Başlangıç verisi yükleniyor..."
venv/bin/python seed.py
echo "✓ Seed tamamlandı"

# ── 8. Systemd servisi ────────────────────────────────────
echo "→ Systemd servisi kuruluyor..."
cp deploy/openpyerp.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable openpyerp
systemctl start openpyerp
echo "✓ Servis başlatıldı"

# ── 9. Nginx ──────────────────────────────────────────────
echo "→ Nginx konfigürasyonu..."
cp deploy/nginx_openpyerp.conf /etc/nginx/sites-available/openpyerp
ln -sf /etc/nginx/sites-available/openpyerp /etc/nginx/sites-enabled/openpyerp
nginx -t && systemctl reload nginx
echo "✓ Nginx yeniden yüklendi"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " ✅ Kurulum tamamlandı!"
echo ""
echo " Giriş: https://erp.sirketiniz.com"
echo " Kullanıcı: admin@openpyerp.local"
echo " Şifre: Admin1234!  ← HEMEN DEĞİŞTİRİN"
echo ""
echo " Log izleme:"
echo "   journalctl -u openpyerp -f"
echo "   tail -f /var/log/openpyerp/error.log"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
