"""Add can_access_leave column to user table

Revision ID: 3c5f1a2b4d78
Revises: 1f2e3d4c5b67
Create Date: 2025-08-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3c5f1a2b4d78'
down_revision = '1f2e3d4c5b67'
branch_labels = None
depends_on = None


def upgrade():
    # Add can_access_leave with NOT NULL and default 0/False for existing rows.
    op.add_column(
        'user',
        sa.Column(
            'can_access_leave',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('0')
        )
    )

    # Backfill initial access for specified users
    try:
        op.execute("UPDATE user SET can_access_leave = 1 WHERE username IN ('karl','janny','junji')")
    except Exception:
        # If this fails on specific backends, it can be applied manually later.
        pass


def downgrade():
    op.drop_column('user', 'can_access_leave')
