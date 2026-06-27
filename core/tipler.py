"""
core/tipler.py — Uygulama geneli sabit setler ve VARCHAR yardımcısı

NEDEN db.Enum KULLANMIYORUZ?
    SQLAlchemy'nin db.Enum() MariaDB'de native ENUM, PostgreSQL'de CREATE TYPE
    üretir. Her ikisinde de sonradan değer eklemek özel ALTER TABLE sözdizimi
    gerektirir ve üretim tablosunda yavaş olabilir.

    Çözüm: VARCHAR(30) + uygulama katmanında kontrol.
    - Migration: sadece op.add_column(sa.String(30)) — her DB'de aynı
    - Yeni durum eklemek: sadece bu dosyada sabite ekle, migration YOK
    - SQLAlchemy CheckConstraint ile DB düzeyinde de doğrulama yapılabilir
      (opsiyonel, performans odaklı projelerde)

KULLANIM:
    from core.tipler import D, BelgeTip, Durum

    # Model tanımında:
    belge_tip = db.Column(D.STR_30, nullable=False)

    # İş kuralında:
    assert belge.belge_tip in BelgeTip.TUMU

    # Workflow guard'ında:
    if belge.belge_tip not in BelgeTip.STOK_ETKILI:
        return  # stok hareketi oluşturma
"""
from core.extensions import db


# ── Sütun tip kısayolları ─────────────────────────────────────────────────

class D:
    """Sık kullanılan SQLAlchemy kolon tipleri için kısayollar."""
    STR_10  = db.String(10)
    STR_20  = db.String(20)
    STR_30  = db.String(30)
    STR_50  = db.String(50)
    STR_100 = db.String(100)
    STR_200 = db.String(200)
    PARA    = db.Numeric(15, 2)
    MIKTAR  = db.Numeric(15, 4)
    ORAN    = db.Numeric(5, 2)


# ── İş alanı sabitleri ────────────────────────────────────────────────────

class BelgeTip:
    TALEP    = 'TALEP'
    SIPARIS  = 'SIPARIS'
    IRSALIYE = 'IRSALIYE'
    FATURA   = 'FATURA'
    TUMU     = {TALEP, SIPARIS, IRSALIYE, FATURA}
    # Stok hareketi OLUŞTURAN belge tipleri (İrsaliye onayı da stok etkiler)
    STOK_ETKILI = {IRSALIYE, FATURA}

    ADLAR = {
        TALEP: 'Talep', SIPARIS: 'Sipariş',
        IRSALIYE: 'İrsaliye', FATURA: 'Fatura',
    }
    # Dönüşüm zinciri: bu tip → bir üst tip
    DONUSUM = {
        TALEP:    SIPARIS,
        SIPARIS:  IRSALIYE,
        IRSALIYE: FATURA,
    }


class CariTip:
    SATIS     = 'SATIS'
    ALIS      = 'ALIS'
    TUMU      = {SATIS, ALIS}
    # Satışta cari BORÇLANIR, alışta ALACAKLANIR
    CARI_HAREKET = {SATIS: 'BORC', ALIS: 'ALACAK'}
    # Satışta stok ÇIKIŞ, alışta GİRİŞ
    STOK_HAREKET = {SATIS: 'CIKIS', ALIS: 'GIRIS'}


class BelgeDurum:
    TASLAK    = 'TASLAK'
    ACIK      = 'ACIK'
    ONAYLANDI = 'ONAYLANDI'
    IPTAL     = 'IPTAL'
    TUMU      = {TASLAK, ACIK, ONAYLANDI, IPTAL}
    # Değiştirilebilir durumlar (kilitli değil)
    DUZENLENEBILIR = {TASLAK, ACIK}
    # Silinebilir durumlar
    SILINEBILIR = {TASLAK, ACIK}


class SevkDurum:
    SEVK_EDILMEDI      = 'SEVK_EDILMEDI'
    KISMI_SEVK         = 'KISMI_SEVK'
    TUMU_SEVK_EDILDI   = 'TUMU_SEVK_EDILDI'
    TUMU = {SEVK_EDILMEDI, KISMI_SEVK, TUMU_SEVK_EDILDI}


class HareketTip:
    BORC    = 'BORC'
    ALACAK  = 'ALACAK'
    GIRIS   = 'GIRIS'
    CIKIS   = 'CIKIS'


class StokTip:
    MALZEME = 'MALZEME'
    HIZMET  = 'HIZMET'
    TUMU    = {MALZEME, HIZMET}


class KullaniciRol:
    ADMIN        = 'ADMIN'
    KULLANICI    = 'KULLANICI'
    SADECE_OKUMA = 'SADECE_OKUMA'
    MUHASEBECI   = 'MUHASEBECI'
    TUMU         = {ADMIN, KULLANICI, SADECE_OKUMA, MUHASEBECI}
