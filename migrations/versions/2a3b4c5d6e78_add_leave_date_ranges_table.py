"""Add leave_date_ranges table for multiple date ranges per leave request

Revision ID: 2a3b4c5d6e78
Revises: 1f2e3d4c5b67
Create Date: 2025-08-19 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import Integer, Date, text

# revision identifiers, used by Alembic.
revision = '2a3b4c5d6e78'
down_revision = '1f2e3d4c5b67'
branch_labels = None
depends_on = None


def upgrade():
    # Create table to hold multiple date ranges per leave request
    op.create_table(
        'leave_date_ranges',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('leave_request_id', sa.Integer(), sa.ForeignKey('leave_requests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
    )
    # Composite index to speed up lookups and ordering by dates within a leave
    op.create_index(
        'ix_leave_date_ranges_leave_request_id_start_end',
        'leave_date_ranges',
        ['leave_request_id', 'start_date', 'end_date'],
        unique=False
    )

    # Backfill: for each existing leave_requests row, create a single date range
    bind = op.get_bind()
    try:
        rows = bind.execute(text("SELECT id, start_date, end_date FROM leave_requests")).fetchall()
    except Exception:
        rows = []

    if rows:
        # Prepare a lightweight table construct for bulk_insert
        ranges_tbl = table(
            'leave_date_ranges',
            column('leave_request_id', Integer),
            column('start_date', Date),
            column('end_date', Date),
        )

        data = []
        for row in rows:
            leave_id = row[0]
            s = row[1]
            e = row[2]
            if s is None and e is None:
                continue
            if s is None and e is not None:
                s = e
            if e is None and s is not None:
                e = s
            # Normalize ordering
            try:
                if s and e and e < s:
                    s, e = e, s
            except Exception:
                pass
            if s is None or e is None:
                continue
            data.append({'leave_request_id': leave_id, 'start_date': s, 'end_date': e})

        if data:
            op.bulk_insert(ranges_tbl, data)


def downgrade():
    # Drop index then table
    try:
        op.drop_index('ix_leave_date_ranges_leave_request_id_start_end', table_name='leave_date_ranges')
    except Exception:
        # Some backends drop indexes automatically with the table
        pass
    op.drop_table('leave_date_ranges')
