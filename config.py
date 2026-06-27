"""
config.py — Uygulama konfigürasyonu

Tüm hassas değerler ortam değişkenlerinden okunur.
Sunucuda /etc/openpyerp.env dosyasına yazılır, systemd bu dosyayı yükler.
"""
import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'degistir-beni-uretimde')

    # PostgreSQL — varsayılan bağlantı dizesi
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'postgresql+psycopg2://openpyerp_user:sifre@localhost/openpyerp'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size':    5,
        'max_overflow': 10,
        'pool_recycle': 280,
        'pool_pre_ping': True,
    }
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret'
