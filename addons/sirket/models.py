"""
addons/sirket/models.py — Şirket, Depo, NumaraSira, DonemKilidi modelleri

Eski app.py'deki aynı adlı sınıfların taşınmış hali. Şema (tablo adı, kolon
adları, kısıtlar) BİREBİR korunmuştur — bu sayede mevcut MySQL veritabanı
hiçbir migration gerektirmeden bu yeni model tanımlarıyla çalışabilir.

Bu modül 'sirket' addon'unun parçasıdır ve hiçbir başka addon'a bağımlı
değildir (bkz. __manifest__.py) — diğer tüm modüller (cari, stok, belge...)
buna bağımlıdır.
"""
from datetime import datetime

from core.extensions import db


class Sirket(db.Model):
    """Şirket bilgilerini tutan model. Çok şirketli yapıyı destekler."""
    __tablename__ = 'sirket'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    kod = db.Column(db.String(20), nullable=False)
    unvan = db.Column(db.String(200), nullable=False)
    vergi_no = db.Column(db.String(20))
    vergi_dairesi = db.Column(db.String(100))
    telefon = db.Column(db.String(20))
    email = db.Column(db.String(100))
    adres = db.Column(db.Text)
    logo_url = db.Column(db.String(300))
    aktif = db.Column(db.Boolean, default=True, server_default='1', nullable=False)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.now)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


class Depo(db.Model):
    """Şirkete bağlı depo/ambar tanımları. Şirket başına benzersiz kod zorunludur."""
    __tablename__ = 'depo'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sirket_id = db.Column(db.Integer, db.ForeignKey('sirket.id', ondelete='CASCADE'), nullable=False)
    kod = db.Column(db.String(20), nullable=False)
    ad = db.Column(db.String(100), nullable=False)
    adres = db.Column(db.Text)
    varsayilan = db.Column(db.Boolean, default=False, server_default='0')
    aktif = db.Column(db.Boolean, default=True, server_default='1', nullable=False)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.now)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    sirket = db.relationship('Sirket', backref=db.backref('depolar', lazy='dynamic'))

    __table_args__ = (db.UniqueConstraint('sirket_id', 'kod', name='uq_depo_sirket_kod'),)


class NumaraSira(db.Model):
    """Belge numarası otomatik üretimi için sıra takip tablosu.

    Her (sirket, belge_tip, cari_tip, yil) kombinasyonu için ayrı sıra tutulur.
    sonraki_no() metodu son sayıyı artırıp formatlanmış belge numarası döner.
    """
    __tablename__ = 'numara_sira'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sirket_id = db.Column(db.Integer, db.ForeignKey('sirket.id', ondelete='CASCADE'), nullable=False)
    belge_tip = db.Column(db.String(30), nullable=False)
    cari_tip = db.Column(db.Enum('SATIS', 'ALIS'), nullable=False, default='SATIS')
    prefix = db.Column(db.String(10), nullable=False)
    yil = db.Column(db.SmallInteger, nullable=False)
    son_sayi = db.Column(db.Integer, default=0, nullable=False)
    basamak = db.Column(db.SmallInteger, default=5)

    sirket = db.relationship('Sirket', backref=db.backref('numara_siralar', lazy='dynamic'))
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.now)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        db.UniqueConstraint('sirket_id', 'belge_tip', 'cari_tip', 'yil', name='uq_ns_sirket_tip_yil'),
    )

    def sonraki_no(self):
        """Sıradaki belge numarasını üretip son_sayi'yı 1 artırır.

        Format: PREFIX + YIL(son 2 hane) + SAYI(basamak sayısı kadar sıfır dolgulu)
        Örnek: FAT26000001 → Fatura, 2026, 1. kayıt (6 basamak)
        """
        self.son_sayi += 1
        return f"{self.prefix}{str(self.yil)[2:]}{str(self.son_sayi).zfill(self.basamak)}"


class DonemKilidi(db.Model):
    """Muhasebe dönem kilidi.

    Kilitli dönemde belge oluşturma, düzenleme ve silme engellenir.
    KDV beyannamesi verildikten sonra geçmiş dönem kilitlenir.
    """
    __tablename__ = 'donem_kilidi'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sirket_id = db.Column(db.Integer, db.ForeignKey('sirket.id', ondelete='CASCADE'), nullable=False)
    yil = db.Column(db.Integer, nullable=False)
    ay = db.Column(db.Integer, nullable=True)  # None = tüm yıl kilitli
    kilitli = db.Column(db.Boolean, default=True, server_default='1')
    aciklama = db.Column(db.String(300))
    kilitleyen_id = db.Column(db.Integer, db.ForeignKey('kullanici.id', ondelete='SET NULL'))
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.now)

    sirket = db.relationship('Sirket', backref=db.backref('donem_kilitleri', lazy='dynamic'))
    kilitleyen = db.relationship('Kullanici', foreign_keys='DonemKilidi.kilitleyen_id')

    __table_args__ = (
        db.UniqueConstraint('sirket_id', 'yil', 'ay', name='uq_donem_kilidi'),
        db.Index('ix_dk_sirket_donem', 'sirket_id', 'yil', 'ay'),
    )
