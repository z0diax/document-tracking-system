"""Add civil service records JSON column to employees

Revision ID: e2b6d4c1a89f
Revises: d8f2eac3845f
Create Date: 2025-11-13 14:30:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e2b6d4c1a89f'
down_revision = 'd8f2eac3845f'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'employees',
        sa.Column('civil_service_records_json', sa.Text(), nullable=True)
    )


def downgrade():
    op.drop_column('employees', 'civil_service_records_json')
