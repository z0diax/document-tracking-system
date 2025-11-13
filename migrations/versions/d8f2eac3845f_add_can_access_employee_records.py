"""Add can_access_employee_records column to user table

Revision ID: d8f2eac3845f
Revises: c5f32d2a719b
Create Date: 2025-10-24 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd8f2eac3845f'
down_revision = 'c5f32d2a719b'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'user',
        sa.Column(
            'can_access_employee_records',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('0')
        )
    )


def downgrade():
    op.drop_column('user', 'can_access_employee_records')
