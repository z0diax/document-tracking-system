"""Add learning & development json column to employees

Revision ID: b7c9d0e1f234
Revises: a3c1b5d6e7f8
Create Date: 2025-11-13 16:10:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7c9d0e1f234'
down_revision = 'a3c1b5d6e7f8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'employees',
        sa.Column('learning_dev_json', sa.Text(), nullable=True)
    )


def downgrade():
    op.drop_column('employees', 'learning_dev_json')
