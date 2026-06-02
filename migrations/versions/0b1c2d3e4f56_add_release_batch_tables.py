"""Add release batch tables

Revision ID: 0b1c2d3e4f56
Revises: d4f1a2b3c4d5
Create Date: 2025-12-17 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0b1c2d3e4f56'
down_revision = 'd4f1a2b3c4d5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'release_batch',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('release_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
    )
    op.create_index('ix_release_batch_created_at', 'release_batch', ['created_at'])

    op.create_table(
        'release_batch_document',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('release_batch_id', sa.Integer(), sa.ForeignKey('release_batch.id', ondelete='CASCADE'), nullable=False),
        sa.Column('document_id', sa.Integer(), sa.ForeignKey('document.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_release_batch_document', 'release_batch_document', ['release_batch_id', 'document_id'], unique=True)


def downgrade():
    op.drop_index('ix_release_batch_document', table_name='release_batch_document')
    op.drop_table('release_batch_document')
    op.drop_index('ix_release_batch_created_at', table_name='release_batch')
    op.drop_table('release_batch')
