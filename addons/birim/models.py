"""
addons/birim/models.py — BirimGrubu, Birim, BirimDonusum modelleri

Eski app.py'deki aynı adlı sınıfların taşınmış hali. Şema birebir korunmuştur.
"""
from datetime import datetime

from core.extensions import db


class BirimGrubu(db.Model):
    """Birim grupları (Uzunluk, Ağırlık, Hacim vb.). Her grubun bir taban birimi vardır."""
    __tablename__ = 'birim_grubu'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ad = db.Column(db.String(50), unique=True, nullable=False)
    aciklama = db.Column(db.String(200))
    aktif = db.Column(db.Boolean, default=True, server_default='1', nullable=False)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.now)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    birimler = db.relationship('Birim', backref='grup', lazy='dynamic', foreign_keys='Birim.grup_id')


class Birim(db.Model):
    """Ölçü birimi tanımı. katsayi, taban birime göre çevrim katsayısıdır.

    Örnek (Uzunluk grubu, taban=MT): KM→1000, MT→1, CM→0.01, MM→0.001
    """
    __tablename__ = 'birim'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    grup_id = db.Column(db.Integer, db.ForeignKey('birim_grubu.id', ondelete='RESTRICT'), nullable=False)
    kod = db.Column(db.String(20), unique=True, nullable=False)
    ad = db.Column(db.String(50), nullable=False)
    katsayi = db.Column(db.Numeric(20, 10), nullable=False, default=1.0)
    taban_mi = db.Column(db.Boolean, default=False, nullable=False)
    aktif = db.Column(db.Boolean, default=True, server_default='1', nullable=False)

    olusturma_tarihi = db.Column(db.DateTime, default=datetime.now)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (db.Index('ix_birim_grup', 'grup_id'),)

    def cevirme_katsayisi(self, hedef_birim):
        """self biriminden hedef_birim'e çevrim katsayısı döner. Farklı gruptaysa None."""
        if self.id == hedef_birim.id:
            return 1.0
        if self.grup_id != hedef_birim.grup_id:
            return None
        return float(self.katsayi) / float(hedef_birim.katsayi)


class BirimDonusum(db.Model):
    """Farklı gruplar arası veya özel birim çevrimleri (örn: 1 Koli = 6 Kutu).

    kaynak_birim_id × carpan = hedef_birim_id (1 kaynak = carpan × hedef)
    """
    __tablename__ = 'birim_donusum'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    kaynak_birim_id = db.Column(db.Integer, db.ForeignKey('birim.id', ondelete='CASCADE'), nullable=False)
    hedef_birim_id = db.Column(db.Integer, db.ForeignKey('birim.id', ondelete='CASCADE'), nullable=False)
    carpan = db.Column(db.Numeric(20, 10), nullable=False)
    aciklama = db.Column(db.String(200))
    aktif = db.Column(db.Boolean, default=True, server_default='1', nullable=False)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.now)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    kaynak = db.relationship('Birim', foreign_keys=[kaynak_birim_id],
                              backref=db.backref('cikis_donusumler', lazy='dynamic'))
    hedef = db.relationship('Birim', foreign_keys=[hedef_birim_id],
                             backref=db.backref('giris_donusumler', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('kaynak_birim_id', 'hedef_birim_id', name='uq_donusum_kh'),
        db.Index('ix_donusum_kaynak', 'kaynak_birim_id'),
    )
