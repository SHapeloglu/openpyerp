"""
addons/belge/models.py — BelgeBaslik, BelgeSatir modelleri

ENUM → VARCHAR değişikliği:
    db.Enum('TASLAK','ACIK',...) yerine db.String(30) kullanılıyor.
    Geçerli değerler core/tipler.py içinde sabit olarak tanımlı,
    uygulama katmanında (workflow + servis) kontrol ediliyor.
    Bu sayede MariaDB ve PostgreSQL'de migration aynı Alembic kodu.
"""
from datetime import date, datetime

from core.extensions import db
from core.tipler import BelgeTip, CariTip, BelgeDurum, SevkDurum


class BelgeBaslik(db.Model):
    """Ticari belge başlığı — Talep → Sipariş → İrsaliye → Fatura zinciri.

    durum geçişleri addons/belge/workflow.py içindeki BELGE_WF tarafından
    yönetilir. Doğrudan baslik.durum = 'ONAYLANDI' yazmak yerine
    BELGE_WF.gecer(baslik, BelgeDurum.ONAYLANDI) kullanılmalıdır.
    """
    __tablename__ = 'belge_baslik'

    id              = db.Column(db.Integer, primary_key=True, autoincrement=True)
    belge_tip       = db.Column(db.String(20), nullable=False)
    belge_no        = db.Column(db.String(50), unique=True, nullable=False)
    tarih           = db.Column(db.Date, nullable=False, default=date.today)
    vade_tarihi     = db.Column(db.Date)
    cari_id         = db.Column(db.Integer, db.ForeignKey('cari.id',    ondelete='SET NULL'))
    cari_tip        = db.Column(db.String(10), nullable=False, default=CariTip.SATIS)
    aciklama        = db.Column(db.Text)
    durum           = db.Column(db.String(20), nullable=False, default=BelgeDurum.ACIK)
    kaynak_belge_id = db.Column(db.Integer, db.ForeignKey('belge_baslik.id', ondelete='SET NULL'))
    toplam_kdvsiz   = db.Column(db.Numeric(15, 2), default=0.00)
    toplam_kdv      = db.Column(db.Numeric(15, 2), default=0.00)
    toplam_kdvli    = db.Column(db.Numeric(15, 2), default=0.00)
    sirket_id       = db.Column(db.Integer, db.ForeignKey('sirket.id',  ondelete='SET NULL'))
    depo_id         = db.Column(db.Integer, db.ForeignKey('depo.id',    ondelete='SET NULL'))
    evrak_no        = db.Column(db.String(50))
    sevk_durumu     = db.Column(db.String(20), default=SevkDurum.SEVK_EDILMEDI)
    olusturma_tarihi  = db.Column(db.DateTime, default=datetime.now)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # ── İlişkiler ──────────────────────────────────────────────────────
    sirket       = db.relationship('Sirket')
    depo         = db.relationship('Depo')
    cari         = db.relationship('Cari', backref=db.backref('belgeler', lazy='dynamic'))
    satirlar     = db.relationship('BelgeSatir', backref='baslik',
                                   cascade='all, delete-orphan',
                                   order_by='BelgeSatir.sira_no')
    kaynak_belge = db.relationship('BelgeBaslik', remote_side=[id],
                                   backref=db.backref('donusum_belgeler', lazy='dynamic'))

    __table_args__ = (
        db.Index('ix_bb_tip_ctip_tarih', 'belge_tip', 'cari_tip', 'tarih'),
        db.Index('ix_bb_cari',           'cari_id'),
        db.Index('ix_bb_sirket_tarih',   'sirket_id', 'tarih'),
        db.Index('ix_bb_sirket_durum',   'sirket_id', 'durum'),
        db.Index('ix_bb_vade',           'vade_tarihi'),
    )

    # ── Domain sabitleri (backward compat — tipler.py tercih edilmeli) ──
    TIP_ADLARI       = BelgeTip.ADLAR
    DONUSUM_HARITASI = {
        k: (v, BelgeTip.ADLAR[v])
        for k, v in BelgeTip.DONUSUM.items()
    }

    # ── Durum yardımcıları ─────────────────────────────────────────────
    @property
    def duzenlenebilir_mi(self) -> bool:
        return self.durum in BelgeDurum.DUZENLENEBILIR

    @property
    def silinebilir_mi(self) -> bool:
        return self.durum in BelgeDurum.SILINEBILIR

    def mevcut_gecisler(self):
        """Workflow'dan mevcut geçiş listesini döner — template butonları için."""
        from addons.belge.workflow import BELGE_WF
        return BELGE_WF.mevcut_gecisler(self)


class BelgeSatir(db.Model):
    """Belge satırı — miktar, birim, fiyat, iskonto, KDV.

    donusum_carpan: Belge anındaki birim çarpanı (tarihsel doğruluk için saklanır).
    cevrilen_miktar: Ana birimde miktar = miktar × donusum_carpan
    """
    __tablename__ = 'belge_satir'

    id               = db.Column(db.Integer, primary_key=True, autoincrement=True)
    baslik_id        = db.Column(db.Integer, db.ForeignKey('belge_baslik.id', ondelete='CASCADE'), nullable=False)
    sira_no          = db.Column(db.SmallInteger, nullable=False)
    stok_id          = db.Column(db.Integer, db.ForeignKey('stok_karti.id', ondelete='SET NULL'))
    aciklama         = db.Column(db.String(500))
    miktar           = db.Column(db.Numeric(15, 4), nullable=False, default=1.0)
    birim_id         = db.Column(db.Integer, db.ForeignKey('birim.id', ondelete='RESTRICT'))
    donusum_carpan   = db.Column(db.Numeric(20, 6), default=1.0)
    cevrilen_miktar  = db.Column(db.Numeric(15, 4))
    birim_fiyat      = db.Column(db.Numeric(15, 4), nullable=False, default=0.0)
    iskonto_oran     = db.Column(db.Numeric(5,  2), default=0.00)
    kdv_orani        = db.Column(db.Numeric(5,  2), default=20.00)
    kdvsiz_tutar     = db.Column(db.Numeric(15, 2), default=0.00)
    kdv_tutar        = db.Column(db.Numeric(15, 2), default=0.00)
    kdvli_tutar      = db.Column(db.Numeric(15, 2), default=0.00)
    olusturma_tarihi  = db.Column(db.DateTime, default=datetime.now)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    stok  = db.relationship('StokKarti')
    birim = db.relationship('Birim')

    __table_args__ = (
        db.Index('ix_bs_baslik', 'baslik_id'),
        db.Index('ix_bs_stok',   'stok_id'),
    )

    def cevrilen_miktar_hesapla(self) -> float:
        return float(self.miktar or 0) * float(self.donusum_carpan or 1)
