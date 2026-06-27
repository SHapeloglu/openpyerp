"""
addons/eticaret/migrations/0001_stok_karti_eticaret_alanlari.py

Alembic migration — StokKarti tablosuna e-ticaret kolonlarını ekler.

Bu dosya, addons/eticaret/extends.py'deki Python tarafı extend'in
veritabanı tarafı karşılığıdır. İkisi birlikte Odoo'nun _inherit +
otomatik ALTER TABLE davranışına karşılık gelir.

Çalıştırma:
    alembic -c addons/eticaret/alembic.ini upgrade head

Geri alma:
    alembic -c addons/eticaret/alembic.ini downgrade -1
"""
from alembic import op
import sqlalchemy as sa

# Alembic metadata
revision = '0001_eticaret'
down_revision = None   # Bu addon'un ilk migration'ı
branch_labels = ('eticaret',)
depends_on = None


def upgrade():
    """StokKarti tablosuna e-ticaret alanlarını ekle."""
    with op.batch_alter_table('stok_karti') as batch_op:
        batch_op.add_column(
            sa.Column('woo_id', sa.Integer(), nullable=True,
                      comment='WooCommerce ürün ID')
        )
        batch_op.add_column(
            sa.Column('trendyol_barkod', sa.String(50), nullable=True,
                      comment='Trendyol platformuna özgü barkod')
        )
        batch_op.add_column(
            sa.Column('eticaret_aktif', sa.Boolean(), nullable=False,
                      server_default=sa.text('0'),
                      comment='E-ticaret platformlarında yayınlanıyor mu?')
        )
        batch_op.create_index('ix_stok_woo_id', ['woo_id'])


def downgrade():
    """E-ticaret alanlarını kaldır (addon devre dışı bırakıldığında)."""
    with op.batch_alter_table('stok_karti') as batch_op:
        batch_op.drop_index('ix_stok_woo_id')
        batch_op.drop_column('eticaret_aktif')
        batch_op.drop_column('trendyol_barkod')
        batch_op.drop_column('woo_id')
