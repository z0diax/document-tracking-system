import json

from flask import current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_
from sqlalchemy.exc import OperationalError, ProgrammingError

from app import db
from app.forms import EmployeeForm
from app.models import (
    CIVIL_SERVICE_FIELD_NAMES,
    EDUCATION_FIELD_NAMES,
    Employee,
    LEARNING_DEV_FIELD_NAMES,
    VOLUNTARY_WORK_FIELD_NAMES,
    WORK_EXPERIENCE_FIELD_NAMES,
)
from app.route_modules.shared import OFFICE_CHOICES, main


def _can_manage_employee_records():
    return current_user.is_admin or current_user.can_access_employee_records


@main.route('/employees')
@login_required
def employee_list():
    form = EmployeeForm()
    form.office.choices = OFFICE_CHOICES
    try:
        if not _can_manage_employee_records():
            flash('You are not authorized to access Employee Records.', 'danger')
            return redirect(url_for('main.dashboard'))

        search_query = request.args.get('search', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = 10

        try:
            query = Employee.query
            if search_query:
                query = query.filter(
                    or_(
                        Employee.employee_name.ilike(f'%{search_query}%'),
                        Employee.bio_number.ilike(f'%{search_query}%'),
                        Employee.office.ilike(f'%{search_query}%'),
                        Employee.position.ilike(f'%{search_query}%'),
                        Employee.status.ilike(f'%{search_query}%'),
                    )
                )

            pagination = query.order_by(Employee.bio_number.asc()).paginate(
                page=page,
                per_page=per_page,
                error_out=False,
            )
            employees = pagination.items
        except (OperationalError, ProgrammingError) as exc:
            try:
                current_app.logger.error(f'Employee list DB error: {exc}')
            except Exception:
                pass
            flash('Employee module is not initialized in the database. Please run migrations.', 'warning')
            pagination = None
            employees = []

        return render_template(
            'employee_records.html',
            title='Onboarding',
            employees=employees,
            pagination=pagination,
            search_query=search_query,
            form=form,
        )
    except Exception as exc:
        try:
            current_app.logger.error(f'Unexpected error in /employees: {exc}')
        except Exception:
            pass
        flash('Unexpected error loading Employee Records.', 'danger')
        return render_template(
            'employee_records.html',
            title='Onboarding',
            employees=[],
            pagination=None,
            search_query=request.args.get('search', '').strip(),
            form=form,
        )


@main.route('/employees/add', methods=['GET', 'POST'])
@login_required
def add_employee():
    if not _can_manage_employee_records():
        flash('You are not authorized to add employees.', 'danger')
        return redirect(url_for('main.employee_list'))

    form = EmployeeForm()
    form.office.choices = OFFICE_CHOICES

    if form.validate_on_submit():
        try:
            existing = Employee.query.filter_by(bio_number=form.bio_number.data.strip()).first()
            if existing:
                flash(f'Biometric number is already taken by employee {existing.employee_name}.', 'danger')
                return redirect(url_for('main.employee_list'))

            surname = (form.surname.data or '').strip() if hasattr(form, 'surname') else ''
            first_name = (form.first_name.data or '').strip() if hasattr(form, 'first_name') else ''
            composed_name = (
                f'{surname}, {first_name}'.strip(', ').strip()
                if (surname or first_name)
                else ((form.employee_name.data or '').strip() if hasattr(form, 'employee_name') else '')
            )
            employee = Employee(
                bio_number=form.bio_number.data.strip(),
                employee_name=composed_name,
                office=form.office.data,
                position=form.position.data,
                status=(form.status.data or 'Active') if hasattr(form, 'status') else 'Active',
            )

            employee.surname = (form.surname.data or '').strip() if hasattr(form, 'surname') else None
            employee.first_name = (form.first_name.data or '').strip() if hasattr(form, 'first_name') else None
            employee.middle_name = (form.middle_name.data or '').strip() if hasattr(form, 'middle_name') else None
            employee.name_extension = (form.name_extension.data or '').strip() if hasattr(form, 'name_extension') else None
            employee.date_of_birth = (form.date_of_birth.data or '').strip() if hasattr(form, 'date_of_birth') else None
            employee.place_of_birth = (form.place_of_birth.data or '').strip() if hasattr(form, 'place_of_birth') else None
            employee.sex = (form.sex.data or '').strip() if hasattr(form, 'sex') else None
            employee.civil_status = (form.civil_status.data or '').strip() if hasattr(form, 'civil_status') else None
            employee.height_m = (form.height_m.data or '').strip() if hasattr(form, 'height_m') else None
            employee.weight_kg = (form.weight_kg.data or '').strip() if hasattr(form, 'weight_kg') else None
            employee.blood_type = (form.blood_type.data or '').strip() if hasattr(form, 'blood_type') else None
            employee.gsis_id_no = (form.gsis_id_no.data or '').strip() if hasattr(form, 'gsis_id_no') else None
            employee.pagibig_id_no = (form.pagibig_id_no.data or '').strip() if hasattr(form, 'pagibig_id_no') else None
            employee.philhealth_no = (form.philhealth_no.data or '').strip() if hasattr(form, 'philhealth_no') else None
            employee.sss_no = (form.sss_no.data or '').strip() if hasattr(form, 'sss_no') else None
            employee.tin = (form.tin.data or '').strip() if hasattr(form, 'tin') else None
            employee.agency_employee_no = (form.agency_employee_no.data or '').strip() if hasattr(form, 'agency_employee_no') else None
            employee.citizenship = (form.citizenship.data or '').strip() if hasattr(form, 'citizenship') else None
            employee.citizenship_details = (
                (form.citizenship_details.data or '').strip() if hasattr(form, 'citizenship_details') else None
            )
            employee.res_house_lot = (form.res_house_lot.data or '').strip() if hasattr(form, 'res_house_lot') else None
            employee.res_street = (form.res_street.data or '').strip() if hasattr(form, 'res_street') else None
            employee.res_subdivision = (
                (form.res_subdivision.data or '').strip() if hasattr(form, 'res_subdivision') else None
            )
            employee.res_barangay = (form.res_barangay.data or '').strip() if hasattr(form, 'res_barangay') else None
            employee.res_city_municipality = (
                (form.res_city_municipality.data or '').strip()
                if hasattr(form, 'res_city_municipality')
                else None
            )
            employee.res_province = (form.res_province.data or '').strip() if hasattr(form, 'res_province') else None
            employee.res_zip_code = (form.res_zip_code.data or '').strip() if hasattr(form, 'res_zip_code') else None
            employee.perm_house_lot = (
                (form.perm_house_lot.data or '').strip() if hasattr(form, 'perm_house_lot') else None
            )
            employee.perm_street = (form.perm_street.data or '').strip() if hasattr(form, 'perm_street') else None
            employee.perm_subdivision = (
                (form.perm_subdivision.data or '').strip() if hasattr(form, 'perm_subdivision') else None
            )
            employee.perm_barangay = (
                (form.perm_barangay.data or '').strip() if hasattr(form, 'perm_barangay') else None
            )
            employee.perm_city_municipality = (
                (form.perm_city_municipality.data or '').strip()
                if hasattr(form, 'perm_city_municipality')
                else None
            )
            employee.perm_province = (form.perm_province.data or '').strip() if hasattr(form, 'perm_province') else None
            employee.perm_zip_code = (form.perm_zip_code.data or '').strip() if hasattr(form, 'perm_zip_code') else None
            employee.telephone_no = (form.telephone_no.data or '').strip() if hasattr(form, 'telephone_no') else None
            employee.mobile_no = (form.mobile_no.data or '').strip() if hasattr(form, 'mobile_no') else None
            employee.email_address = (
                (form.email_address.data or '').strip() if hasattr(form, 'email_address') else None
            )

            db.session.add(employee)
            db.session.commit()
            flash('Employee added successfully.', 'success')
            return redirect(url_for('main.employee_list'))
        except Exception as exc:
            db.session.rollback()
            flash(f'Error adding employee: {str(exc)}', 'danger')

    return render_template('employee_form.html', title='Add Employee', form=form)


@main.route('/employees/edit/<int:employee_id>', methods=['GET', 'POST'])
@login_required
def edit_employee(employee_id):
    if not _can_manage_employee_records():
        flash('You are not authorized to edit employees.', 'danger')
        return redirect(url_for('main.employee_list'))

    employee = Employee.query.get_or_404(employee_id)
    form = EmployeeForm(obj=employee)
    form.office.choices = OFFICE_CHOICES

    if form.validate_on_submit():
        try:
            if employee.bio_number != form.bio_number.data.strip():
                existing = Employee.query.filter_by(bio_number=form.bio_number.data.strip()).first()
                if existing:
                    flash(f'Biometric number is already taken by employee {existing.employee_name}.', 'danger')
                    return redirect(url_for('main.employee_list'))

            employee.bio_number = form.bio_number.data.strip()
            employee.employee_name = form.employee_name.data.strip()
            employee.office = form.office.data
            employee.position = form.position.data
            if hasattr(form, 'status') and (form.status.data or '').strip():
                employee.status = form.status.data

            employee.surname = (form.surname.data or '').strip() if hasattr(form, 'surname') else employee.surname
            employee.first_name = (
                (form.first_name.data or '').strip() if hasattr(form, 'first_name') else employee.first_name
            )
            employee.middle_name = (
                (form.middle_name.data or '').strip() if hasattr(form, 'middle_name') else employee.middle_name
            )
            employee.name_extension = (
                (form.name_extension.data or '').strip()
                if hasattr(form, 'name_extension')
                else employee.name_extension
            )
            employee.date_of_birth = (
                (form.date_of_birth.data or '').strip() if hasattr(form, 'date_of_birth') else employee.date_of_birth
            )
            employee.place_of_birth = (
                (form.place_of_birth.data or '').strip()
                if hasattr(form, 'place_of_birth')
                else employee.place_of_birth
            )
            employee.sex = (form.sex.data or '').strip() if hasattr(form, 'sex') else employee.sex
            employee.civil_status = (
                (form.civil_status.data or '').strip()
                if hasattr(form, 'civil_status')
                else employee.civil_status
            )
            employee.height_m = (form.height_m.data or '').strip() if hasattr(form, 'height_m') else employee.height_m
            employee.weight_kg = (form.weight_kg.data or '').strip() if hasattr(form, 'weight_kg') else employee.weight_kg
            employee.blood_type = (
                (form.blood_type.data or '').strip() if hasattr(form, 'blood_type') else employee.blood_type
            )
            employee.gsis_id_no = (
                (form.gsis_id_no.data or '').strip() if hasattr(form, 'gsis_id_no') else employee.gsis_id_no
            )
            employee.pagibig_id_no = (
                (form.pagibig_id_no.data or '').strip()
                if hasattr(form, 'pagibig_id_no')
                else employee.pagibig_id_no
            )
            employee.philhealth_no = (
                (form.philhealth_no.data or '').strip()
                if hasattr(form, 'philhealth_no')
                else employee.philhealth_no
            )
            employee.sss_no = (form.sss_no.data or '').strip() if hasattr(form, 'sss_no') else employee.sss_no
            employee.tin = (form.tin.data or '').strip() if hasattr(form, 'tin') else employee.tin
            employee.agency_employee_no = (
                (form.agency_employee_no.data or '').strip()
                if hasattr(form, 'agency_employee_no')
                else employee.agency_employee_no
            )
            employee.citizenship = (
                (form.citizenship.data or '').strip() if hasattr(form, 'citizenship') else employee.citizenship
            )
            employee.citizenship_details = (
                (form.citizenship_details.data or '').strip()
                if hasattr(form, 'citizenship_details')
                else employee.citizenship_details
            )
            employee.res_house_lot = (
                (form.res_house_lot.data or '').strip() if hasattr(form, 'res_house_lot') else employee.res_house_lot
            )
            employee.res_street = (
                (form.res_street.data or '').strip() if hasattr(form, 'res_street') else employee.res_street
            )
            employee.res_subdivision = (
                (form.res_subdivision.data or '').strip()
                if hasattr(form, 'res_subdivision')
                else employee.res_subdivision
            )
            employee.res_barangay = (
                (form.res_barangay.data or '').strip() if hasattr(form, 'res_barangay') else employee.res_barangay
            )
            employee.res_city_municipality = (
                (form.res_city_municipality.data or '').strip()
                if hasattr(form, 'res_city_municipality')
                else employee.res_city_municipality
            )
            employee.res_province = (
                (form.res_province.data or '').strip() if hasattr(form, 'res_province') else employee.res_province
            )
            employee.res_zip_code = (
                (form.res_zip_code.data or '').strip() if hasattr(form, 'res_zip_code') else employee.res_zip_code
            )
            employee.perm_house_lot = (
                (form.perm_house_lot.data or '').strip() if hasattr(form, 'perm_house_lot') else employee.perm_house_lot
            )
            employee.perm_street = (
                (form.perm_street.data or '').strip() if hasattr(form, 'perm_street') else employee.perm_street
            )
            employee.perm_subdivision = (
                (form.perm_subdivision.data or '').strip()
                if hasattr(form, 'perm_subdivision')
                else employee.perm_subdivision
            )
            employee.perm_barangay = (
                (form.perm_barangay.data or '').strip() if hasattr(form, 'perm_barangay') else employee.perm_barangay
            )
            employee.perm_city_municipality = (
                (form.perm_city_municipality.data or '').strip()
                if hasattr(form, 'perm_city_municipality')
                else employee.perm_city_municipality
            )
            employee.perm_province = (
                (form.perm_province.data or '').strip() if hasattr(form, 'perm_province') else employee.perm_province
            )
            employee.perm_zip_code = (
                (form.perm_zip_code.data or '').strip() if hasattr(form, 'perm_zip_code') else employee.perm_zip_code
            )
            employee.telephone_no = (
                (form.telephone_no.data or '').strip()
                if hasattr(form, 'telephone_no')
                else employee.telephone_no
            )
            employee.mobile_no = (
                (form.mobile_no.data or '').strip() if hasattr(form, 'mobile_no') else employee.mobile_no
            )
            employee.email_address = (
                (form.email_address.data or '').strip()
                if hasattr(form, 'email_address')
                else employee.email_address
            )

            edited_surname = (form.surname.data or '').strip() if hasattr(form, 'surname') else ''
            edited_first_name = (form.first_name.data or '').strip() if hasattr(form, 'first_name') else ''
            if edited_surname or edited_first_name:
                employee.employee_name = f'{edited_surname}, {edited_first_name}'.strip(', ').strip()

            db.session.commit()
            flash('Employee updated successfully.', 'success')
            return redirect(url_for('main.employee_list'))
        except Exception as exc:
            db.session.rollback()
            flash(f'Error updating employee: {str(exc)}', 'danger')

    return render_template('employee_form.html', title='Edit Employee', form=form, employee=employee)


@main.route('/employees/delete/<int:employee_id>', methods=['POST'])
@login_required
def delete_employee(employee_id):
    if not _can_manage_employee_records():
        flash('You are not authorized to delete employees.', 'danger')
        return redirect(url_for('main.employee_list'))

    employee = Employee.query.get_or_404(employee_id)
    try:
        db.session.delete(employee)
        db.session.commit()
        flash('Employee deleted successfully.', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(f'Error deleting employee: {str(exc)}', 'danger')

    return redirect(url_for('main.employee_list'))


@main.route('/employees/toggle_status/<int:employee_id>', methods=['POST'])
@login_required
def toggle_employee_status(employee_id):
    if not _can_manage_employee_records():
        flash('You are not authorized to modify employees.', 'danger')
        return redirect(url_for('main.employee_list'))
    try:
        employee = Employee.query.get_or_404(employee_id)
        employee.status = 'Inactive' if employee.status == 'Active' else 'Active'
        db.session.commit()
        flash(f'Employee status updated to {employee.status}.', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(f'Error updating employee status: {str(exc)}', 'danger')
    return redirect(url_for('main.employee_list'))


@main.route('/employees/update_profile/<int:employee_id>', methods=['POST'])
@login_required
def update_employee_profile(employee_id):
    if not _can_manage_employee_records():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    try:
        employee = Employee.query.get_or_404(employee_id)
        allowed_fields = [
            'surname', 'first_name', 'middle_name', 'name_extension',
            'date_of_birth', 'place_of_birth', 'sex', 'civil_status',
            'height_m', 'weight_kg', 'blood_type',
            'gsis_id_no', 'pagibig_id_no', 'philhealth_no', 'sss_no', 'tin', 'agency_employee_no',
            'citizenship', 'citizenship_details',
            'res_house_lot', 'res_street', 'res_subdivision', 'res_barangay',
            'res_city_municipality', 'res_province', 'res_zip_code',
            'perm_house_lot', 'perm_street', 'perm_subdivision', 'perm_barangay',
            'perm_city_municipality', 'perm_province', 'perm_zip_code',
            'telephone_no', 'mobile_no', 'email_address',
            'spouse_surname', 'spouse_first_name', 'spouse_middle_name', 'spouse_occupation',
            'spouse_employer_name', 'spouse_business_address', 'spouse_telephone_no',
            'father_surname', 'father_first_name', 'father_middle_name', 'father_extension',
            'mother_maiden_surname', 'mother_maiden_first_name', 'mother_maiden_middle_name',
            'children_info',
            'elem_school_name', 'elem_basic_education', 'elem_period_from', 'elem_period_to',
            'elem_highest_level', 'elem_year_graduated', 'elem_scholarships',
            'sec_school_name', 'sec_basic_education', 'sec_period_from', 'sec_period_to',
            'sec_highest_level', 'sec_year_graduated', 'sec_scholarships',
            'voc_school_name', 'voc_basic_education', 'voc_period_from', 'voc_period_to',
            'voc_highest_level', 'voc_year_graduated', 'voc_scholarships',
            'college_school_name', 'college_basic_education', 'college_period_from', 'college_period_to',
            'college_highest_level', 'college_year_graduated', 'college_scholarships',
            'grad_school_name', 'grad_basic_education', 'grad_period_from', 'grad_period_to',
            'grad_highest_level', 'grad_year_graduated', 'grad_scholarships',
            'bio_number', 'office', 'position', 'status',
        ]

        data = request.form if request.form else (request.get_json(silent=True) or {})

        if 'bio_number' in data:
            new_bio = (data.get('bio_number') or '').strip()
            if new_bio and new_bio != (employee.bio_number or ''):
                dupe = Employee.query.filter(Employee.bio_number == new_bio, Employee.id != employee.id).first()
                if dupe:
                    return jsonify({
                        'success': False,
                        'message': f'Biometric number is already taken by employee {dupe.employee_name}',
                    }), 400

        if 'office' in data:
            office = (data.get('office') or '').strip()
            valid_offices = {value for (value, _label) in OFFICE_CHOICES}
            if office and office not in valid_offices:
                return jsonify({'success': False, 'message': 'Invalid office selection'}), 400

        if 'position' in data:
            position = (data.get('position') or '').strip()
            valid_positions = {'Job Order Worker', 'Contract of Service'}
            if position and position not in valid_positions:
                return jsonify({'success': False, 'message': 'Invalid position selection'}), 400

        if 'status' in data:
            status = (data.get('status') or '').strip()
            if status and status not in {'Active', 'Inactive'}:
                return jsonify({'success': False, 'message': 'Invalid status value'}), 400

        education_json_fields = [
            ('elem_records_json', 'elem'),
            ('sec_records_json', 'sec'),
            ('voc_records_json', 'voc'),
            ('college_records_json', 'college'),
            ('grad_records_json', 'grad'),
        ]

        def _normalize_education_entries(raw_entries):
            normalized = []
            if isinstance(raw_entries, list):
                for entry in raw_entries:
                    if not isinstance(entry, dict):
                        continue
                    norm = {field: (entry.get(field) or '').strip() for field in EDUCATION_FIELD_NAMES}
                    if any(norm.values()):
                        normalized.append(norm)
            return normalized

        def _normalize_civil_service_entries(raw_entries):
            normalized = []
            if isinstance(raw_entries, list):
                for entry in raw_entries:
                    if not isinstance(entry, dict):
                        continue
                    norm = {field: (entry.get(field) or '').strip() for field in CIVIL_SERVICE_FIELD_NAMES}
                    if any(norm.values()):
                        normalized.append(norm)
            return normalized

        def _normalize_work_experience_entries(raw_entries):
            normalized = []
            if isinstance(raw_entries, list):
                for entry in raw_entries:
                    if not isinstance(entry, dict):
                        continue
                    norm = {field: (entry.get(field) or '').strip() for field in WORK_EXPERIENCE_FIELD_NAMES}
                    if any(norm.values()):
                        normalized.append(norm)
            return normalized

        def _normalize_voluntary_work_entries(raw_entries):
            normalized = []
            if isinstance(raw_entries, list):
                for entry in raw_entries:
                    if not isinstance(entry, dict):
                        continue
                    norm = {field: (entry.get(field) or '').strip() for field in VOLUNTARY_WORK_FIELD_NAMES}
                    if any(norm.values()):
                        normalized.append(norm)
            return normalized

        def _normalize_learning_dev_entries(raw_entries):
            normalized = []
            if isinstance(raw_entries, list):
                for entry in raw_entries:
                    if not isinstance(entry, dict):
                        continue
                    norm = {field: (entry.get(field) or '').strip() for field in LEARNING_DEV_FIELD_NAMES}
                    if any(norm.values()):
                        normalized.append(norm)
            return normalized

        normalized_education = {}
        updated = {}

        for json_field, prefix in education_json_fields:
            if json_field in data:
                raw_json = data.get(json_field) or ''
                try:
                    parsed = json.loads(raw_json)
                except Exception:
                    parsed = []
                normalized = _normalize_education_entries(parsed)
                json_str = json.dumps(normalized)
                setattr(employee, json_field, json_str if normalized else None)
                normalized_education[prefix] = normalized
                updated[json_field] = json_str

        if 'civil_service_records_json' in data:
            raw_json = data.get('civil_service_records_json') or ''
            try:
                parsed = json.loads(raw_json)
            except Exception:
                parsed = []
            normalized_cse = _normalize_civil_service_entries(parsed)
            json_str = json.dumps(normalized_cse)
            employee.civil_service_records_json = json_str if normalized_cse else None
            updated['civil_service_records_json'] = json_str

        if 'work_experience_json' in data:
            raw_json = data.get('work_experience_json') or ''
            try:
                parsed = json.loads(raw_json)
            except Exception:
                parsed = []
            normalized_we = _normalize_work_experience_entries(parsed)
            json_str = json.dumps(normalized_we)
            employee.work_experience_json = json_str if normalized_we else None
            updated['work_experience_json'] = json_str

        if 'voluntary_work_json' in data:
            raw_json = data.get('voluntary_work_json') or ''
            try:
                parsed = json.loads(raw_json)
            except Exception:
                parsed = []
            normalized_vw = _normalize_voluntary_work_entries(parsed)
            json_str = json.dumps(normalized_vw)
            employee.voluntary_work_json = json_str if normalized_vw else None
            updated['voluntary_work_json'] = json_str

        if 'learning_dev_json' in data:
            raw_json = data.get('learning_dev_json') or ''
            try:
                parsed = json.loads(raw_json)
            except Exception:
                parsed = []
            normalized_ld = _normalize_learning_dev_entries(parsed)
            json_str = json.dumps(normalized_ld)
            employee.learning_dev_json = json_str if normalized_ld else None
            updated['learning_dev_json'] = json_str

        for key in allowed_fields:
            if key in data:
                value = (data.get(key) or '').strip()
                if key == 'children_info':
                    lines = [line.strip() for line in value.splitlines()]
                    lines = [line for line in lines if line]
                    value = '\n'.join(lines)
                setattr(employee, key, value if value != '' else None)
                updated[key] = getattr(employee, key)

        for prefix, entries in normalized_education.items():
            first_entry = entries[0] if entries else {}
            for field in EDUCATION_FIELD_NAMES:
                column_name = f'{prefix}_{field}'
                value = first_entry.get(field, '').strip() if first_entry else ''
                setattr(employee, column_name, value if value != '' else None)
                updated[column_name] = getattr(employee, column_name)

        if ('surname' in data) or ('first_name' in data):
            surname = (employee.surname or '').strip()
            first_name = (employee.first_name or '').strip()
            employee.employee_name = f'{surname}, {first_name}'.strip(', ').strip()

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Profile updated successfully.',
            'updated': updated,
            'employee_name': employee.employee_name or '',
            'id': employee.id,
        })
    except Exception as exc:
        db.session.rollback()
        try:
            current_app.logger.error(f'Inline profile update error: {exc}')
        except Exception:
            pass
        return jsonify({'success': False, 'message': str(exc)}), 500


@main.route('/employees/check_bio_number', methods=['POST'])
@login_required
def check_bio_number():
    """Validate Employee biometric (bio_number) availability."""
    if not _can_manage_employee_records():
        return jsonify({'valid': False, 'message': 'Unauthorized'}), 403
    try:
        bio = (request.form.get('bio_number') or '').strip()
        exclude_id = request.form.get('exclude_id', type=int)
        if not bio:
            return jsonify({'valid': False, 'message': 'Biometric number is required'})
        existing = Employee.query.filter_by(bio_number=bio).first()
        if existing and (exclude_id is None or existing.id != exclude_id):
            return jsonify({
                'valid': False,
                'message': f'Biometric number is already taken by employee {existing.employee_name}',
                'employee_name': existing.employee_name,
            })
        return jsonify({'valid': True, 'message': 'Biometric number is available'})
    except Exception as exc:
        try:
            current_app.logger.error(f'Error in check_bio_number: {exc}')
        except Exception:
            pass
        return jsonify({'valid': False, 'message': 'Server error'}), 500
