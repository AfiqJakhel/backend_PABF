"""add_nama_panggilan_to_users

Revision ID: 51eab23934a6
Revises: e4f2b1a8c9d0
Create Date: 2026-10-23 02:20:26.547039

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '51eab23934a6'
down_revision = 'e4f2b1a8c9d0'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('nama_panggilan', sa.String(length=50), nullable=True))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('nama_panggilan')
