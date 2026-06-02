"""add can_see_rsp_tracker to user

Revision ID: 7c1d4a9e2b35
Revises: 2f4b8d6c1a90
Create Date: 2026-02-11 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7c1d4a9e2b35'
down_revision = '2f4b8d6c1a90'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'user',
        sa.Column('can_see_rsp_tracker', sa.Boolean(), nullable=False, server_default='0')
    )


def downgrade():
    op.drop_column('user', 'can_see_rsp_tracker')
