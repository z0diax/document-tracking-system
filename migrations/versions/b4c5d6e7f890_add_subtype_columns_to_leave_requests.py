"""Add subtype and subtype_detail columns to leave_requests

Revision ID: b4c5d6e7f890
Revises: ade5d4a7ad4a
Create Date: 2025-08-27 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b4c5d6e7f890'
down_revision = 'ade5d4a7ad4a'
branch_labels = None
depends_on = None


def upgrade():
    # Add new nullable columns to store leave subtypes and details
    op.add_column(
        'leave_requests',
        sa.Column('subtype', sa.String(length=100), nullable=True)
    )
    op.add_column(
        'leave_requests',
        sa.Column('subtype_detail', sa.Text(), nullable=True)
    )


def downgrade():
    # Remove the columns on downgrade
    op.drop_column('leave_requests', 'subtype_detail')
    op.drop_column('leave_requests', 'subtype')
