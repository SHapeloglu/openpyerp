"""
addons/cari/models.py — Cari, CariHareket modelleri

PILOT KAPSAM NOTU:
    Eski app.py'de Cari modeli; HesapGrubu ve FiyatListesi'ne (henüz bu pilotta
    taşınmamış modüller) foreign key veriyordu. SQLAlchemy'de bir modelin henüz
    import edilmemiş bir başka modele FK vermesi sorun değildir — db.relationship
    'HesapGrubu' gibi STRING isim kullanır, sınıfı sadece ilk kullanıldığında
    (mapper configure anında) arar. Bu yüzden bu iki alan burada bilinçli olarak
    YORUMA alınmıştır — addons/hesap_grubu ve addons/fiyat_listesi pilot
    sonrası eklendiğinde geri açılacaktır. Şu an bu iki FK olmadan da modül
    tam çalışır; CariHareket ve bakiye hesaplama (belge modülünün ihtiyaç
    duyduğu asıl mantık) burada eksiksizdir.
"""
from datetime import date, datetime

from sqlalchemy import func

from core.extensions import db


class Cari(db.Model):
    """Alıcı, satıcı veya her ikisi olabilen cari hesap.

    tip: ALICI | SATICI | PERSONEL | HER_IKISI
    bakiye(): cari_hareket tablosundan borç-alacak farkını hesaplar.
    """
    __tablename__ = 'cari'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sirket_id = db.Column(db.Integer, db.ForeignKey('sirket.id', ondelete='RESTRICT'))
    kod = db.Column(db.String(20), nullable=False)
    unvan = db.Column(db.String(200), nullable=False)
    tip = db.Column(db.Enum('ALICI', 'SATICI', 'PERSONEL', 'HER_IKISI'), nullable=False)
    vergi_no = db.Column(db.String(20))
    vergi_dairesi = db.Column(db.String(100))
    telefon = db.Column(db.String(20))
    email = db.Column(db.String(100))
    adres = db.Column(db.Text)
    sehir = db.Column(db.String(50))
    # hesap_grubu_id ve fiyat_listesi_id — bkz. modül başlığındaki PILOT KAPSAM NOTU
    website = db.Column(db.String(200))
    aktif = db.Column(db.Boolean, default=True, server_default='1', nullable=False)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.now)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    iletisimler = db.relationship('CariIletisim', backref='cari',
                                   cascade='all, delete-orphan', lazy='dynamic')
    adresler = db.relationship('CariAdres', backref='cari',
                                cascade='all, delete-orphan', lazy='dynamic')

    __table_args__ = (
        db.Index('ix_cari_sirket_aktif', 'sirket_id', 'aktif'),
        db.Index('ix_cari_sirket_tip', 'sirket_id', 'tip'),
        db.Index('ix_cari_sirket_kod', 'sirket_id', 'kod'),
    )

    def varsayilan_adres(self):
        """Carinin varsayılan adresini döner; yoksa ilk aktif adres seçilir."""
        return self.adresler.filter_by(varsayilan=True, aktif=True).first() or \
            self.adresler.filter_by(aktif=True).first()

    def bakiye(self):
        """Giriş ve çıkış hareketlerini toplayarak net bakiyeyi döner.

        NOT: Tek cari için anlıktır. Çok sayıda cari için addons/cari/services.py
        içindeki toplu_cari_bakiyeleri() kullanılmalıdır (N+1 sorgu riskini önler).
        """
        borc = db.session.query(func.sum(CariHareket.tutar)).filter(
            CariHareket.cari_id == self.id, CariHareket.hareket_tipi == 'BORC'
        ).scalar() or 0
        alacak = db.session.query(func.sum(CariHareket.tutar)).filter(
            CariHareket.cari_id == self.id, CariHareket.hareket_tipi == 'ALACAK'
        ).scalar() or 0
        return float(borc) - float(alacak)


class CariHareket(db.Model):
    """Cari hesap hareketleri (borç/alacak).

    kaynak_tip ve kaynak_id ile kaynak belgesi izlenebilir (örn: kaynak_tip='FATURA',
    kaynak_id=<belge_baslik.id>). Bu, addons/belge modülünün cari ile entegre
    olduğu temel mekanizmadır — belge modülü bu tabloyu DOĞRUDAN yazar
    (bkz. addons/belge/services.py FaturaKaydetServisi).
    """
    __tablename__ = 'cari_hareket'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cari_id = db.Column(db.Integer, db.ForeignKey('cari.id', ondelete='CASCADE'), nullable=False)
    tarih = db.Column(db.Date, nullable=False, default=date.today)
    belge_no = db.Column(db.String(50))
    aciklama = db.Column(db.String(500))
    hareket_tipi = db.Column(db.Enum('BORC', 'ALACAK'), nullable=False)
    tutar = db.Column(db.Numeric(15, 2), nullable=False)
    kaynak_tip = db.Column(db.String(20))
    kaynak_id = db.Column(db.Integer)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.now)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    cari = db.relationship('Cari', backref=db.backref('hareketler', lazy='dynamic'))

    __table_args__ = (db.Index('ix_ch_cari_tarih', 'cari_id', 'tarih'),)


class CariAdres(db.Model):
    """Cariye ait çoklu adres (MERKEZ, SUBE, FATURA, SEVKIYAT...)."""
    __tablename__ = 'cari_adres'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cari_id = db.Column(db.Integer, db.ForeignKey('cari.id', ondelete='CASCADE'), nullable=False)
    tip = db.Column(db.Enum('MERKEZ', 'SUBE', 'FATURA', 'SEVKIYAT', 'DIGER'), nullable=False, default='MERKEZ')
    baslik = db.Column(db.String(100))
    il_id = db.Column(db.Integer)
    ilce_id = db.Column(db.Integer)
    mahalle_id = db.Column(db.Integer)
    adres_metni = db.Column(db.Text)
    posta_kodu = db.Column(db.String(10))
    varsayilan = db.Column(db.Boolean, default=False, server_default='0', nullable=False)
    aktif = db.Column(db.Boolean, default=True, server_default='1', nullable=False)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.now)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (db.Index('ix_ca_cari', 'cari_id'),)


class CariIletisim(db.Model):
    """Bir cariye ait iletişim bilgileri (telefon, e-posta, fax vb.). Birden fazla kayıt olabilir."""
    __tablename__ = 'cari_iletisim'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cari_id = db.Column(db.Integer, db.ForeignKey('cari.id', ondelete='CASCADE'), nullable=False)
    tip = db.Column(db.Enum('TELEFON', 'CEP', 'FAX', 'EMAIL', 'WEB', 'DIGER'), nullable=False)
    deger = db.Column(db.String(200), nullable=False)
    aciklama = db.Column(db.String(100))
    varsayilan = db.Column(db.Boolean, default=False, server_default='0', nullable=False)
    aktif = db.Column(db.Boolean, default=True, server_default='1', nullable=False)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.now)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (db.Index('ix_ci_cari', 'cari_id'),)
