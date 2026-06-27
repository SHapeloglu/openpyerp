"""app.py — Flask uygulama fabrikası"""
import logging
from flask import Flask
from core.extensions import db, csrf
from core.registry import register_addons

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s — %(message)s')
logger = logging.getLogger(__name__)


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object('config.Config')
    if test_config:
        app.config.update(test_config)

    _tum_modelleri_import_et()

    db.init_app(app)
    csrf.init_app(app)

    with app.app_context():
        register_addons(app)

    _genel_routelari_kaydet(app)
    logger.info("OpenPyERP başlatıldı")
    return app


def _tum_modelleri_import_et():
    import addons.ayarlar.models   # noqa
    import addons.sirket.models    # noqa
    import addons.birim.models     # noqa
    import addons.cari.models      # noqa
    import addons.stok.models      # noqa
    import addons.finans.models    # noqa
    import addons.belge.models     # noqa
    import addons.uretim.models    # noqa
    import addons.personel.models  # noqa


def _genel_routelari_kaydet(app):
    from flask import redirect, url_for, jsonify
    from core.registry import yuklenmis_addonlar

    @app.route('/')
    def index():
        return redirect(url_for('dashboard.index'))

    @app.route('/health')
    def health():
        try:
            db.session.execute(db.text('SELECT 1'))
            db_durum = 'ok'
        except Exception as e:
            db_durum = f'hata: {e}'
        return jsonify({
            'durum': 'ok' if db_durum == 'ok' else 'hata',
            'db': db_durum,
            'yuklenmis_addonlar': yuklenmis_addonlar(),
        })
