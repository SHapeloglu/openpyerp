"""İlk kurulum — tüm OpenPyERP tabloları

Revision ID: 0001_ilk_kurulum
Revises: —
Create Date: 2026-06-21

Bu migration `alembic revision --autogenerate` ile üretilmiş gibi
yazılmıştır — el ile de çalıştırılabilir.

Tablo oluşturma sırası bağımlılık zincirine göre düzenlenmiştir:
    1. Bağımsız tablolar (kullanici, birim_grubu)
    2. Sirket (kullanici'ya FK)
    3. Birim, Depo, NumaraSira, DonemKilidi (sirket'e FK)
    4. Cari, StokKarti (sirket + birim'e FK)
    5. Belge, Finans, Üretim, Personel (üstteki hepsine FK)
"""
from alembic import op
import sqlalchemy as sa

revision = '0001_ilk_kurulum'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:

    # ── 1. kullanici ────────────────────────────────────────────────────
    op.create_table('kullanici',
        sa.Column('id',        sa.Integer(),     primary_key=True, autoincrement=True),
        sa.Column('ad_soyad',  sa.String(100),   nullable=False),
        sa.Column('email',     sa.String(150),   nullable=False),
        sa.Column('sifre_hash',sa.String(255),   nullable=False),
        sa.Column('rol',       sa.String(20),    nullable=False, server_default='KULLANICI'),
        sa.Column('aktif',     sa.Boolean(),     nullable=False, server_default='1'),
        sa.Column('olusturma_tarihi',  sa.DateTime()),
        sa.Column('guncelleme_tarihi', sa.DateTime()),
        sa.UniqueConstraint('email', name='uq_kullanici_email'),
    )

    # ── 2. sirket ───────────────────────────────────────────────────────
    op.create_table('sirket',
        sa.Column('id',            sa.Integer(),   primary_key=True, autoincrement=True),
        sa.Column('kod',           sa.String(20),  nullable=False),
        sa.Column('unvan',         sa.String(200), nullable=False),
        sa.Column('vergi_no',      sa.String(20)),
        sa.Column('vergi_dairesi', sa.String(100)),
        sa.Column('telefon',       sa.String(20)),
        sa.Column('email',         sa.String(100)),
        sa.Column('adres',         sa.Text()),
        sa.Column('logo_url',      sa.String(300)),
        sa.Column('aktif',         sa.Boolean(),   nullable=False, server_default='1'),
        sa.Column('olusturma_tarihi',  sa.DateTime()),
        sa.Column('guncelleme_tarihi', sa.DateTime()),
    )

    # ── 3. birim_grubu + birim + birim_donusum ──────────────────────────
    op.create_table('birim_grubu',
        sa.Column('id',    sa.Integer(),  primary_key=True, autoincrement=True),
        sa.Column('ad',    sa.String(50), nullable=False),
        sa.Column('aciklama', sa.String(200)),
        sa.Column('aktif', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('olusturma_tarihi',  sa.DateTime()),
        sa.Column('guncelleme_tarihi', sa.DateTime()),
        sa.UniqueConstraint('ad', name='uq_birim_grubu_ad'),
    )
    op.create_table('birim',
        sa.Column('id',       sa.Integer(),      primary_key=True, autoincrement=True),
        sa.Column('grup_id',  sa.Integer(),      nullable=False),
        sa.Column('kod',      sa.String(20),     nullable=False),
        sa.Column('ad',       sa.String(50),     nullable=False),
        sa.Column('katsayi',  sa.Numeric(20,10), nullable=False, server_default='1'),
        sa.Column('taban_mi', sa.Boolean(),      nullable=False, server_default='0'),
        sa.Column('aktif',    sa.Boolean(),      nullable=False, server_default='1'),
        sa.Column('olusturma_tarihi',  sa.DateTime()),
        sa.Column('guncelleme_tarihi', sa.DateTime()),
        sa.ForeignKeyConstraint(['grup_id'], ['birim_grubu.id'], ondelete='RESTRICT'),
        sa.UniqueConstraint('kod', name='uq_birim_kod'),
    )
    op.create_index('ix_birim_grup', 'birim', ['grup_id'])
    op.create_table('birim_donusum',
        sa.Column('id',              sa.Integer(),      primary_key=True, autoincrement=True),
        sa.Column('kaynak_birim_id', sa.Integer(),      nullable=False),
        sa.Column('hedef_birim_id',  sa.Integer(),      nullable=False),
        sa.Column('carpan',          sa.Numeric(20,10), nullable=False),
        sa.Column('aciklama',        sa.String(200)),
        sa.Column('aktif',           sa.Boolean(),      nullable=False, server_default='1'),
        sa.Column('olusturma_tarihi',  sa.DateTime()),
        sa.Column('guncelleme_tarihi', sa.DateTime()),
        sa.ForeignKeyConstraint(['kaynak_birim_id'], ['birim.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['hedef_birim_id'],  ['birim.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('kaynak_birim_id', 'hedef_birim_id', name='uq_donusum_kh'),
    )
    op.create_index('ix_donusum_kaynak', 'birim_donusum', ['kaynak_birim_id'])

    # ── 4. depo + numara_sira + donem_kilidi ────────────────────────────
    op.create_table('depo',
        sa.Column('id',         sa.Integer(),  primary_key=True, autoincrement=True),
        sa.Column('sirket_id',  sa.Integer(),  nullable=False),
        sa.Column('kod',        sa.String(20), nullable=False),
        sa.Column('ad',         sa.String(100),nullable=False),
        sa.Column('adres',      sa.Text()),
        sa.Column('varsayilan', sa.Boolean(),  nullable=False, server_default='0'),
        sa.Column('aktif',      sa.Boolean(),  nullable=False, server_default='1'),
        sa.Column('olusturma_tarihi',  sa.DateTime()),
        sa.Column('guncelleme_tarihi', sa.DateTime()),
        sa.ForeignKeyConstraint(['sirket_id'], ['sirket.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('sirket_id', 'kod', name='uq_depo_sirket_kod'),
    )
    op.create_table('numara_sira',
        sa.Column('id',         sa.Integer(),    primary_key=True, autoincrement=True),
        sa.Column('sirket_id',  sa.Integer(),    nullable=False),
        sa.Column('belge_tip',  sa.String(30),   nullable=False),
        sa.Column('cari_tip',   sa.String(10),   nullable=False, server_default='SATIS'),
        sa.Column('prefix',     sa.String(10),   nullable=False),
        sa.Column('yil',        sa.SmallInteger(),nullable=False),
        sa.Column('son_sayi',   sa.Integer(),    nullable=False, server_default='0'),
        sa.Column('basamak',    sa.SmallInteger(),server_default='6'),
        sa.Column('olusturma_tarihi',  sa.DateTime()),
        sa.Column('guncelleme_tarihi', sa.DateTime()),
        sa.ForeignKeyConstraint(['sirket_id'], ['sirket.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('sirket_id','belge_tip','cari_tip','yil', name='uq_ns_sirket_tip_yil'),
    )
    op.create_table('donem_kilidi',
        sa.Column('id',           sa.Integer(),    primary_key=True, autoincrement=True),
        sa.Column('sirket_id',    sa.Integer(),    nullable=False),
        sa.Column('yil',          sa.Integer(),    nullable=False),
        sa.Column('ay',           sa.Integer()),
        sa.Column('kilitli',      sa.Boolean(),    nullable=False, server_default='1'),
        sa.Column('aciklama',     sa.String(300)),
        sa.Column('kilitleyen_id',sa.Integer()),
        sa.Column('olusturma_tarihi', sa.DateTime()),
        sa.ForeignKeyConstraint(['sirket_id'],     ['sirket.id'],   ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['kilitleyen_id'], ['kullanici.id'],ondelete='SET NULL'),
        sa.UniqueConstraint('sirket_id','yil','ay', name='uq_donem_kilidi'),
    )
    op.create_index('ix_dk_sirket_donem', 'donem_kilidi', ['sirket_id','yil','ay'])

    # ── 5. cari + cari_adres + cari_iletisim ────────────────────────────
    op.create_table('cari',
        sa.Column('id',            sa.Integer(),  primary_key=True, autoincrement=True),
        sa.Column('sirket_id',     sa.Integer()),
        sa.Column('kod',           sa.String(20), nullable=False),
        sa.Column('unvan',         sa.String(200),nullable=False),
        sa.Column('tip',           sa.String(20), nullable=False),
        sa.Column('vergi_no',      sa.String(20)),
        sa.Column('vergi_dairesi', sa.String(100)),
        sa.Column('telefon',       sa.String(20)),
        sa.Column('email',         sa.String(100)),
        sa.Column('adres',         sa.Text()),
        sa.Column('sehir',         sa.String(50)),
        sa.Column('website',       sa.String(200)),
        sa.Column('aktif',         sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('olusturma_tarihi',  sa.DateTime()),
        sa.Column('guncelleme_tarihi', sa.DateTime()),
        sa.ForeignKeyConstraint(['sirket_id'], ['sirket.id'], ondelete='RESTRICT'),
    )
    op.create_index('ix_cari_sirket_aktif', 'cari', ['sirket_id','aktif'])
    op.create_index('ix_cari_sirket_tip',   'cari', ['sirket_id','tip'])
    op.create_index('ix_cari_sirket_kod',   'cari', ['sirket_id','kod'])

    op.create_table('cari_adres',
        sa.Column('id',          sa.Integer(),  primary_key=True, autoincrement=True),
        sa.Column('cari_id',     sa.Integer(),  nullable=False),
        sa.Column('tip',         sa.String(20), nullable=False, server_default='MERKEZ'),
        sa.Column('baslik',      sa.String(100)),
        sa.Column('il_id',       sa.Integer()),
        sa.Column('ilce_id',     sa.Integer()),
        sa.Column('mahalle_id',  sa.Integer()),
        sa.Column('adres_metni', sa.Text()),
        sa.Column('posta_kodu',  sa.String(10)),
        sa.Column('varsayilan',  sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('aktif',       sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('olusturma_tarihi',  sa.DateTime()),
        sa.Column('guncelleme_tarihi', sa.DateTime()),
        sa.ForeignKeyConstraint(['cari_id'], ['cari.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_ca_cari', 'cari_adres', ['cari_id'])

    op.create_table('cari_iletisim',
        sa.Column('id',         sa.Integer(),  primary_key=True, autoincrement=True),
        sa.Column('cari_id',    sa.Integer(),  nullable=False),
        sa.Column('tip',        sa.String(20), nullable=False),
        sa.Column('deger',      sa.String(200),nullable=False),
        sa.Column('aciklama',   sa.String(100)),
        sa.Column('varsayilan', sa.Boolean(),  nullable=False, server_default='0'),
        sa.Column('aktif',      sa.Boolean(),  nullable=False, server_default='1'),
        sa.Column('olusturma_tarihi',  sa.DateTime()),
        sa.Column('guncelleme_tarihi', sa.DateTime()),
        sa.ForeignKeyConstraint(['cari_id'], ['cari.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_ci_cari', 'cari_iletisim', ['cari_id'])

    op.create_table('cari_hareket',
        sa.Column('id',            sa.Integer(),    primary_key=True, autoincrement=True),
        sa.Column('cari_id',       sa.Integer(),    nullable=False),
        sa.Column('tarih',         sa.Date(),       nullable=False),
        sa.Column('belge_no',      sa.String(50)),
        sa.Column('aciklama',      sa.String(500)),
        sa.Column('hareket_tipi',  sa.String(10),   nullable=False),
        sa.Column('tutar',         sa.Numeric(15,2),nullable=False),
        sa.Column('kaynak_tip',    sa.String(20)),
        sa.Column('kaynak_id',     sa.Integer()),
        sa.Column('olusturma_tarihi',  sa.DateTime()),
        sa.Column('guncelleme_tarihi', sa.DateTime()),
        sa.ForeignKeyConstraint(['cari_id'], ['cari.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_ch_cari_tarih', 'cari_hareket', ['cari_id','tarih'])

    # ── 6. stok_karti + stok_hareket ────────────────────────────────────
    op.create_table('stok_karti',
        sa.Column('id',            sa.Integer(),    primary_key=True, autoincrement=True),
        sa.Column('sirket_id',     sa.Integer()),
        sa.Column('kod',           sa.String(50),   nullable=False),
        sa.Column('ad',            sa.String(200),  nullable=False),
        sa.Column('tip',           sa.String(20),   nullable=False),
        sa.Column('kullanim_tipi', sa.String(20),   nullable=False, server_default='HER_IKISI'),
        sa.Column('birim_id',      sa.Integer(),    nullable=False),
        sa.Column('kdv_orani',     sa.Numeric(5,2), server_default='20.00'),
        sa.Column('satis_fiyati',  sa.Numeric(15,4),server_default='0'),
        sa.Column('alis_fiyati',   sa.Numeric(15,4),server_default='0'),
        sa.Column('aciklama',      sa.Text()),
        sa.Column('barkod_ean8',   sa.String(8)),
        sa.Column('barkod_ean13',  sa.String(13)),
        sa.Column('min_stok',      sa.Numeric(15,4)),
        sa.Column('aktif',         sa.Boolean(),    nullable=False, server_default='1'),
        sa.Column('olusturma_tarihi',  sa.DateTime()),
        sa.Column('guncelleme_tarihi', sa.DateTime()),
        sa.ForeignKeyConstraint(['sirket_id'], ['sirket.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['birim_id'],  ['birim.id'],  ondelete='RESTRICT'),
    )
    op.create_index('ix_stok_sirket_aktif', 'stok_karti', ['sirket_id','aktif'])
    op.create_index('ix_stok_kod',          'stok_karti', ['sirket_id','kod'])
    op.create_index('ix_stok_barkod',       'stok_karti', ['barkod_ean13','barkod_ean8'])

    op.create_table('stok_hareket',
        sa.Column('id',              sa.Integer(),    primary_key=True, autoincrement=True),
        sa.Column('stok_id',         sa.Integer(),    nullable=False),
        sa.Column('tarih',           sa.Date(),       nullable=False),
        sa.Column('belge_no',        sa.String(50)),
        sa.Column('hareket_tipi',    sa.String(10),   nullable=False),
        sa.Column('birim_id',        sa.Integer()),
        sa.Column('miktar',          sa.Numeric(15,4),nullable=False),
        sa.Column('cevrilen_miktar', sa.Numeric(15,4)),
        sa.Column('birim_fiyat',     sa.Numeric(15,4)),
        sa.Column('aciklama',        sa.String(500)),
        sa.Column('depo_id',         sa.Integer()),
        sa.Column('olusturma_tarihi',  sa.DateTime()),
        sa.Column('guncelleme_tarihi', sa.DateTime()),
        sa.ForeignKeyConstraint(['stok_id'],  ['stok_karti.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['birim_id'], ['birim.id'],      ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['depo_id'],  ['depo.id'],       ondelete='SET NULL'),
    )
    op.create_index('ix_sh_stok_tarih', 'stok_hareket', ['stok_id','tarih'])
    op.create_index('ix_sh_depo',       'stok_hareket', ['depo_id'])
    op.create_index('ix_sh_tip',        'stok_hareket', ['hareket_tipi'])

    # ── 7. belge_baslik + belge_satir ───────────────────────────────────
    op.create_table('belge_baslik',
        sa.Column('id',              sa.Integer(),    primary_key=True, autoincrement=True),
        sa.Column('belge_tip',       sa.String(20),   nullable=False),
        sa.Column('belge_no',        sa.String(50),   nullable=False),
        sa.Column('tarih',           sa.Date(),       nullable=False),
        sa.Column('vade_tarihi',     sa.Date()),
        sa.Column('cari_id',         sa.Integer()),
        sa.Column('cari_tip',        sa.String(10),   nullable=False, server_default='SATIS'),
        sa.Column('aciklama',        sa.Text()),
        sa.Column('durum',           sa.String(20),   nullable=False, server_default='ACIK'),
        sa.Column('kaynak_belge_id', sa.Integer()),
        sa.Column('toplam_kdvsiz',   sa.Numeric(15,2),server_default='0'),
        sa.Column('toplam_kdv',      sa.Numeric(15,2),server_default='0'),
        sa.Column('toplam_kdvli',    sa.Numeric(15,2),server_default='0'),
        sa.Column('sirket_id',       sa.Integer()),
        sa.Column('depo_id',         sa.Integer()),
        sa.Column('evrak_no',        sa.String(50)),
        sa.Column('sevk_durumu',     sa.String(30),   server_default='SEVK_EDILMEDI'),
        sa.Column('olusturma_tarihi',  sa.DateTime()),
        sa.Column('guncelleme_tarihi', sa.DateTime()),
        sa.ForeignKeyConstraint(['cari_id'],         ['cari.id'],         ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['kaynak_belge_id'], ['belge_baslik.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['sirket_id'],       ['sirket.id'],       ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['depo_id'],         ['depo.id'],         ondelete='SET NULL'),
        sa.UniqueConstraint('belge_no', name='uq_belge_no'),
    )
    op.create_index('ix_bb_tip_ctip_tarih', 'belge_baslik', ['belge_tip','cari_tip','tarih'])
    op.create_index('ix_bb_cari',           'belge_baslik', ['cari_id'])
    op.create_index('ix_bb_sirket_tarih',   'belge_baslik', ['sirket_id','tarih'])
    op.create_index('ix_bb_sirket_durum',   'belge_baslik', ['sirket_id','durum'])
    op.create_index('ix_bb_vade',           'belge_baslik', ['vade_tarihi'])

    op.create_table('belge_satir',
        sa.Column('id',              sa.Integer(),    primary_key=True, autoincrement=True),
        sa.Column('baslik_id',       sa.Integer(),    nullable=False),
        sa.Column('sira_no',         sa.SmallInteger(),nullable=False),
        sa.Column('stok_id',         sa.Integer()),
        sa.Column('aciklama',        sa.String(500)),
        sa.Column('miktar',          sa.Numeric(15,4),nullable=False, server_default='1'),
        sa.Column('birim_id',        sa.Integer()),
        sa.Column('donusum_carpan',  sa.Numeric(20,6),server_default='1'),
        sa.Column('cevrilen_miktar', sa.Numeric(15,4)),
        sa.Column('birim_fiyat',     sa.Numeric(15,4),nullable=False, server_default='0'),
        sa.Column('iskonto_oran',    sa.Numeric(5,2), server_default='0'),
        sa.Column('kdv_orani',       sa.Numeric(5,2), server_default='20'),
        sa.Column('kdvsiz_tutar',    sa.Numeric(15,2),server_default='0'),
        sa.Column('kdv_tutar',       sa.Numeric(15,2),server_default='0'),
        sa.Column('kdvli_tutar',     sa.Numeric(15,2),server_default='0'),
        sa.Column('olusturma_tarihi',  sa.DateTime()),
        sa.Column('guncelleme_tarihi', sa.DateTime()),
        sa.ForeignKeyConstraint(['baslik_id'], ['belge_baslik.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['stok_id'],   ['stok_karti.id'],   ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['birim_id'],  ['birim.id'],        ondelete='RESTRICT'),
    )
    op.create_index('ix_bs_baslik', 'belge_satir', ['baslik_id'])
    op.create_index('ix_bs_stok',   'belge_satir', ['stok_id'])

    # ── 8. finans (kasa + banka + hareketler) ───────────────────────────
    op.create_table('kasa',
        sa.Column('id',           sa.Integer(),  primary_key=True, autoincrement=True),
        sa.Column('sirket_id',    sa.Integer()),
        sa.Column('kod',          sa.String(20), nullable=False),
        sa.Column('ad',           sa.String(100),nullable=False),
        sa.Column('para_birimi',  sa.String(5),  server_default='TRY'),
        sa.Column('aktif',        sa.Boolean(),  nullable=False, server_default='1'),
        sa.Column('olusturma_tarihi',  sa.DateTime()),
        sa.Column('guncelleme_tarihi', sa.DateTime()),
        sa.ForeignKeyConstraint(['sirket_id'], ['sirket.id'], ondelete='CASCADE'),
    )
    op.create_table('kasa_hareket',
        sa.Column('id',           sa.Integer(),    primary_key=True, autoincrement=True),
        sa.Column('kasa_id',      sa.Integer(),    nullable=False),
        sa.Column('tarih',        sa.Date(),       nullable=False),
        sa.Column('belge_no',     sa.String(50)),
        sa.Column('aciklama',     sa.String(500)),
        sa.Column('hareket_tipi', sa.String(10),   nullable=False),
        sa.Column('tutar',        sa.Numeric(15,2),nullable=False),
        sa.Column('cari_id',      sa.Integer()),
        sa.Column('kaynak_tip',   sa.String(20)),
        sa.Column('kaynak_id',    sa.Integer()),
        sa.Column('olusturma_tarihi',  sa.DateTime()),
        sa.Column('guncelleme_tarihi', sa.DateTime()),
        sa.ForeignKeyConstraint(['kasa_id'], ['kasa.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['cari_id'], ['cari.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_kh_kasa_tarih', 'kasa_hareket', ['kasa_id','tarih'])

    op.create_table('banka',
        sa.Column('id',           sa.Integer(),  primary_key=True, autoincrement=True),
        sa.Column('sirket_id',    sa.Integer()),
        sa.Column('banka_adi',    sa.String(100),nullable=False),
        sa.Column('sube_adi',     sa.String(100)),
        sa.Column('iban',         sa.String(35)),
        sa.Column('hesap_no',     sa.String(50)),
        sa.Column('para_birimi',  sa.String(5),  server_default='TRY'),
        sa.Column('aktif',        sa.Boolean(),  nullable=False, server_default='1'),
        sa.Column('olusturma_tarihi',  sa.DateTime()),
        sa.Column('guncelleme_tarihi', sa.DateTime()),
        sa.ForeignKeyConstraint(['sirket_id'], ['sirket.id'], ondelete='CASCADE'),
    )
    op.create_table('banka_hareket',
        sa.Column('id',           sa.Integer(),    primary_key=True, autoincrement=True),
        sa.Column('banka_id',     sa.Integer(),    nullable=False),
        sa.Column('tarih',        sa.Date(),       nullable=False),
        sa.Column('belge_no',     sa.String(50)),
        sa.Column('aciklama',     sa.String(500)),
        sa.Column('hareket_tipi', sa.String(10),   nullable=False),
        sa.Column('tutar',        sa.Numeric(15,2),nullable=False),
        sa.Column('cari_id',      sa.Integer()),
        sa.Column('kaynak_tip',   sa.String(20)),
        sa.Column('kaynak_id',    sa.Integer()),
        sa.Column('olusturma_tarihi',  sa.DateTime()),
        sa.Column('guncelleme_tarihi', sa.DateTime()),
        sa.ForeignKeyConstraint(['banka_id'], ['banka.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['cari_id'],  ['cari.id'],  ondelete='SET NULL'),
    )
    op.create_index('ix_bh_banka_tarih', 'banka_hareket', ['banka_id','tarih'])

    # ── 9. uretim ───────────────────────────────────────────────────────
    op.create_table('uretim_fis',
        sa.Column('id',                sa.Integer(),    primary_key=True, autoincrement=True),
        sa.Column('sirket_id',         sa.Integer()),
        sa.Column('fis_no',            sa.String(50),   nullable=False),
        sa.Column('tarih',             sa.Date(),       nullable=False),
        sa.Column('mamul_stok_id',     sa.Integer(),    nullable=False),
        sa.Column('uretilecek_miktar', sa.Numeric(15,4),nullable=False),
        sa.Column('uretilen_miktar',   sa.Numeric(15,4),server_default='0'),
        sa.Column('depo_id',           sa.Integer()),
        sa.Column('durum',             sa.String(20),   nullable=False, server_default='TASLAK'),
        sa.Column('aciklama',          sa.Text()),
        sa.Column('olusturma_tarihi',  sa.DateTime()),
        sa.Column('guncelleme_tarihi', sa.DateTime()),
        sa.ForeignKeyConstraint(['sirket_id'],     ['sirket.id'],    ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['mamul_stok_id'], ['stok_karti.id'],ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['depo_id'],       ['depo.id'],      ondelete='SET NULL'),
        sa.UniqueConstraint('fis_no', name='uq_uretim_fis_no'),
    )
    op.create_index('ix_uf_sirket_tarih', 'uretim_fis', ['sirket_id','tarih'])
    op.create_table('uretim_fis_satir',
        sa.Column('id',              sa.Integer(),    primary_key=True, autoincrement=True),
        sa.Column('fis_id',          sa.Integer(),    nullable=False),
        sa.Column('stok_id',         sa.Integer(),    nullable=False),
        sa.Column('miktar',          sa.Numeric(15,4),nullable=False),
        sa.Column('birim_id',        sa.Integer()),
        sa.Column('cevrilen_miktar', sa.Numeric(15,4)),
        sa.ForeignKeyConstraint(['fis_id'],   ['uretim_fis.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['stok_id'],  ['stok_karti.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['birim_id'], ['birim.id'],      ondelete='RESTRICT'),
    )

    # ── 10. personel ────────────────────────────────────────────────────
    op.create_table('personel',
        sa.Column('id',          sa.Integer(),  primary_key=True, autoincrement=True),
        sa.Column('sirket_id',   sa.Integer()),
        sa.Column('sicil_no',    sa.String(30), nullable=False),
        sa.Column('ad',          sa.String(50), nullable=False),
        sa.Column('soyad',       sa.String(50), nullable=False),
        sa.Column('tc_kimlik',   sa.String(11)),
        sa.Column('ise_giris',   sa.Date(),     nullable=False),
        sa.Column('isten_cikis', sa.Date()),
        sa.Column('cari_id',     sa.Integer()),
        sa.Column('aktif',       sa.Boolean(),  nullable=False, server_default='1'),
        sa.Column('olusturma_tarihi',  sa.DateTime()),
        sa.Column('guncelleme_tarihi', sa.DateTime()),
        sa.ForeignKeyConstraint(['sirket_id'], ['sirket.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['cari_id'],   ['cari.id'],   ondelete='SET NULL'),
        sa.UniqueConstraint('sirket_id','sicil_no', name='uq_personel_sirket_sicil'),
    )
    op.create_index('ix_personel_sirket_aktif', 'personel', ['sirket_id','aktif'])

    op.create_table('personel_izin',
        sa.Column('id',           sa.Integer(),  primary_key=True, autoincrement=True),
        sa.Column('personel_id',  sa.Integer(),  nullable=False),
        sa.Column('izin_tipi',    sa.String(30), nullable=False),
        sa.Column('baslangic',    sa.Date(),     nullable=False),
        sa.Column('bitis',        sa.Date(),     nullable=False),
        sa.Column('gun_sayisi',   sa.Integer(),  nullable=False),
        sa.Column('durum',        sa.String(20), server_default='BEKLEMEDE'),
        sa.Column('aciklama',     sa.Text()),
        sa.Column('onaylayan_id', sa.Integer()),
        sa.Column('olusturma_tarihi',  sa.DateTime()),
        sa.Column('guncelleme_tarihi', sa.DateTime()),
        sa.ForeignKeyConstraint(['personel_id'],  ['personel.id'],  ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['onaylayan_id'], ['kullanici.id'], ondelete='SET NULL'),
    )
    op.create_table('puantaj',
        sa.Column('id',             sa.Integer(),    primary_key=True, autoincrement=True),
        sa.Column('personel_id',    sa.Integer(),    nullable=False),
        sa.Column('yil',            sa.SmallInteger(),nullable=False),
        sa.Column('ay',             sa.SmallInteger(),nullable=False),
        sa.Column('calisilan_gun',  sa.SmallInteger(),server_default='0'),
        sa.Column('fazla_mesai',    sa.Numeric(5,2), server_default='0'),
        sa.Column('durum',          sa.String(20),   server_default='TASLAK'),
        sa.Column('olusturma_tarihi',  sa.DateTime()),
        sa.Column('guncelleme_tarihi', sa.DateTime()),
        sa.ForeignKeyConstraint(['personel_id'], ['personel.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('personel_id','yil','ay', name='uq_puantaj_personel_donem'),
    )


def downgrade() -> None:
    """Tüm tabloları ters bağımlılık sırasında siler."""
    tablolar = [
        'puantaj', 'personel_izin', 'personel',
        'uretim_fis_satir', 'uretim_fis',
        'banka_hareket', 'banka', 'kasa_hareket', 'kasa',
        'belge_satir', 'belge_baslik',
        'stok_hareket', 'stok_karti',
        'cari_hareket', 'cari_iletisim', 'cari_adres', 'cari',
        'donem_kilidi', 'numara_sira', 'depo',
        'birim_donusum', 'birim', 'birim_grubu',
        'sirket', 'kullanici',
    ]
    for t in tablolar:
        op.drop_table(t)
