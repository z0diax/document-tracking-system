"""Add position column to employees and migrate data

Revision ID: 5e7a9c3d2b10
Revises: 43409adfd50a
Create Date: 2025-09-12 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5e7a9c3d2b10'
down_revision = '43409adfd50a'
branch_labels = None
depends_on = None


def upgrade():
    # 1) Add new nullable column first to allow backfill
    op.add_column('employees', sa.Column('position', sa.String(length=50), nullable=True))

    # 2) Data migration: copy existing employment-type values from status into position
    conn = op.get_bind()
    try:
        # Copy any existing status value into position
        conn.execute(sa.text("UPDATE employees SET position = status WHERE position IS NULL"))
    except Exception:
        # Best effort: continue even if table empty or other benign issues
        pass

    # 3) Normalize status to the new domain: Active/Inactive
    #    Set all rows to Active unless already explicitly Inactive
    try:
        conn.execute(sa.text("UPDATE employees SET status = 'Active' WHERE status IS NULL OR status NOT IN ('Active','Inactive')"))
    except Exception:
        pass

    # 4) Enforce NOT NULL on position now that data is backfilled
    op.alter_column('employees', 'position', existing_type=sa.String(length=50), nullable=False)

    # 5) Set server_default for status to 'Active' going forward
    op.alter_column('employees', 'status', existing_type=sa.String(length=50), server_default='Active')


def downgrade():
    # Attempt to restore previous semantics where 'status' held the employment type
    conn = op.get_bind()
    try:
        # Copy back the position value into status (legacy schema expectation)
        conn.execute(sa.text("UPDATE employees SET status = position WHERE position IS NOT NULL"))
    except Exception:
        pass

    # Drop the position column
    op.drop_column('employees', 'position')

    # Remove server_default on status (restore previous definition without default)
    op.alter_column('employees', 'status', existing_type=sa.String(length=50), server_default=None)
