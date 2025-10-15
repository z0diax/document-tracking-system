"""add sla alert preferences table

Revision ID: c5f32d2a719b
Revises: b1f9071a56a7
Create Date: 2025-10-15 10:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c5f32d2a719b'
down_revision = 'b1f9071a56a7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'sla_alert_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('category', name='uq_sla_alert_preferences_category'),
    )


def downgrade():
    op.drop_table('sla_alert_preferences')

