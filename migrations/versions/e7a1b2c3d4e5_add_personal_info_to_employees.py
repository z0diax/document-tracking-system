"""add personal info columns to employees

Revision ID: e7a1b2c3d4e5
Revises: d1e2f3a4b5c6
Create Date: 2025-10-06 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e7a1b2c3d4e5'
down_revision = 'd1e2f3a4b5c6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('employees') as batch_op:
        # Personal Information (identity)
        batch_op.add_column(sa.Column('surname', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('first_name', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('middle_name', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('name_extension', sa.String(length=20), nullable=True))

        # Birth details
        batch_op.add_column(sa.Column('date_of_birth', sa.String(length=20), nullable=True))  # mm/dd/yyyy as string
        batch_op.add_column(sa.Column('place_of_birth', sa.String(length=200), nullable=True))

        # Demographics
        batch_op.add_column(sa.Column('sex', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('civil_status', sa.String(length=20), nullable=True))

        # Physical
        batch_op.add_column(sa.Column('height_m', sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column('weight_kg', sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column('blood_type', sa.String(length=10), nullable=True))

        # Government IDs
        batch_op.add_column(sa.Column('gsis_id_no', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('pagibig_id_no', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('philhealth_no', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('sss_no', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('tin', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('agency_employee_no', sa.String(length=120), nullable=True))

        # Citizenship
        batch_op.add_column(sa.Column('citizenship', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('citizenship_details', sa.Text(), nullable=True))

        # Residential Address
        batch_op.add_column(sa.Column('res_house_lot', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('res_street', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('res_subdivision', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('res_barangay', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('res_city_municipality', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('res_province', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('res_zip_code', sa.String(length=10), nullable=True))

        # Permanent Address
        batch_op.add_column(sa.Column('perm_house_lot', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('perm_street', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('perm_subdivision', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('perm_barangay', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('perm_city_municipality', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('perm_province', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('perm_zip_code', sa.String(length=10), nullable=True))

        # Contact
        batch_op.add_column(sa.Column('telephone_no', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('mobile_no', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('email_address', sa.String(length=120), nullable=True))


def downgrade():
    with op.batch_alter_table('employees') as batch_op:
        # Contact
        batch_op.drop_column('email_address')
        batch_op.drop_column('mobile_no')
        batch_op.drop_column('telephone_no')

        # Permanent Address
        batch_op.drop_column('perm_zip_code')
        batch_op.drop_column('perm_province')
        batch_op.drop_column('perm_city_municipality')
        batch_op.drop_column('perm_barangay')
        batch_op.drop_column('perm_subdivision')
        batch_op.drop_column('perm_street')
        batch_op.drop_column('perm_house_lot')

        # Residential Address
        batch_op.drop_column('res_zip_code')
        batch_op.drop_column('res_province')
        batch_op.drop_column('res_city_municipality')
        batch_op.drop_column('res_barangay')
        batch_op.drop_column('res_subdivision')
        batch_op.drop_column('res_street')
        batch_op.drop_column('res_house_lot')

        # Citizenship
        batch_op.drop_column('citizenship_details')
        batch_op.drop_column('citizenship')

        # Government IDs
        batch_op.drop_column('agency_employee_no')
        batch_op.drop_column('tin')
        batch_op.drop_column('sss_no')
        batch_op.drop_column('philhealth_no')
        batch_op.drop_column('pagibig_id_no')
        batch_op.drop_column('gsis_id_no')

        # Physical
        batch_op.drop_column('blood_type')
        batch_op.drop_column('weight_kg')
        batch_op.drop_column('height_m')

        # Demographics
        batch_op.drop_column('civil_status')
        batch_op.drop_column('sex')

        # Birth details
        batch_op.drop_column('place_of_birth')
        batch_op.drop_column('date_of_birth')

        # Identity
        batch_op.drop_column('name_extension')
        batch_op.drop_column('middle_name')
        batch_op.drop_column('first_name')
        batch_op.drop_column('surname')
