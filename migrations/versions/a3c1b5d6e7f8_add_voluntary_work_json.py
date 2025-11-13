"""Add voluntary work json column to employees

Revision ID: a3c1b5d6e7f8
Revises: f6c3e7d21f0b
Create Date: 2025-11-13 15:45:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3c1b5d6e7f8'
down_revision = 'f6c3e7d21f0b'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'employees',
        sa.Column('voluntary_work_json', sa.Text(), nullable=True)
    )


def downgrade():
    op.drop_column('employees', 'voluntary_work_json')
