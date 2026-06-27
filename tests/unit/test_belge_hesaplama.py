"""
tests/unit/test_belge_hesaplama.py — Saf domain mantığı testleri

Bu testler HİÇBİR DB bağlantısı, Flask app context'i veya HTTP isteği
gerektirmez — çünkü addons/belge/services.py içindeki hesaplama
fonksiyonları (satir_hesapla, baslik_toplamla) saf Python'dur.

Bu, katmanlı mimarinin somut faydası: eski app.py'de satir_hesapla()
test etmek için Flask app başlatmak, test DB kurmak, HTTP request mock'lamak
gerekirdi. Şimdi tek satır yeterli.
"""
import pytest
from decimal import Decimal

from addons.belge.services import satir_hesapla


class TestSatirHesapla:
    """satir_hesapla(miktar, birim_fiyat, iskonto_oran, kdv_orani) → (kdvsiz, kdv, kdvli)"""

    def test_temel_hesaplama(self):
        kdvsiz, kdv, kdvli = satir_hesapla(10, 100, 0, 20)
        assert kdvsiz == 1000.00
        assert kdv == 200.00
        assert kdvli == 1200.00

    def test_iskonto_uygulanir(self):
        """10 birim × 100 TL, %10 iskonto → 900 TL KDV hariç"""
        kdvsiz, kdv, kdvli = satir_hesapla(10, 100, 10, 20)
        assert kdvsiz == 900.00
        assert kdv == 180.00
        assert kdvli == 1080.00

    def test_sifir_miktar(self):
        kdvsiz, kdv, kdvli = satir_hesapla(0, 100, 0, 20)
        assert kdvsiz == 0.00
        assert kdv == 0.00
        assert kdvli == 0.00

    def test_tam_iskonto(self):
        """% 100 iskonto → her şey sıfır"""
        kdvsiz, kdv, kdvli = satir_hesapla(10, 100, 100, 20)
        assert kdvsiz == 0.00
        assert kdv == 0.00
        assert kdvli == 0.00

    def test_kurus_hassasiyeti(self):
        """0.005 TL → ROUND_HALF_UP ile 0.01 TL'ye yuvarlanmalı"""
        kdvsiz, kdv, kdvli = satir_hesapla(1, 0.005, 0, 0)
        assert kdvsiz == 0.01

    def test_ondalikli_miktar(self):
        """1.5 birim × 10 TL = 15 TL"""
        kdvsiz, kdv, kdvli = satir_hesapla(1.5, 10, 0, 18)
        assert kdvsiz == 15.00
        assert round(kdv, 2) == 2.70
        assert round(kdvli, 2) == 17.70

    def test_sifir_kdv(self):
        """Temel gıda gibi %0 KDV'li ürünler"""
        kdvsiz, kdv, kdvli = satir_hesapla(100, 5, 0, 0)
        assert kdvsiz == 500.00
        assert kdv == 0.00
        assert kdvli == 500.00

    def test_string_degerler_kabul_edilir(self):
        """Form'dan gelen string değerler (core.para.miktar_d/para ile işlenir)"""
        kdvsiz, kdv, kdvli = satir_hesapla('5', '200.50', '0', '20')
        assert kdvsiz == 1002.50


class TestExtendModel:
    """extend_model() şema genişletme mekanizması — Odoo'nun _inherit'ine karşılık."""

    def test_mixin_alani_hedef_modele_eklenir(self):
        """Mixin'deki bir alan, extend_model sonrası hedef modelden erişilebilir olmalı."""
        from core.registry import extend_model
        from addons.stok.models import StokKarti

        class TestMixin:
            test_alani_xyz = 'test_değeri'

        extend_model(StokKarti, TestMixin)
        assert hasattr(StokKarti, 'test_alani_xyz')
        assert StokKarti.test_alani_xyz == 'test_değeri'

    def test_mevcut_alan_uzerine_yazilmaz(self):
        """Hedef modelde zaten var olan bir alan, mixin tarafından ezilmemeli."""
        from core.registry import extend_model
        from addons.stok.models import StokKarti

        orijinal_ad = StokKarti.ad

        class CakisanMixin:
            ad = 'YANLIS_DEGER'

        extend_model(StokKarti, CakisanMixin)
        # 'ad' alanı değişmemiş olmalı
        assert StokKarti.ad is orijinal_ad

    def test_dunder_alanlar_atlanir(self):
        """__tablename__ gibi dunder alanlar extend_model tarafından atlanmalı."""
        from core.registry import extend_model
        from addons.stok.models import StokKarti

        class DunderMixin:
            __tablename__ = 'BASKA_TABLO'
            gercek_alan = 'deger'

        orijinal_tablo = StokKarti.__tablename__
        extend_model(StokKarti, DunderMixin)
        assert StokKarti.__tablename__ == orijinal_tablo


class TestHooks:
    """core/hooks.py — emit/on sinyal mekanizması testleri."""

    def test_dinleyici_cagirilir(self):
        from core.hooks import on, emit

        cagirildi = []

        @on('test.olay')
        def dinleyici(**kwargs):
            cagirildi.append(kwargs)

        emit('test.olay', veri='merhaba')
        assert len(cagirildi) == 1
        assert cagirildi[0]['veri'] == 'merhaba'

    def test_dinleyici_olmadan_emit_hata_vermez(self):
        from core.hooks import emit
        emit('var.olmayan.olay')  # Exception fırlatmamalı

    def test_birden_fazla_dinleyici_sirayla_cagirilir(self):
        from core.hooks import on, emit

        sira = []

        @on('sira.olay')
        def birinci(**kwargs):
            sira.append(1)

        @on('sira.olay')
        def ikinci(**kwargs):
            sira.append(2)

        emit('sira.olay')
        assert sira == [1, 2]

    def test_dinleyici_hata_yayilir(self):
        from core.hooks import on, emit

        @on('hata.olay')
        def hata_fırlatan(**kwargs):
            raise ValueError('Kasıtlı test hatası')

        with pytest.raises(ValueError, match='Kasıtlı test hatası'):
            emit('hata.olay')


class TestDonemServisi:
    """addons/sirket/services.py — dönem kilidi kontrolü."""

    def test_kilitli_donem(self, db, sirket):
        from datetime import date
        from addons.sirket.models import DonemKilidi
        from addons.sirket.services import donem_kilitli_mi

        kilit = DonemKilidi(sirket_id=sirket.id, yil=2026, ay=1, kilitli=True)
        db.session.add(kilit)
        db.session.commit()

        test_tarihi = date(2026, 1, 15)
        assert donem_kilitli_mi(sirket.id, test_tarihi) is True

    def test_acik_donem(self, db, sirket):
        from datetime import date
        from addons.sirket.services import donem_kilitli_mi

        test_tarihi = date(2026, 6, 1)
        assert donem_kilitli_mi(sirket.id, test_tarihi) is False

    def test_yillik_kilit(self, db, sirket):
        from datetime import date
        from addons.sirket.models import DonemKilidi
        from addons.sirket.services import donem_kilitli_mi

        kilit = DonemKilidi(sirket_id=sirket.id, yil=2025, ay=None, kilitli=True)
        db.session.add(kilit)
        db.session.commit()

        # Yılın herhangi bir ayı kilitli olmalı
        assert donem_kilitli_mi(sirket.id, date(2025, 3, 1)) is True
        assert donem_kilitli_mi(sirket.id, date(2025, 12, 31)) is True
        # 2026 açık
        assert donem_kilitli_mi(sirket.id, date(2026, 1, 1)) is False
