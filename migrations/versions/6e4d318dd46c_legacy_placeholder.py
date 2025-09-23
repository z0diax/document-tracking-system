"""Legacy placeholder to bridge unknown revision in existing database

Revision ID: 6e4d318dd46c
Revises: 
Create Date: 2025-08-18 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '6e4d318dd46c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # No-op placeholder: this revision intentionally does not modify schema
    pass


def downgrade():
    # No-op placeholder
    pass
