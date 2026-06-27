"""addons/finans/models.py — Kasa, Banka, CekSenet modelleri"""
from datetime import date, datetime
from core.extensions import db

class Kasa(db.Model):
    __tablename__ = 'kasa'
    id        = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sirket_id = db.Column(db.Integer, db.ForeignKey('sirket.id', ondelete='CASCADE'))
    kod       = db.Column(db.String(20), nullable=False)
    ad        = db.Column(db.String(100), nullable=False)
    para_birimi = db.Column(db.String(5), default='TRY')
    aktif     = db.Column(db.Boolean, default=True, server_default='1')
    olusturma_tarihi  = db.Column(db.DateTime, default=datetime.now)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    sirket    = db.relationship('Sirket', backref=db.backref('kasalar', lazy='dynamic'))

class KasaHareket(db.Model):
    __tablename__ = 'kasa_hareket'
    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    kasa_id     = db.Column(db.Integer, db.ForeignKey('kasa.id', ondelete='CASCADE'))
    tarih       = db.Column(db.Date, default=date.today)
    belge_no    = db.Column(db.String(50))
    aciklama    = db.Column(db.String(500))
    hareket_tipi = db.Column(db.String(10))  # GIRIS | CIKIS
    tutar       = db.Column(db.Numeric(15, 2), nullable=False)
    cari_id     = db.Column(db.Integer, db.ForeignKey('cari.id', ondelete='SET NULL'))
    kaynak_tip  = db.Column(db.String(20))
    kaynak_id   = db.Column(db.Integer)
    olusturma_tarihi  = db.Column(db.DateTime, default=datetime.now)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    kasa        = db.relationship('Kasa', backref=db.backref('hareketler', lazy='dynamic'))
    __table_args__ = (db.Index('ix_kh_kasa_tarih', 'kasa_id', 'tarih'),)

class Banka(db.Model):
    __tablename__ = 'banka'
    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sirket_id   = db.Column(db.Integer, db.ForeignKey('sirket.id', ondelete='CASCADE'))
    banka_adi   = db.Column(db.String(100), nullable=False)
    sube_adi    = db.Column(db.String(100))
    iban        = db.Column(db.String(35))
    hesap_no    = db.Column(db.String(50))
    para_birimi = db.Column(db.String(5), default='TRY')
    aktif       = db.Column(db.Boolean, default=True, server_default='1')
    olusturma_tarihi  = db.Column(db.DateTime, default=datetime.now)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    sirket      = db.relationship('Sirket', backref=db.backref('bankalar', lazy='dynamic'))

class BankaHareket(db.Model):
    __tablename__ = 'banka_hareket'
    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    banka_id    = db.Column(db.Integer, db.ForeignKey('banka.id', ondelete='CASCADE'))
    tarih       = db.Column(db.Date, default=date.today)
    belge_no    = db.Column(db.String(50))
    aciklama    = db.Column(db.String(500))
    hareket_tipi = db.Column(db.String(10))  # GIRIS | CIKIS
    tutar       = db.Column(db.Numeric(15, 2), nullable=False)
    cari_id     = db.Column(db.Integer, db.ForeignKey('cari.id', ondelete='SET NULL'))
    kaynak_tip  = db.Column(db.String(20))
    kaynak_id   = db.Column(db.Integer)
    olusturma_tarihi  = db.Column(db.DateTime, default=datetime.now)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    banka       = db.relationship('Banka', backref=db.backref('hareketler', lazy='dynamic'))
    __table_args__ = (db.Index('ix_bh_banka_tarih', 'banka_id', 'tarih'),)
