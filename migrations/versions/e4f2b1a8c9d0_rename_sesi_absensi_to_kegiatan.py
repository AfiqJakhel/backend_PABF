"""rename_sesi_absensi_to_kegiatan

Revision ID: e4f2b1a8c9d0
Revises: c3d1a7e9f2b4
Create Date: 2026-10-23 01:28:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e4f2b1a8c9d0'
down_revision = 'c3d1a7e9f2b4'
branch_labels = None
depends_on = None


def upgrade():
    # Rename tabel sesi_absensi menjadi kegiatan
    op.rename_table('sesi_absensi', 'kegiatan')


def downgrade():
    # Rollback nama tabel kegiatan kembali ke sesi_absensi
    op.rename_table('kegiatan', 'sesi_absensi')
