"""
core/extensions.py — Paylaşılan Flask eklentileri

Odoo'nun `odoo/models.py` ile tek bir ORM kayıt noktası sağlamasına benzer şekilde,
bu modül tüm addon'ların import edeceği TEK `db` (SQLAlchemy) ve `csrf` (CSRFProtect)
örneğini barındırır.

Neden ayrı bir dosya?
    Eski app.py'de `db = SQLAlchemy(app)` app.py içinde tanımlanıyordu. Bu, her
    addon'un modellerini tanımlamak için app.py'yi import etmesini gerektirirdi —
    bu da dairesel import (circular import) riskini doğurur:
        app.py -> addons.cari.models -> app.py (db için)  # ÇÖKER

    Çözüm: db nesnesi burada, hiçbir addon'a bağımlı olmayan bu dosyada yaşar.
    Addon'lar `from core.extensions import db` ile import eder, app.py ise
    factory içinde `db.init_app(app)` çağırır.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
csrf = CSRFProtect()
