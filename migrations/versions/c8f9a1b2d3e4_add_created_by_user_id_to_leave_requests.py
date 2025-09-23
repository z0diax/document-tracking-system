"""Add created_by_user_id to leave_requests

Revision ID: c8f9a1b2d3e4
Revises: b4c5d6e7f890
Create Date: 2025-01-15 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c8f9a1b2d3e4'
down_revision = 'b4c5d6e7f890'
branch_labels = None
depends_on = None


def upgrade():
    # Add created_by_user_id column to track who created the leave request
    op.add_column(
        'leave_requests',
        sa.Column('created_by_user_id', sa.Integer(), nullable=True)
    )
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_leave_requests_created_by_user_id',
        'leave_requests',
        'user',
        ['created_by_user_id'],
        ['id']
    )
    
    # Add index for performance
    op.create_index(
        'ix_leave_requests_created_by_user_id',
        'leave_requests',
        ['created_by_user_id']
    )


def downgrade():
    # Remove index
    op.drop_index('ix_leave_requests_created_by_user_id', table_name='leave_requests')
    
    # Remove foreign key constraint
    op.drop_constraint('fk_leave_requests_created_by_user_id', 'leave_requests', type_='foreignkey')
    
    # Remove column
    op.drop_column('leave_requests', 'created_by_user_id')
