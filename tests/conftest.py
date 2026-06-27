"""
tests/conftest.py — Pytest fixtures ve test izolasyonu

NEDEN BU DOSYA KRİTİK?
    Eski CariMatik'te test yoktu. Bu, 11.597 satırlık bir uygulamanın
    herhangi bir refactor'ında "acaba bir şeyi bozduk mu?" sorusuna
    cevap verilemiyordu demektir.

    Odoo'nun test altyapısı (odoo.tests.common.TransactionCase) her test
    için ayrı bir transaction başlatır ve test bitince rollback yapar.
    Burada aynı prensibi pytest-flask + SQLite in-memory ile uyguluyoruz:

    - Her test kendi Flask app örneğini alır (factory pattern sayesinde)
    - DB SQLite in-memory — MySQL kurulumu gerektirmez, hızlıdır
    - Her test sonunda db.session.remove() + tablolar temizlenir
    - Hook dinleyicileri her test için sıfırlanır (test kirliliği önlenir)
"""
import pytest

from app import create_app
from core.extensions import db as _db
from core.hooks import dinleyicileri_temizle


TEST_CONFIG = {
    'TESTING': True,
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    'WTF_CSRF_ENABLED': False,   # test'te CSRF token gerekmez
    'SECRET_KEY': 'test-secret-key',
}


@pytest.fixture(scope='session')
def app():
    """Session boyunca tek Flask app örneği — sadece bir kere oluşturulur."""
    uygulama = create_app(TEST_CONFIG)
    with uygulama.app_context():
        _db.create_all()
        yield uygulama
        _db.drop_all()


@pytest.fixture(scope='function')
def db(app):
    """Her test için temiz DB durumu.

    Test öncesi tüm tabloları temizler, test sonrası session'ı kapatır.
    Bu, Odoo'nun TransactionCase'inin rollback stratejisine karşılık gelir.
    """
    with app.app_context():
        # Tüm tabloları temizle
        for tablo in reversed(_db.metadata.sorted_tables):
            _db.session.execute(tablo.delete())
        _db.session.commit()
        yield _db
        _db.session.remove()


@pytest.fixture(scope='function', autouse=True)
def hook_temizle():
    """Her testten sonra hook dinleyicilerini temizle.

    Test A'da kayıtlı bir dinleyici test B'yi etkilemesin.
    """
    yield
    dinleyicileri_temizle()


@pytest.fixture
def client(app):
    """Flask test client'ı — HTTP endpoint'lerini test etmek için."""
    return app.test_client()


@pytest.fixture
def sirket(db):
    """Testlerde kullanmak için temel şirket fixture'ı."""
    from addons.sirket.models import Sirket
    s = Sirket(kod='TEST', unvan='Test Şirketi A.Ş.', aktif=True)
    db.session.add(s)
    db.session.commit()
    return s


@pytest.fixture
def birim(db):
    """Testlerde kullanmak için temel birim fixture'ı."""
    from addons.birim.models import BirimGrubu, Birim
    grup = BirimGrubu(ad='Adet')
    db.session.add(grup)
    db.session.flush()
    b = Birim(grup_id=grup.id, kod='ADET', ad='Adet', katsayi=1.0, taban_mi=True)
    db.session.add(b)
    db.session.commit()
    return b


@pytest.fixture
def stok_karti(db, sirket, birim):
    """Testlerde kullanmak için temel stok kartı fixture'ı."""
    from addons.stok.models import StokKarti
    s = StokKarti(
        sirket_id=sirket.id, kod='TST001', ad='Test Malzemesi',
        tip='MALZEME', birim_id=birim.id, kdv_orani=20, satis_fiyati=100.0,
    )
    db.session.add(s)
    db.session.commit()
    return s


@pytest.fixture
def cari(db, sirket):
    """Testlerde kullanmak için temel cari fixture'ı."""
    from addons.cari.models import Cari
    c = Cari(sirket_id=sirket.id, kod='C001', unvan='Test Müşterisi Ltd.', tip='ALICI')
    db.session.add(c)
    db.session.commit()
    return c
