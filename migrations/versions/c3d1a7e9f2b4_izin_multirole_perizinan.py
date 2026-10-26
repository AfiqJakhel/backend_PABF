"""izin_multirole_perizinan

Menambah fitur perizinan multi-role secara NON-DESTRUKTIF:
  - tabel baru: sesi_presensi, fasilitator_gedung, izin_dokumen
  - ALTER izin: + jenis, sesi_id, reviewed_at, cancelled_at (+ index komposit)
  - data izin: status 'disetujui' -> 'approved', 'ditolak' -> 'rejected'
  - backfill fasilitator_gedung dari gedung.user_id

Tidak ada kolom/tabel lama yang dihapus. Downgrade membalik seluruh perubahan.

Revision ID: c3d1a7e9f2b4
Revises: b8f9e21a4c5d
Create Date: 2026-10-20 21:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3d1a7e9f2b4'
down_revision = 'b8f9e21a4c5d'
branch_labels = None
depends_on = None


# Representasi tabel ringan untuk operasi data (tanpa string SQL mentah)
_izin_t = sa.table('izin', sa.column('status', sa.String))
_gedung_t = sa.table('gedung', sa.column('id', sa.Integer), sa.column('user_id', sa.Integer))
_fg_t = sa.table(
    'fasilitator_gedung',
    sa.column('fasilitator_id', sa.Integer),
    sa.column('gedung_id', sa.Integer),
)


def upgrade():
    # 1. sesi_presensi
    op.create_table(
        'sesi_presensi',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('kode', sa.String(length=20), nullable=False),
        sa.Column('nama', sa.String(length=50), nullable=False),
        sa.Column('jam_mulai', sa.Time(), nullable=True),
        sa.Column('jam_selesai', sa.Time(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('kode', name='uq_sesi_presensi_kode'),
    )

    # 2. fasilitator_gedung
    op.create_table(
        'fasilitator_gedung',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('fasilitator_id', sa.Integer(), nullable=False),
        sa.Column('gedung_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['fasilitator_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['gedung_id'], ['gedung.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('fasilitator_id', 'gedung_id', name='uq_fasilitator_gedung'),
    )
    op.create_index('ix_fasilitator_gedung_fasilitator_id', 'fasilitator_gedung', ['fasilitator_id'])
    op.create_index('ix_fasilitator_gedung_gedung_id', 'fasilitator_gedung', ['gedung_id'])

    # Backfill dari relasi lama gedung.user_id (1 fasil -> 1 gedung)
    op.execute(
        _fg_t.insert().from_select(
            ['fasilitator_id', 'gedung_id'],
            sa.select(_gedung_t.c.user_id, _gedung_t.c.id).where(_gedung_t.c.user_id.isnot(None)),
        )
    )

    # 3. ALTER izin (tambah kolom saja)
    with op.batch_alter_table('izin', schema=None) as batch_op:
        batch_op.add_column(sa.Column('jenis', sa.String(length=10), server_default='full', nullable=False))
        batch_op.add_column(sa.Column('sesi_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('reviewed_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('cancelled_at', sa.DateTime(), nullable=True))
        batch_op.create_foreign_key(
            'fk_izin_sesi_id', 'sesi_presensi', ['sesi_id'], ['id'], ondelete='RESTRICT'
        )
        batch_op.create_index('ix_izin_user_status', ['user_id', 'status'], unique=False)
        batch_op.create_index('ix_izin_status_mulai', ['status', 'tanggal_mulai'], unique=False)

    # 4. Normalisasi vocabulary status lama
    op.execute(_izin_t.update().where(_izin_t.c.status == 'disetujui').values(status='approved'))
    op.execute(_izin_t.update().where(_izin_t.c.status == 'ditolak').values(status='rejected'))

    # 5. izin_dokumen
    op.create_table(
        'izin_dokumen',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('izin_id', sa.Integer(), nullable=False),
        sa.Column('stored_name', sa.String(length=64), nullable=False),
        sa.Column('original_name', sa.String(length=255), nullable=True),
        sa.Column('mime_type', sa.String(length=50), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['izin_id'], ['izin.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stored_name', name='uq_izin_dokumen_stored_name'),
    )
    op.create_index('ix_izin_dokumen_izin_id', 'izin_dokumen', ['izin_id'])


def downgrade():
    op.drop_index('ix_izin_dokumen_izin_id', table_name='izin_dokumen')
    op.drop_table('izin_dokumen')

    # Kembalikan vocabulary lama. 'cancelled' tidak punya padanan lama -> tetap.
    op.execute(_izin_t.update().where(_izin_t.c.status == 'approved').values(status='disetujui'))
    op.execute(_izin_t.update().where(_izin_t.c.status == 'rejected').values(status='ditolak'))

    with op.batch_alter_table('izin', schema=None) as batch_op:
        batch_op.drop_index('ix_izin_status_mulai')
        batch_op.drop_index('ix_izin_user_status')
        batch_op.drop_constraint('fk_izin_sesi_id', type_='foreignkey')
        batch_op.drop_column('cancelled_at')
        batch_op.drop_column('reviewed_at')
        batch_op.drop_column('sesi_id')
        batch_op.drop_column('jenis')

    op.drop_index('ix_fasilitator_gedung_gedung_id', table_name='fasilitator_gedung')
    op.drop_index('ix_fasilitator_gedung_fasilitator_id', table_name='fasilitator_gedung')
    op.drop_table('fasilitator_gedung')
    op.drop_table('sesi_presensi')
