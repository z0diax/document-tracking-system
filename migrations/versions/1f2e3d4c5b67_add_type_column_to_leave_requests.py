"""Add type column to leave_requests

Revision ID: 1f2e3d4c5b67
Revises: 9b1d2a3c4e56
Create Date: 2025-08-18 00:30:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1f2e3d4c5b67'
down_revision = '9b1d2a3c4e56'
branch_labels = None
depends_on = None


def upgrade():
    # Add 'type' column with server_default to satisfy NOT NULL constraint for existing rows
    op.add_column(
        'leave_requests',
        sa.Column('type', sa.String(length=50), nullable=False, server_default='Others')
    )
    # If you want to drop the server default after backfilling existing rows, you can uncomment below
    # Note: Some backends (like SQLite) may ignore/skip this alteration
    # op.alter_column('leave_requests', 'type', server_default=None)


def downgrade():
    op.drop_column('leave_requests', 'type')
