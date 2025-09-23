"""add ewp_records table

Revision ID: 7129e35b3a85
Revises: d1e2f3a4b5c6
Create Date: 2025-09-02 08:11:22.485374

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '7129e35b3a85'
down_revision = 'd1e2f3a4b5c6'
branch_labels = None
depends_on = None


def upgrade():
    # Idempotent creation: only create table / indexes if they don't already exist
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    tables = inspector.get_table_names()
    if 'ewp_records' not in tables:
        op.create_table(
            'ewp_records',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('barcode', sa.String(length=50), nullable=True),
            sa.Column('employee_name', sa.String(length=120), nullable=False),
            sa.Column('office', sa.String(length=100), nullable=False),
            sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
            sa.Column('purpose', sa.Text(), nullable=True),
            sa.Column('remarks', sa.Text(), nullable=True),
            sa.Column('status', sa.String(length=20), server_default='For Computation', nullable=False),
            sa.Column('created_timestamp', sa.DateTime(), nullable=False),
            sa.Column('created_by_user_id', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['created_by_user_id'], ['user.id']),
            sa.PrimaryKeyConstraint('id')
        )

    # Ensure indexes exist
    existing_indexes = []
    try:
        existing_indexes = [ix.get('name') for ix in inspector.get_indexes('ewp_records')]
    except Exception:
        existing_indexes = []

    ix_barcode = op.f('ix_ewp_records_barcode')
    ix_created_by = op.f('ix_ewp_records_created_by_user_id')

    if ix_barcode not in (existing_indexes or []):
        op.create_index(ix_barcode, 'ewp_records', ['barcode'], unique=False)
    if ix_created_by not in (existing_indexes or []):
        op.create_index(ix_created_by, 'ewp_records', ['created_by_user_id'], unique=False)


def downgrade():
    # Idempotent drop: remove indexes if present, then drop table if present
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'ewp_records' in tables:
        existing_indexes = []
        try:
            existing_indexes = [ix.get('name') for ix in inspector.get_indexes('ewp_records')]
        except Exception:
            existing_indexes = []

        ix_barcode = op.f('ix_ewp_records_barcode')
        ix_created_by = op.f('ix_ewp_records_created_by_user_id')

        if ix_barcode in (existing_indexes or []):
            op.drop_index(ix_barcode, table_name='ewp_records')
        if ix_created_by in (existing_indexes or []):
            op.drop_index(ix_created_by, table_name='ewp_records')

        op.drop_table('ewp_records')
