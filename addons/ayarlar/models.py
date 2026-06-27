"""addons/ayarlar/models.py — Kullanici modeli"""
from datetime import datetime
import bcrypt
from core.extensions import db
from core.tipler import KullaniciRol

class Kullanici(db.Model):
    __tablename__ = 'kullanici'
    id       = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ad_soyad = db.Column(db.String(100), nullable=False)
    email    = db.Column(db.String(150), unique=True, nullable=False)
    sifre_hash = db.Column(db.String(255), nullable=False)
    rol      = db.Column(db.String(20), nullable=False, default=KullaniciRol.KULLANICI)
    aktif    = db.Column(db.Boolean, default=True, server_default='1')
    olusturma_tarihi  = db.Column(db.DateTime, default=datetime.now)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def sifre_dogru_mu(self, sifre: str) -> bool:
        return bcrypt.checkpw(sifre.encode(), self.sifre_hash.encode())

    @staticmethod
    def sifre_hashle(sifre: str) -> str:
        return bcrypt.hashpw(sifre.encode(), bcrypt.gensalt()).decode()
