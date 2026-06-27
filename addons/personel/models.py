"""addons/personel/models.py — Personel, PersonelIzin, Puantaj modelleri"""
from datetime import date, datetime
from core.extensions import db

class Personel(db.Model):
    __tablename__ = 'personel'
    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sirket_id   = db.Column(db.Integer, db.ForeignKey('sirket.id', ondelete='SET NULL'))
    sicil_no    = db.Column(db.String(30), nullable=False)
    ad          = db.Column(db.String(50), nullable=False)
    soyad       = db.Column(db.String(50), nullable=False)
    tc_kimlik   = db.Column(db.String(11))
    ise_giris   = db.Column(db.Date, nullable=False, default=date.today)
    isten_cikis = db.Column(db.Date)
    cari_id     = db.Column(db.Integer, db.ForeignKey('cari.id', ondelete='SET NULL'))
    aktif       = db.Column(db.Boolean, default=True, server_default='1')
    olusturma_tarihi  = db.Column(db.DateTime, default=datetime.now)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    sirket      = db.relationship('Sirket', backref=db.backref('personeller', lazy='dynamic'))
    __table_args__ = (
        db.UniqueConstraint('sirket_id', 'sicil_no', name='uq_personel_sirket_sicil'),
        db.Index('ix_personel_sirket_aktif', 'sirket_id', 'aktif'),
    )

    @property
    def tam_ad(self):
        return f"{self.ad} {self.soyad}"

class PersonelIzin(db.Model):
    __tablename__ = 'personel_izin'
    id           = db.Column(db.Integer, primary_key=True, autoincrement=True)
    personel_id  = db.Column(db.Integer, db.ForeignKey('personel.id', ondelete='CASCADE'), nullable=False)
    izin_tipi    = db.Column(db.String(30), nullable=False)  # YILLIK | HASTALIK | UCRETSIZ
    baslangic    = db.Column(db.Date, nullable=False)
    bitis        = db.Column(db.Date, nullable=False)
    gun_sayisi   = db.Column(db.Integer, nullable=False)
    durum        = db.Column(db.String(20), default='BEKLEMEDE')  # BEKLEMEDE|ONAYLANDI|REDDEDILDI
    aciklama     = db.Column(db.Text)
    onaylayan_id = db.Column(db.Integer, db.ForeignKey('kullanici.id', ondelete='SET NULL'))
    olusturma_tarihi  = db.Column(db.DateTime, default=datetime.now)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    personel     = db.relationship('Personel', backref=db.backref('izinler', lazy='dynamic'))

class Puantaj(db.Model):
    __tablename__ = 'puantaj'
    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    personel_id = db.Column(db.Integer, db.ForeignKey('personel.id', ondelete='CASCADE'), nullable=False)
    yil         = db.Column(db.SmallInteger, nullable=False)
    ay          = db.Column(db.SmallInteger, nullable=False)
    calisilan_gun = db.Column(db.SmallInteger, default=0)
    fazla_mesai   = db.Column(db.Numeric(5, 2), default=0)
    durum       = db.Column(db.String(20), default='TASLAK')
    olusturma_tarihi  = db.Column(db.DateTime, default=datetime.now)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    personel    = db.relationship('Personel', backref=db.backref('puantajlar', lazy='dynamic'))
    __table_args__ = (
        db.UniqueConstraint('personel_id', 'yil', 'ay', name='uq_puantaj_personel_donem'),
    )
