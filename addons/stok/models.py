"""
addons/stok/models.py — StokKarti, StokHareket modelleri

PILOT KAPSAM NOTU: hesap_grubu_id, satin_alma_birim_id/carpan, varyant_id
alanları eski şemada vardı; bu pilotta varyant ve hesap_grubu addon'ları
henüz taşınmadığı için o FK'ler bilinçli olarak çıkarılmıştır (bkz.
addons/cari/models.py'deki aynı not). Mevcut MySQL tablosunda bu kolonlar
fiziksel olarak DURUYOR — model sınıfında tanımlanmamaları, SQLAlchemy'nin
o kolonları görmezden gelmesi anlamına gelir, veri kaybı OLMAZ. Bu addon'lar
eklendiğinde models.py'a geri eklenecektir.
"""
from datetime import date, datetime

from core.extensions import db


class StokKarti(db.Model):
    """Stok kartı (malzeme veya hizmet).

    tip: MALZEME (stok takipli) | HIZMET (stok takipsiz)
    stok_miktari(): tüm depolardaki toplam net miktarı döner.
    """
    __tablename__ = 'stok_karti'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sirket_id = db.Column(db.Integer, db.ForeignKey('sirket.id', ondelete='CASCADE'))
    kod = db.Column(db.String(50), nullable=False)
    ad = db.Column(db.String(200), nullable=False)
    tip = db.Column(db.Enum('MALZEME', 'HIZMET'), nullable=False)
    kullanim_tipi = db.Column(db.Enum('ALIS', 'SATIS', 'HER_IKISI'), nullable=False,
                               default='HER_IKISI', server_default='HER_IKISI')
    birim_id = db.Column(db.Integer, db.ForeignKey('birim.id', ondelete='RESTRICT'), nullable=False)
    kdv_orani = db.Column(db.Numeric(5, 2), default=20.00)
    satis_fiyati = db.Column(db.Numeric(15, 4), default=0.0)
    alis_fiyati = db.Column(db.Numeric(15, 4), default=0.0)
    aciklama = db.Column(db.Text)
    barkod_ean8 = db.Column(db.String(8), index=True)
    barkod_ean13 = db.Column(db.String(13), index=True)
    min_stok = db.Column(db.Numeric(15, 4), nullable=True)
    aktif = db.Column(db.Boolean, default=True, server_default='1', nullable=False)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.now)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    birim = db.relationship('Birim', foreign_keys='StokKarti.birim_id',
                             backref=db.backref('stoklar', lazy='dynamic'))

    __table_args__ = (
        db.Index('ix_stok_sirket_aktif', 'sirket_id', 'aktif'),
        db.Index('ix_stok_kod', 'sirket_id', 'kod'),
        db.Index('ix_stok_barkod', 'barkod_ean13', 'barkod_ean8'),
    )

    def stok_miktari(self, depo_id=None):
        """Ana birimde toplam stok miktarını döner.

        cevrilen_miktar kullanır — birim dönüşümü doğru hesaplanır.
        depo_id verilirse sadece o deponun bakiyesini döner. HIZMET tipli
        kartlarda stok takibi yapılmadığı için None döner.
        """
        if self.tip == 'HIZMET':
            return None

        from sqlalchemy import func, case

        q_giris = db.session.query(func.sum(
            case((StokHareket.cevrilen_miktar.isnot(None), StokHareket.cevrilen_miktar),
                 else_=StokHareket.miktar)
        )).filter(StokHareket.stok_id == self.id, StokHareket.hareket_tipi == 'GIRIS')
        q_cikis = db.session.query(func.sum(
            case((StokHareket.cevrilen_miktar.isnot(None), StokHareket.cevrilen_miktar),
                 else_=StokHareket.miktar)
        )).filter(StokHareket.stok_id == self.id, StokHareket.hareket_tipi == 'CIKIS')

        if depo_id:
            q_giris = q_giris.filter(StokHareket.depo_id == depo_id)
            q_cikis = q_cikis.filter(StokHareket.depo_id == depo_id)

        giris = q_giris.scalar() or 0
        cikis = q_cikis.scalar() or 0
        return float(giris) - float(cikis)

    def barkod(self):
        """İlk geçerli barkodu döner."""
        return self.barkod_ean13 or self.barkod_ean8 or None


class StokHareket(db.Model):
    """Stok giriş/çıkış hareketleri.

    Hareket birimi ile stok birimi farklı olabilir; cevrilen_miktar ana
    birimde tutulur. addons/belge servisleri, fatura/irsaliye onaylandığında
    bu tabloya DOĞRUDAN yazar (bkz. addons/stok/services.py
    stok_hareketi_olustur, ve addons/belge/services.py'deki kullanımı).
    """
    __tablename__ = 'stok_hareket'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    stok_id = db.Column(db.Integer, db.ForeignKey('stok_karti.id', ondelete='CASCADE'), nullable=False)
    tarih = db.Column(db.Date, nullable=False, default=date.today)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.now)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    belge_no = db.Column(db.String(50))
    hareket_tipi = db.Column(db.Enum('GIRIS', 'CIKIS'), nullable=False)
    birim_id = db.Column(db.Integer, db.ForeignKey('birim.id', ondelete='RESTRICT'))
    miktar = db.Column(db.Numeric(15, 4), nullable=False)
    cevrilen_miktar = db.Column(db.Numeric(15, 4))
    birim_fiyat = db.Column(db.Numeric(15, 4))
    aciklama = db.Column(db.String(500))
    depo_id = db.Column(db.Integer, db.ForeignKey('depo.id', ondelete='SET NULL'), nullable=True)

    stok = db.relationship('StokKarti', backref=db.backref('hareketler', lazy='dynamic'))
    birim = db.relationship('Birim')

    __table_args__ = (
        db.Index('ix_sh_stok_tarih', 'stok_id', 'tarih'),
        db.Index('ix_sh_depo', 'depo_id'),
        db.Index('ix_sh_tip', 'hareket_tipi'),
    )
