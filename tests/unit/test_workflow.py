"""tests/unit/test_workflow.py — core/workflow.py ve belge/uretim workflow testleri"""
import pytest
from unittest.mock import MagicMock
from core.workflow import Workflow, Gecis, GecersizGecisHatasi, GuardReddiHatasi
from core.tipler import BelgeDurum


# ════════ CORE WORKFLOW MOTORU ════════

class TestWorkflowMotoru:

    def _basit_wf(self):
        return Workflow(
            durumlar=['A', 'B', 'C', 'IPTAL'],
            gecisler=[
                Gecis('A', 'B', isim='A→B'),
                Gecis('B', 'C', isim='B→C'),
                Gecis('B', 'IPTAL', isim='İptal'),
            ],
            baslangic='A',
        )

    def _nesne(self, durum='A'):
        n = MagicMock()
        n.durum = durum
        return n

    def test_gecerli_gecis_durumu_gunceller(self):
        wf = self._basit_wf()
        n = self._nesne('A')
        wf.gecer(n, 'B')
        assert n.durum == 'B'

    def test_tanimsiz_gecis_hata_firlatir(self):
        wf = self._basit_wf()
        n = self._nesne('A')
        with pytest.raises(GecersizGecisHatasi) as exc:
            wf.gecer(n, 'C')  # A→C tanımlı değil
        assert 'A' in str(exc.value)
        assert 'C' in str(exc.value)

    def test_guard_red_gecisi_engeller(self):
        def kotu_guard(nesne, **ctx):
            raise GuardReddiHatasi('Yasak!', kod='YASAK')

        wf = Workflow(
            durumlar=['A', 'B'],
            gecisler=[Gecis('A', 'B', isim='Git', guard=kotu_guard)],
            baslangic='A',
        )
        n = self._nesne('A')
        with pytest.raises(GuardReddiHatasi, match='Yasak!'):
            wf.gecer(n, 'B')
        assert n.durum == 'A'  # Durum değişmedi

    def test_action_gecis_sonrasi_cagirilir(self):
        eylemler = []
        def action(nesne, **ctx):
            eylemler.append(nesne.durum)

        wf = Workflow(
            durumlar=['A', 'B'],
            gecisler=[Gecis('A', 'B', isim='Git', action=action)],
            baslangic='A',
        )
        n = self._nesne('A')
        wf.gecer(n, 'B')
        # Action, durum güncellendikten SONRA çağrılır
        assert eylemler == ['B']

    def test_mevcut_gecisler_listesi(self):
        wf = self._basit_wf()
        n = self._nesne('B')
        gecisler = wf.mevcut_gecisler(n)
        isimler = [g.isim for g in gecisler]
        assert 'B→C' in isimler
        assert 'İptal' in isimler
        assert 'A→B' not in isimler  # A durumundan geçiş, B'de listede olmaz

    def test_gecis_gecerli_mi(self):
        wf = self._basit_wf()
        n = self._nesne('A')
        assert wf.gecis_gecerli_mi(n, 'B') is True
        assert wf.gecis_gecerli_mi(n, 'C') is False

    def test_workflow_gecis_olayi_yayinlanir(self):
        from core.hooks import on, emit
        kayitlar = []

        @on('workflow.gecis')
        def dinle(kayit, **kw):
            kayitlar.append(kayit)

        wf = self._basit_wf()
        n = self._nesne('A')
        n.id = 99
        wf.gecer(n, 'B', kullanici_id=7)

        assert len(kayitlar) == 1
        assert kayitlar[0].eski_durum == 'A'
        assert kayitlar[0].yeni_durum == 'B'
        assert kayitlar[0].kullanici_id == 7


# ════════ BELGE WORKFLOW ════════

class TestBelgeWorkflow:
    """addons/belge/workflow.py — BELGE_WF entegrasyon testleri (DB gerekli)"""

    def test_taslak_acik_gecisi(self, db, sirket, cari, stok_karti, birim):
        from addons.belge.models import BelgeBaslik
        from addons.belge.workflow import BELGE_WF
        from addons.sirket.services import yeni_belge_no
        from datetime import date

        baslik = BelgeBaslik(
            belge_tip='FATURA', belge_no=yeni_belge_no('FATURA', 'SATIS', sirket.id),
            tarih=date.today(), cari_id=cari.id, cari_tip='SATIS',
            durum=BelgeDurum.TASLAK, sirket_id=sirket.id,
        )
        db.session.add(baslik)
        db.session.commit()

        BELGE_WF.gecer(baslik, BelgeDurum.ACIK)
        assert baslik.durum == BelgeDurum.ACIK

    def test_cari_eksik_onay_reddedilir(self, db, sirket, stok_karti, birim):
        from addons.belge.models import BelgeBaslik, BelgeSatir
        from addons.belge.workflow import BELGE_WF
        from addons.sirket.services import yeni_belge_no
        from datetime import date

        baslik = BelgeBaslik(
            belge_tip='FATURA', belge_no=yeni_belge_no('FATURA', 'SATIS', sirket.id),
            tarih=date.today(), cari_id=None, cari_tip='SATIS',  # Cari YOK
            durum=BelgeDurum.ACIK, sirket_id=sirket.id,
        )
        db.session.add(baslik)
        db.session.flush()
        db.session.add(BelgeSatir(
            baslik_id=baslik.id, sira_no=1, stok_id=stok_karti.id,
            miktar=1, birim_id=birim.id, birim_fiyat=100, kdv_orani=20,
            kdvsiz_tutar=100, kdv_tutar=20, kdvli_tutar=120,
        ))
        db.session.commit()

        with pytest.raises(GuardReddiHatasi) as exc:
            BELGE_WF.gecer(baslik, BelgeDurum.ONAYLANDI)
        assert exc.value.kod == 'CARI_EKSIK'
        assert baslik.durum == BelgeDurum.ACIK  # Değişmedi

    def test_acik_iptal_gecisi(self, db, sirket, cari):
        from addons.belge.models import BelgeBaslik
        from addons.belge.workflow import BELGE_WF
        from addons.sirket.services import yeni_belge_no
        from datetime import date

        baslik = BelgeBaslik(
            belge_tip='SIPARIS', belge_no=yeni_belge_no('SIPARIS', 'SATIS', sirket.id),
            tarih=date.today(), cari_id=cari.id, cari_tip='SATIS',
            durum=BelgeDurum.ACIK, sirket_id=sirket.id,
        )
        db.session.add(baslik)
        db.session.commit()

        BELGE_WF.gecer(baslik, BelgeDurum.IPTAL)
        assert baslik.durum == BelgeDurum.IPTAL

    def test_onaylandi_acik_gecisi_tanimsiz(self, db, sirket, cari):
        from addons.belge.models import BelgeBaslik
        from addons.belge.workflow import BELGE_WF
        from addons.sirket.services import yeni_belge_no
        from datetime import date

        baslik = BelgeBaslik(
            belge_tip='FATURA', belge_no=yeni_belge_no('FATURA', 'SATIS', sirket.id),
            tarih=date.today(), cari_id=cari.id, cari_tip='SATIS',
            durum=BelgeDurum.ONAYLANDI, sirket_id=sirket.id,
        )
        db.session.add(baslik)
        db.session.commit()

        # ONAYLANDI → ACIK geçişi yoktur (sadece IPTAL var)
        with pytest.raises(GecersizGecisHatasi):
            BELGE_WF.gecer(baslik, BelgeDurum.ACIK)

    def test_mevcut_gecisler_template_icin(self, db, sirket, cari):
        """Template, hangi butonu göstereceğini bu metoddan öğrenir."""
        from addons.belge.models import BelgeBaslik
        from addons.sirket.services import yeni_belge_no
        from datetime import date

        baslik = BelgeBaslik(
            belge_tip='FATURA', belge_no=yeni_belge_no('FATURA', 'SATIS', sirket.id),
            tarih=date.today(), cari_id=cari.id, cari_tip='SATIS',
            durum=BelgeDurum.ACIK, sirket_id=sirket.id,
        )
        db.session.add(baslik)
        db.session.commit()

        gecisler = baslik.mevcut_gecisler()
        isimler = [g.isim for g in gecisler]
        assert 'Onayla' in isimler
        assert 'İptal Et' in isimler
        assert 'Aç' not in isimler  # TASLAK→ACIK, ACIK için listede yok
