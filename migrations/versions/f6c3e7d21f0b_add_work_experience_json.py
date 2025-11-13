"""Add work experience json column to employees

Revision ID: f6c3e7d21f0b
Revises: e2b6d4c1a89f
Create Date: 2025-11-13 15:05:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f6c3e7d21f0b'
down_revision = 'e2b6d4c1a89f'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'employees',
        sa.Column('work_experience_json', sa.Text(), nullable=True)
    )


def downgrade():
    op.drop_column('employees', 'work_experience_json')
