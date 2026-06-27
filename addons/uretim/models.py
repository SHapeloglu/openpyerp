"""addons/uretim/models.py — UretimFis, UretimFisSatir"""
from datetime import date, datetime
from core.extensions import db
from core.tipler import BelgeDurum

class UretimFis(db.Model):
    __tablename__ = 'uretim_fis'
    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sirket_id   = db.Column(db.Integer, db.ForeignKey('sirket.id', ondelete='SET NULL'))
    fis_no      = db.Column(db.String(50), unique=True, nullable=False)
    tarih       = db.Column(db.Date, nullable=False, default=date.today)
    mamul_stok_id = db.Column(db.Integer, db.ForeignKey('stok_karti.id', ondelete='RESTRICT'), nullable=False)
    uretilecek_miktar = db.Column(db.Numeric(15, 4), nullable=False)
    uretilen_miktar   = db.Column(db.Numeric(15, 4), default=0)
    depo_id     = db.Column(db.Integer, db.ForeignKey('depo.id', ondelete='SET NULL'))
    durum       = db.Column(db.String(20), nullable=False, default=BelgeDurum.TASLAK)
    aciklama    = db.Column(db.Text)
    olusturma_tarihi  = db.Column(db.DateTime, default=datetime.now)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    mamul       = db.relationship('StokKarti', foreign_keys=[mamul_stok_id])
    satirlar    = db.relationship('UretimFisSatir', backref='fis',
                                  cascade='all, delete-orphan', order_by='UretimFisSatir.id')
    __table_args__ = (db.Index('ix_uf_sirket_tarih', 'sirket_id', 'tarih'),)

class UretimFisSatir(db.Model):
    """Üretim reçetesi satırı — hammadde tüketimi."""
    __tablename__ = 'uretim_fis_satir'
    id       = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fis_id   = db.Column(db.Integer, db.ForeignKey('uretim_fis.id', ondelete='CASCADE'), nullable=False)
    stok_id  = db.Column(db.Integer, db.ForeignKey('stok_karti.id', ondelete='RESTRICT'), nullable=False)
    miktar   = db.Column(db.Numeric(15, 4), nullable=False)
    birim_id = db.Column(db.Integer, db.ForeignKey('birim.id', ondelete='RESTRICT'))
    cevrilen_miktar = db.Column(db.Numeric(15, 4))
    stok     = db.relationship('StokKarti')
    birim    = db.relationship('Birim')
