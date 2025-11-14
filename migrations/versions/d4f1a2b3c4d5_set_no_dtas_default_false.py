"""Set no_dtas_flag default to false and reset existing rows

Revision ID: d4f1a2b3c4d5
Revises: c3a5d7e8f912
Create Date: 2025-11-13 17:05:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4f1a2b3c4d5'
down_revision = 'c3a5d7e8f912'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('UPDATE document SET no_dtas_flag = 0')
    op.alter_column(
        'document',
        'no_dtas_flag',
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text('0')
    )


def downgrade():
    op.alter_column(
        'document',
        'no_dtas_flag',
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text('1')
    )
