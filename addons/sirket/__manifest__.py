"""
addons/sirket/__manifest__.py — Modül bildirimi (Odoo'nun __manifest__.py'ı)

Her addon, kendi bağımlılıklarını burada bildirir. core/registry.py bu
bilgiyi okuyarak addon'ları doğru SIRADA yükler (bağımlılığı önce yüklenir).

Bu sadece BİLDİRİM amaçlıdır — gerçek import zorlaması yapmaz, ama
register_addons() çalışırken bağımlılık sırasını kontrol etmek için
core/registry.py tarafından okunur.
"""

MANIFEST = {
    'ad': 'Şirket',
    'aciklama': 'Çok şirketli yapı: şirket, depo, numara serisi, dönem kilidi.',
    'bagimliliklar': [],   # En temel modül — başka hiçbir addon'a bağımlı değil
    'surum': '1.0.0',
}
