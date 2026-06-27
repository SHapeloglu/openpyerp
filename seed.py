"""
seed.py — Başlangıç verisi yükleyici

Kullanım (migration sonrası):
    python seed.py

Oluşturur:
    - 1 admin kullanıcı (email: admin@openpyerp.local, şifre: Admin1234!)
    - 1 örnek şirket
    - Temel birim grubu + birimler (Adet, KG, Litre, Kutu, Koli)
    - Belge numara serileri (Fatura, Sipariş, İrsaliye, Talep)
    - 1 varsayılan depo

Production'da bu scripti çalıştırdıktan sonra admin şifresini DEĞİŞTİRİN.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from core.extensions import db
from addons.ayarlar.models import Kullanici
from addons.sirket.models import Sirket, Depo, NumaraSira, DonemKilidi
from addons.birim.models import BirimGrubu, Birim

app = create_app()

with app.app_context():

    # ── Admin kullanıcı ──────────────────────────────────────────────
    if not Kullanici.query.filter_by(email='admin@openpyerp.local').first():
        admin = Kullanici(
            ad_soyad='Sistem Yöneticisi',
            email='admin@openpyerp.local',
            sifre_hash=Kullanici.sifre_hashle('Admin1234!'),
            rol='ADMIN',
            aktif=True,
        )
        db.session.add(admin)
        db.session.flush()
        print("✓ Admin kullanıcı oluşturuldu → admin@openpyerp.local / Admin1234!")
    else:
        admin = Kullanici.query.filter_by(email='admin@openpyerp.local').first()
        print("→ Admin kullanıcı zaten var, atlanıyor")

    # ── Şirket ──────────────────────────────────────────────────────
    if not Sirket.query.first():
        sirket = Sirket(
            kod='DEMO',
            unvan='Demo Şirketi A.Ş.',
            vergi_no='1234567890',
            vergi_dairesi='Kadıköy',
            telefon='02121234567',
            email='info@demo.com',
            aktif=True,
        )
        db.session.add(sirket)
        db.session.flush()
        print(f"✓ Şirket oluşturuldu → {sirket.unvan}")

        # Varsayılan depo
        depo = Depo(
            sirket_id=sirket.id, kod='MRKZ',
            ad='Merkez Depo', varsayilan=True, aktif=True,
        )
        db.session.add(depo)
        print(f"✓ Depo oluşturuldu → {depo.ad}")
    else:
        sirket = Sirket.query.first()
        print(f"→ Şirket zaten var ({sirket.unvan}), atlanıyor")

    # ── Birim grupları + birimler ────────────────────────────────────
    if not BirimGrubu.query.first():
        gruplar_birimler = [
            ('Adet',  [('ADET','Adet',1,True), ('KOL','Koli',12,False), ('KTU','Kutu',6,False)]),
            ('Ağırlık',[('KG','Kilogram',1,True), ('GR','Gram',0.001,False), ('TON','Ton',1000,False)]),
            ('Hacim', [('LT','Litre',1,True), ('ML','Mililitre',0.001,False)]),
            ('Uzunluk',[('MT','Metre',1,True), ('CM','Santimetre',0.01,False), ('MM','Milimetre',0.001,False)]),
        ]
        for grup_ad, birimler in gruplar_birimler:
            grup = BirimGrubu(ad=grup_ad, aktif=True)
            db.session.add(grup)
            db.session.flush()
            for kod, ad, katsayi, taban in birimler:
                db.session.add(Birim(
                    grup_id=grup.id, kod=kod, ad=ad,
                    katsayi=katsayi, taban_mi=taban, aktif=True,
                ))
        print("✓ Birim grupları ve birimler oluşturuldu")
    else:
        print("→ Birimler zaten var, atlanıyor")

    # ── Numara serileri ──────────────────────────────────────────────
    from datetime import date
    yil = date.today().year
    seriler = [
        ('FATURA',   'SATIS', 'FAT', 6),
        ('FATURA',   'ALIS',  'ALF', 6),
        ('SIPARIS',  'SATIS', 'SIP', 6),
        ('SIPARIS',  'ALIS',  'ALS', 6),
        ('IRSALIYE', 'SATIS', 'IRS', 6),
        ('IRSALIYE', 'ALIS',  'ALI', 6),
        ('TALEP',    'SATIS', 'TLB', 6),
        ('URETIM',   'SATIS', 'URE', 6),
        ('STOK_FIS', 'SATIS', 'SFS', 6),
        ('KASA',     'SATIS', 'KSA', 6),
        ('BANKA',    'SATIS', 'BNK', 6),
    ]
    for belge_tip, cari_tip, prefix, basamak in seriler:
        mevcut = NumaraSira.query.filter_by(
            sirket_id=sirket.id, belge_tip=belge_tip, cari_tip=cari_tip, yil=yil
        ).first()
        if not mevcut:
            db.session.add(NumaraSira(
                sirket_id=sirket.id, belge_tip=belge_tip, cari_tip=cari_tip,
                prefix=prefix, yil=yil, son_sayi=0, basamak=basamak,
            ))
    print(f"✓ {len(seriler)} adet numara serisi oluşturuldu ({yil})")

    # ── Commit ──────────────────────────────────────────────────────
    db.session.commit()
    print("\n✅ Seed tamamlandı. Giriş: admin@openpyerp.local / Admin1234!")
    print("⚠  Production'da admin şifresini hemen değiştirin!")
