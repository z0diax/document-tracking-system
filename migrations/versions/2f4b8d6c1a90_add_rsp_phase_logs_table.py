"""add rsp phase logs table

Revision ID: 2f4b8d6c1a90
Revises: 1a9d7f4b2c6e
Create Date: 2026-02-11 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2f4b8d6c1a90'
down_revision = '1a9d7f4b2c6e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'rsp_phase_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('rsp_record_id', sa.Integer(), sa.ForeignKey('rsp_records.id', ondelete='CASCADE'), nullable=False),
        sa.Column('phase_number', sa.Integer(), nullable=False),
        sa.Column('phase_name', sa.String(length=220), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_by_user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
    )
    op.create_index('ix_rsp_phase_logs_rsp_record_id', 'rsp_phase_logs', ['rsp_record_id'])
    op.create_index('ix_rsp_phase_logs_completed_by_user_id', 'rsp_phase_logs', ['completed_by_user_id'])
    op.create_index('ix_rsp_phase_logs_completed_at', 'rsp_phase_logs', ['completed_at'])


def downgrade():
    op.drop_index('ix_rsp_phase_logs_completed_at', table_name='rsp_phase_logs')
    op.drop_index('ix_rsp_phase_logs_completed_by_user_id', table_name='rsp_phase_logs')
    op.drop_index('ix_rsp_phase_logs_rsp_record_id', table_name='rsp_phase_logs')
    op.drop_table('rsp_phase_logs')
