"""
tests/integration/test_belge_servisi.py — BelgeKaydetServisi entegrasyon testleri

Bu testler DB (SQLite in-memory) gerektirir ama Flask HTTP katmanı gerektirmez.
BelgeKaydetServisi direkt çağrılır — HTTP route test edilmez.

Bu ayrım önemli: bir HTTP testinde 200/302 dönüyor ama DB'ye yanlış yazıyor
olabilir. Servis testleri bunu yakalar.
"""
import pytest
from datetime import date

from addons.belge.dto import BelgeKaydetGirdi, BelgeSatirGirdi
from addons.belge.services import BelgeKaydetServisi, BelgeDonusturServisi, BelgeSilServisi
from addons.belge.models import BelgeBaslik, BelgeSatir
from addons.stok.models import StokHareket
from addons.cari.models import CariHareket


def _fatura_girdi(sirket_id, cari_id, stok_id, birim_id, miktar=5, fiyat=200):
    """Test için standart fatura girdi DTO'su oluşturur."""
    return BelgeKaydetGirdi(
        belge_tip='FATURA', cari_tip='SATIS', tarih=date.today(),
        cari_id=cari_id, sirket_id=sirket_id, durum='ACIK',
        satirlar=[BelgeSatirGirdi(
            stok_id=stok_id, miktar=miktar, birim_fiyat=fiyat,
            birim_id=birim_id, kdv_orani=20, iskonto_oran=0,
        )],
    )


class TestBelgeKaydet:

    def test_yeni_fatura_basarili_kaydedilir(self, db, sirket, cari, stok_karti, birim):
        """Temel senaryo: fatura kaydedilir, cari ve stok hareketi oluşur."""
        # Önce giriş hareketi koy (negatif stok kontrolü geçsin)
        from addons.stok.services import stok_hareketi_olustur
        stok_hareketi_olustur(
            stok_id=stok_karti.id, tarih=date.today(), hareket_tipi='GIRIS',
            miktar=100, cevrilen_miktar=100, birim_id=birim.id, belge_no='GRS001',
        )
        db.session.commit()

        girdi = _fatura_girdi(sirket.id, cari.id, stok_karti.id, birim.id)
        sonuc = BelgeKaydetServisi().kaydet(girdi)

        assert sonuc.basarili is True
        assert sonuc.belge_no is not None

        # DB'de belge var mı?
        baslik = BelgeBaslik.query.filter_by(id=sonuc.belge_id).first()
        assert baslik is not None
        assert baslik.belge_tip == 'FATURA'
        assert round(float(baslik.toplam_kdvsiz), 2) == 1000.00  # 5 × 200
        assert round(float(baslik.toplam_kdv), 2) == 200.00
        assert round(float(baslik.toplam_kdvli), 2) == 1200.00

    def test_fatura_cari_hareketi_olusturur(self, db, sirket, cari, stok_karti, birim):
        """Fatura kaydedilince cari borç hareketi oluşmalı."""
        from addons.stok.services import stok_hareketi_olustur
        stok_hareketi_olustur(stok_id=stok_karti.id, tarih=date.today(),
                              hareket_tipi='GIRIS', miktar=50, cevrilen_miktar=50, birim_id=birim.id, belge_no='G1')
        db.session.commit()

        girdi = _fatura_girdi(sirket.id, cari.id, stok_karti.id, birim.id)
        sonuc = BelgeKaydetServisi().kaydet(girdi)
        assert sonuc.basarili

        ch = CariHareket.query.filter_by(cari_id=cari.id, kaynak_tip='FATURA').first()
        assert ch is not None
        assert ch.hareket_tipi == 'BORC'
        assert round(float(ch.tutar), 2) == 1200.00

    def test_fatura_stok_hareketi_olusturur(self, db, sirket, cari, stok_karti, birim):
        """Satış faturasında stok ÇIKIŞ hareketi oluşmalı."""
        from addons.stok.services import stok_hareketi_olustur
        stok_hareketi_olustur(stok_id=stok_karti.id, tarih=date.today(),
                              hareket_tipi='GIRIS', miktar=50, cevrilen_miktar=50, birim_id=birim.id, belge_no='G1')
        db.session.commit()

        girdi = _fatura_girdi(sirket.id, cari.id, stok_karti.id, birim.id, miktar=5)
        sonuc = BelgeKaydetServisi().kaydet(girdi)
        assert sonuc.basarili

        sh = StokHareket.query.filter_by(stok_id=stok_karti.id, hareket_tipi='CIKIS').first()
        assert sh is not None
        assert float(sh.miktar) == 5.0

    def test_yetersiz_stok_hata_verir(self, db, sirket, cari, stok_karti, birim):
        """Stok yokken fatura kaydı başarısız olmalı — YetersizStokHatasi."""
        girdi = _fatura_girdi(sirket.id, cari.id, stok_karti.id, birim.id, miktar=999)
        sonuc = BelgeKaydetServisi().kaydet(girdi)

        assert sonuc.basarili is False
        assert sonuc.hata_kodu == 'YETERSIZ_STOK'
        # DB'ye yazılmamış olmalı
        assert BelgeBaslik.query.count() == 0

    def test_donem_kilidi_hata_verir(self, db, sirket, cari, stok_karti, birim):
        """Kilitli dönemde fatura kaydı başarısız olmalı."""
        from addons.sirket.models import DonemKilidi
        kilit = DonemKilidi(sirket_id=sirket.id, yil=date.today().year,
                            ay=date.today().month, kilitli=True)
        db.session.add(kilit)
        db.session.commit()

        girdi = _fatura_girdi(sirket.id, cari.id, stok_karti.id, birim.id)
        sonuc = BelgeKaydetServisi().kaydet(girdi)

        assert sonuc.basarili is False
        assert sonuc.hata_kodu == 'DONEM_KILITLI'

    def test_belge_guncelleme(self, db, sirket, cari, stok_karti, birim):
        """Mevcut belge güncellenince cari hareketi yeniden hesaplanmalı."""
        from addons.stok.services import stok_hareketi_olustur
        stok_hareketi_olustur(stok_id=stok_karti.id, tarih=date.today(),
                              hareket_tipi='GIRIS', miktar=50, cevrilen_miktar=50, birim_id=birim.id, belge_no='G1')
        db.session.commit()

        girdi = _fatura_girdi(sirket.id, cari.id, stok_karti.id, birim.id, miktar=2, fiyat=100)
        sonuc = BelgeKaydetServisi().kaydet(girdi)
        assert sonuc.basarili

        # Fiyatı güncelle
        girdi2 = _fatura_girdi(sirket.id, cari.id, stok_karti.id, birim.id, miktar=3, fiyat=150)
        girdi2.baslik_id = sonuc.belge_id
        sonuc2 = BelgeKaydetServisi().kaydet(girdi2)
        assert sonuc2.basarili

        ch = CariHareket.query.filter_by(cari_id=cari.id, kaynak_tip='FATURA').all()
        assert len(ch) == 1  # Güncelleme: eski silindi, yeni eklendi
        assert round(float(ch[0].tutar), 2) == 540.00  # 3 × 150 × 1.20


class TestBelgeDonustur:

    def _onaylandi_siparis_olustur(self, db, sirket, cari, stok_karti, birim):
        """Test için onaylı bir sipariş oluşturur."""
        from addons.sirket.services import yeni_belge_no
        baslik = BelgeBaslik(
            belge_tip='SIPARIS', belge_no=yeni_belge_no('SIPARIS', 'SATIS', sirket.id),
            tarih=date.today(), cari_id=cari.id, cari_tip='SATIS',
            durum='ONAYLANDI', sirket_id=sirket.id,
        )
        db.session.add(baslik)
        db.session.flush()
        satir = BelgeSatir(
            baslik_id=baslik.id, sira_no=1, stok_id=stok_karti.id,
            miktar=10, birim_id=birim.id, birim_fiyat=100, kdv_orani=20,
            kdvsiz_tutar=1000, kdv_tutar=200, kdvli_tutar=1200,
        )
        db.session.add(satir)
        db.session.commit()
        return baslik

    def test_siparis_irsaliyeye_donusur(self, db, sirket, cari, stok_karti, birim):
        siparis = self._onaylandi_siparis_olustur(db, sirket, cari, stok_karti, birim)
        irsaliye = BelgeDonusturServisi().donustur(siparis.id, 'IRSALIYE')

        assert irsaliye.belge_tip == 'IRSALIYE'
        assert irsaliye.durum == 'TASLAK'
        assert irsaliye.kaynak_belge_id == siparis.id
        assert len(irsaliye.satirlar) == 1

    def test_onaylanmamis_belge_donusturulemez(self, db, sirket, cari, stok_karti, birim):
        from addons.sirket.services import yeni_belge_no
        from addons.belge.services import BelgeDonusturHatasi
        taslak = BelgeBaslik(
            belge_tip='SIPARIS', belge_no=yeni_belge_no('SIPARIS', 'SATIS', sirket.id),
            tarih=date.today(), cari_id=cari.id, cari_tip='SATIS',
            durum='ACIK', sirket_id=sirket.id,
        )
        db.session.add(taslak)
        db.session.commit()

        with pytest.raises(BelgeDonusturHatasi, match='henüz onaylanmamış'):
            BelgeDonusturServisi().donustur(taslak.id, 'IRSALIYE')
