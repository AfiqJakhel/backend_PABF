"""create_users_table

Revision ID: a25b9ac081f0
Revises: 
Create Date: 2026-09-23 23:08:08.945370

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a25b9ac081f0'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('nim', sa.String(length=20), nullable=False),
        sa.Column('nama', sa.String(length=100), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False, server_default='mahasiswa'),
        sa.Column('kamar', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_nim'), 'users', ['nim'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_users_nim'), table_name='users')
    op.drop_table('users')

