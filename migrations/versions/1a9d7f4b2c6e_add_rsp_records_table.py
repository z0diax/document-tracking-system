"""add rsp records table

Revision ID: 1a9d7f4b2c6e
Revises: 0b1c2d3e4f56
Create Date: 2026-02-11 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1a9d7f4b2c6e'
down_revision = '0b1c2d3e4f56'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'rsp_records',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('position', sa.String(length=120), nullable=False),
        sa.Column('office', sa.String(length=100), nullable=False),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('phase_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('phase_started_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by_user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
    )
    op.create_index('ix_rsp_records_created_by_user_id', 'rsp_records', ['created_by_user_id'])
    op.create_index('ix_rsp_records_created_at', 'rsp_records', ['created_at'])
    op.create_index('ix_rsp_records_phase_started_at', 'rsp_records', ['phase_started_at'])


def downgrade():
    op.drop_index('ix_rsp_records_phase_started_at', table_name='rsp_records')
    op.drop_index('ix_rsp_records_created_at', table_name='rsp_records')
    op.drop_index('ix_rsp_records_created_by_user_id', table_name='rsp_records')
    op.drop_table('rsp_records')
