"""Add leave_requests table

Revision ID: 9b1d2a3c4e56
Revises: 7a76c4709d85
Create Date: 2025-08-18 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9b1d2a3c4e56'
down_revision = '7a76c4709d85'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'leave_requests',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('barcode', sa.String(length=50), nullable=True),
        sa.Column('employee_name', sa.String(length=120), nullable=False),
        sa.Column('office', sa.String(length=100), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('created_timestamp', sa.DateTime(), nullable=False),
        sa.Column('released_timestamp', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='For Computation'),
        sa.Column('remarks', sa.Text(), nullable=True),
    )
    # index on barcode for faster lookup
    op.create_index('idx_leave_barcode', 'leave_requests', ['barcode'], unique=False)


def downgrade():
    op.drop_index('idx_leave_barcode', table_name='leave_requests')
    op.drop_table('leave_requests')
