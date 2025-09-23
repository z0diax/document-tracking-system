"""Add time_mode column to leave_date_ranges for per-range time selection

Revision ID: d1e2f3a4b5c6
Revises: c8f9a1b2d3e4
Create Date: 2025-08-28 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd1e2f3a4b5c6'
down_revision = 'c8f9a1b2d3e4'
branch_labels = None
depends_on = None


def upgrade():
    # Add time_mode to leave_date_ranges with default FULL_DAY and non-nullable
    op.add_column(
        'leave_date_ranges',
        sa.Column('time_mode', sa.String(length=20), nullable=False, server_default='FULL_DAY')
    )

    # Optionally, you can drop the server_default after backfill to keep schema clean
    # Note: Some backends (e.g., SQLite) may ignore this alteration
    try:
        with op.get_context().autocommit_block():
            op.execute("UPDATE leave_date_ranges SET time_mode = 'FULL_DAY' WHERE time_mode IS NULL")
        op.alter_column('leave_date_ranges', 'time_mode', server_default=None)
    except Exception:
        # Safe to ignore if backend doesn't support it
        pass


def downgrade():
    # Drop column
    try:
        op.drop_column('leave_date_ranges', 'time_mode')
    except Exception:
        # Some backends may error if constraints exist; ignore for safety
        pass
