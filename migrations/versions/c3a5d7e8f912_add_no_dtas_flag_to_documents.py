"""Add no_dtas_flag column to documents

Revision ID: c3a5d7e8f912
Revises: b7c9d0e1f234
Create Date: 2025-11-13 16:45:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3a5d7e8f912'
down_revision = 'b7c9d0e1f234'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('document', sa.Column('no_dtas_flag', sa.Boolean(), nullable=False, server_default=sa.text('1')))


def downgrade():
    op.drop_column('document', 'no_dtas_flag')
