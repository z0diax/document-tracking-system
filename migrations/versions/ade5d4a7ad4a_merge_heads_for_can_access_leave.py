"""merge heads for can_access_leave

Revision ID: ade5d4a7ad4a
Revises: 2a3b4c5d6e78, 3c5f1a2b4d78
Create Date: 2025-08-20 16:41:20.466923

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ade5d4a7ad4a'
down_revision = ('2a3b4c5d6e78', '3c5f1a2b4d78')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
