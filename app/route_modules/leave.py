from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from flask import flash, redirect, request, url_for
from flask_login import current_user, login_required

from app import db
from app.forms import EWPForm, LEAVE_TYPE_CHOICES, LeaveRequestForm
from app.models import EWPRecord, LeaveDateRange, LeaveRequest
from app.route_modules.shared import OFFICE_CHOICES, main


_ALLOWED_TIME_MODES = {'FULL_DAY', 'AM_HALF', 'PM_HALF'}


def _leave_redirect(page=None, tab=None):
    kwargs = {'view': 'leave'}
    if page is not None:
        kwargs['page'] = page
    if tab is not None:
        kwargs['tab'] = tab
    return redirect(url_for('main.dashboard', **kwargs))


def _parse_leave_range(range_value):
    parts = range_value.split(' to ')
    start_str = (parts[0] or '').strip() if parts else ''
    end_str = (parts[1] or '').strip() if len(parts) > 1 else ''
    fmt = '%Y-%m-%d'
    start = datetime.strptime(start_str, fmt).date() if start_str else None
    end = datetime.strptime(end_str, fmt).date() if end_str else None
    if start and not end:
        end = start
    if start and end and end < start:
        start, end = end, start
    return start, end


def _collect_leave_ranges(form, allow_form_fallback=False):
    range_strs = [value.strip() for value in request.form.getlist('date_range') if (value or '').strip()]
    if allow_form_fallback and not range_strs and (form.start_date.data or form.end_date.data):
        start_date = form.start_date.data
        end_date = form.end_date.data or form.start_date.data
        if start_date:
            range_strs = [f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"]

    time_modes = [(time_mode or '').strip() for time_mode in request.form.getlist('time_mode_range')]
    parsed_ranges = []
    for index, range_value in enumerate(range_strs):
        start_date, end_date = _parse_leave_range(range_value)
        if not start_date:
            continue
        time_mode = time_modes[index] if index < len(time_modes) else 'FULL_DAY'
        if time_mode not in _ALLOWED_TIME_MODES:
            time_mode = 'FULL_DAY'
        parsed_ranges.append((start_date, end_date or start_date, time_mode))
    return parsed_ranges


def _extract_leave_subtype(leave_type):
    subtype = None
    subtype_detail = None
    try:
        if leave_type in ('Vacation Leave', 'Special Privilege Leave'):
            subtype = (request.form.get('vacation_spl_subtype') or '').strip() or None
            subtype_detail = (request.form.get('vacation_spl_detail') or '').strip() or None
        elif leave_type == 'Sick Leave':
            subtype = (request.form.get('sick_leave_subtype') or '').strip() or None
            subtype_detail = (request.form.get('sick_leave_detail') or '').strip() or None
        elif leave_type == 'Special Leave Benefits for Women':
            subtype = 'Special Leave Benefits for Women'
            subtype_detail = (request.form.get('slbw_details') or '').strip() or None
        elif leave_type == 'Study Leave':
            subtype = (request.form.get('study_leave_purpose') or '').strip() or None
        elif leave_type == 'Others':
            subtype = (request.form.get('others_subtype') or '').strip() or None
    except Exception:
        pass
    return subtype, subtype_detail


@main.route('/leave_request/create', methods=['POST'])
@login_required
def create_leave_request():
    form = LeaveRequestForm()

    if not (current_user.is_admin or current_user.can_access_leave):
        flash('You are not authorized to access the Leave section.', 'danger')
        return redirect(url_for('main.dashboard', view='created'))

    form.office.choices = OFFICE_CHOICES
    try:
        form.leave_type.choices = LEAVE_TYPE_CHOICES
    except Exception:
        form.leave_type.choices = [(value, value) for value in [
            'COC', 'Vacation Leave', 'Mandatory/Forced Leave', 'Sick Leave', 'Wellness Leave', 'Maternity Leave',
            'Paternity Leave', 'Special Privilege Leave', 'Solo Parent Leave', 'Study Leave',
            '10-Day VAWC Leave', 'Rehabilitation Privilege', 'Special Leave Benefits for Women',
            'Special Emergency (Calamity)', 'Adoption Leave', 'Others',
        ]]

    if form.validate_on_submit():
        try:
            parsed_ranges = _collect_leave_ranges(form, allow_form_fallback=True)
            if not parsed_ranges:
                flash('Please select at least one valid date range.', 'danger')
                return _leave_redirect(tab='leave')

            parent_start = min(start_date for start_date, _, _ in parsed_ranges)
            parent_end = max(end_date for _, end_date, _ in parsed_ranges)
            barcode_value = (form.barcode.data or '').strip() or None
            leave_type = (form.leave_type.data or '').strip()
            subtype, subtype_detail = _extract_leave_subtype(leave_type)

            leave = LeaveRequest(
                barcode=barcode_value,
                employee_name=form.employee_name.data.strip(),
                office=form.office.data,
                leave_type=leave_type,
                subtype=subtype,
                subtype_detail=subtype_detail,
                status='For Computation',
                remarks=form.remarks.data,
                created_by_user_id=current_user.id,
                start_date=parent_start,
                end_date=parent_end,
            )
            db.session.add(leave)
            db.session.flush()

            for start_date, end_date, time_mode in parsed_ranges:
                db.session.add(LeaveDateRange(
                    leave_request_id=leave.id,
                    start_date=start_date,
                    end_date=end_date,
                    time_mode=time_mode,
                ))

            db.session.commit()
            flash('Leave record successfully created.', 'success')
        except Exception as exc:
            db.session.rollback()
            flash(f'Error creating leave request: {str(exc)}', 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'Error in {field}: {error}', 'danger')

    return _leave_redirect(tab='leave')


@main.route('/ewp/create', methods=['POST'])
@login_required
def create_ewp():
    if not (current_user.is_admin or current_user.can_access_leave):
        flash('You are not authorized to access the Leave/EWP section.', 'danger')
        return redirect(url_for('main.dashboard', view='created'))

    form = EWPForm()
    form.office.choices = OFFICE_CHOICES

    if form.validate_on_submit():
        try:
            raw_amount = (request.form.get('amount') or '').strip()
            normalized_amount = raw_amount.replace(',', '')
            amount_value = Decimal(normalized_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            record = EWPRecord(
                barcode=(form.barcode.data or '').strip() or None,
                employee_name=form.employee_name.data.strip(),
                office=form.office.data,
                amount=amount_value,
                purpose=(form.purpose.data or '').strip() or None,
                remarks=(form.remarks.data or '').strip() or None,
                status='For Computation',
                created_by_user_id=current_user.id,
                created_timestamp=datetime.utcnow(),
            )
            db.session.add(record)
            db.session.commit()
            flash('EWP record created successfully.', 'success')
        except (InvalidOperation, ValueError):
            db.session.rollback()
            flash('Invalid amount value.', 'danger')
        except Exception as exc:
            db.session.rollback()
            flash(f'Error creating EWP record: {str(exc)}', 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'Error in {field}: {error}', 'danger')

    return _leave_redirect(tab='ewp')


@main.route('/ewp/update_status/<int:ewp_id>', methods=['POST'])
@login_required
def update_ewp_status(ewp_id):
    page = request.args.get('page', 1, type=int)
    if not (current_user.is_admin or current_user.can_access_leave):
        flash('You are not authorized to access the Leave/EWP section.', 'danger')
        return _leave_redirect(page=page, tab='ewp')

    try:
        record = EWPRecord.query.get_or_404(ewp_id)
        new_status = (request.form.get('status') or '').strip()
        remarks = (request.form.get('remarks') or '').strip()
        valid_statuses = {'Pending', 'For Computation', 'Released'}
        if new_status not in valid_statuses:
            flash('Invalid status selection.', 'danger')
            return _leave_redirect(page=page, tab='ewp')

        record.status = new_status
        if new_status in ('Pending', 'Released') and remarks != '':
            record.remarks = remarks
        db.session.commit()
        flash('EWP status updated.', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(f'Error updating EWP status: {str(exc)}', 'danger')

    return _leave_redirect(page=page, tab='ewp')


@main.route('/ewp/edit/<int:ewp_id>', methods=['POST'])
@login_required
def edit_ewp(ewp_id):
    page = request.args.get('page', 1, type=int)
    if not (current_user.is_admin or current_user.can_access_leave):
        flash('You are not authorized to access the Leave/EWP section.', 'danger')
        return _leave_redirect(page=page, tab='ewp')

    try:
        record = EWPRecord.query.get_or_404(ewp_id)
        if not (current_user.is_admin or (record.created_by_user_id == current_user.id and current_user.can_access_leave)):
            flash('You are not authorized to edit this EWP record.', 'danger')
            return _leave_redirect(page=page, tab='ewp')
        if (not current_user.is_admin) and getattr(record, 'status', None) == 'Released':
            flash('Released EWP records can only be edited by an administrator.', 'warning')
            return _leave_redirect(page=page, tab='ewp')

        employee_name = (request.form.get('employee_name') or '').strip()
        barcode_value = (request.form.get('barcode') or '').strip() or None
        office = (request.form.get('office') or '').strip()
        amount_str = (request.form.get('amount') or '').strip()
        purpose = (request.form.get('purpose') or '').strip() or None
        remarks = (request.form.get('remarks') or '').strip() or None

        if not employee_name or not office:
            flash('Please provide Name and Office.', 'danger')
            return _leave_redirect(page=page, tab='ewp')

        if amount_str != '':
            try:
                normalized_amount = amount_str.replace(',', '')
                amount_value = Decimal(normalized_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            except (InvalidOperation, ValueError):
                flash('Invalid amount value.', 'danger')
                return _leave_redirect(page=page, tab='ewp')
            record.amount = amount_value

        record.employee_name = employee_name
        record.barcode = barcode_value
        record.office = office
        record.purpose = purpose
        record.remarks = remarks

        db.session.commit()
        flash('EWP record updated successfully.', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(f'Error updating EWP record: {str(exc)}', 'danger')

    return _leave_redirect(page=page, tab='ewp')


@main.route('/ewp/delete/<int:ewp_id>', methods=['POST'])
@login_required
def delete_ewp(ewp_id):
    page = request.args.get('page', 1, type=int)
    if not (current_user.is_admin or current_user.can_access_leave):
        flash('You are not authorized to access the Leave/EWP section.', 'danger')
        return _leave_redirect(page=page, tab='ewp')

    try:
        record = EWPRecord.query.get_or_404(ewp_id)
        if not (current_user.is_admin or (record.created_by_user_id == current_user.id and current_user.can_access_leave)):
            flash('You are not authorized to delete this EWP record.', 'danger')
            return _leave_redirect(page=page, tab='ewp')
        if (not current_user.is_admin) and getattr(record, 'status', None) == 'Released':
            flash('Released EWP records can only be deleted by an administrator.', 'warning')
            return _leave_redirect(page=page, tab='ewp')

        db.session.delete(record)
        db.session.commit()
        flash('EWP record deleted successfully.', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(f'Error deleting EWP record: {str(exc)}', 'danger')

    return _leave_redirect(page=page, tab='ewp')


@main.route('/leave_request/delete/<int:leave_id>', methods=['POST'])
@login_required
def delete_leave_request(leave_id):
    page = request.args.get('page', 1, type=int)
    try:
        leave = LeaveRequest.query.get_or_404(leave_id)
        if not (current_user.is_admin or (current_user.can_access_leave and leave.created_by_user_id == current_user.id)):
            flash('You are not authorized to delete this leave request.', 'danger')
            return _leave_redirect(page=page)
        if (not current_user.is_admin) and getattr(leave, 'status', None) == 'Released':
            flash('Released leave requests can only be deleted by an administrator.', 'warning')
            return _leave_redirect(page=page)

        db.session.delete(leave)
        db.session.commit()
        flash('Leave request deleted successfully.', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(f'Error deleting leave request: {str(exc)}', 'danger')

    return _leave_redirect(page=page)


@main.route('/leave_request/release/<int:leave_id>', methods=['POST'])
@login_required
def release_leave_request(leave_id):
    page = request.args.get('page', 1, type=int)
    if not (current_user.is_admin or current_user.can_access_leave):
        flash('You are not authorized to access the Leave section.', 'danger')
        return _leave_redirect(page=page)

    try:
        leave = LeaveRequest.query.get_or_404(leave_id)
        if leave.status == 'Released':
            flash('Leave request is already released.', 'info')
            return _leave_redirect(page=page)

        leave.status = 'Released'
        leave.released_timestamp = datetime.utcnow()
        db.session.commit()
        flash('Leave request released successfully.', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(f'Error releasing leave request: {str(exc)}', 'danger')

    return _leave_redirect(page=page)


@main.route('/leave_request/update_status/<int:leave_id>', methods=['POST'])
@login_required
def update_leave_request_status(leave_id):
    page = request.args.get('page', 1, type=int)
    if not (current_user.is_admin or current_user.can_access_leave):
        flash('You are not authorized to access the Leave section.', 'danger')
        return _leave_redirect(page=page)

    new_status = (request.form.get('status') or '').strip()
    remarks = (request.form.get('remarks') or '').strip()
    valid_statuses = {'Pending', 'For Computation', 'For Signature', 'Released'}
    if new_status not in valid_statuses:
        flash('Invalid status selection.', 'danger')
        return _leave_redirect(page=page)

    try:
        leave = LeaveRequest.query.get_or_404(leave_id)
        leave.status = new_status
        if new_status in ('Pending', 'For Signature', 'Released') and remarks != '':
            leave.remarks = remarks
        if new_status == 'Released' and not leave.released_timestamp:
            leave.released_timestamp = datetime.utcnow()
        db.session.commit()
        flash('Leave request status updated.', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(f'Error updating status: {str(exc)}', 'danger')

    return _leave_redirect(page=page)


@main.route('/leave_request/edit/<int:leave_id>', methods=['POST'])
@login_required
def edit_leave_request(leave_id):
    page = request.args.get('page', 1, type=int)
    if not current_user.can_access_leave and not current_user.is_admin:
        flash('You are not authorized to access the Leave section.', 'danger')
        return _leave_redirect(page=page)

    try:
        leave = LeaveRequest.query.get_or_404(leave_id)
        if not (current_user.is_admin or (current_user.can_access_leave and leave.created_by_user_id == current_user.id)):
            flash('You are not authorized to edit this leave request.', 'danger')
            return _leave_redirect(page=page)
        if (not current_user.is_admin) and getattr(leave, 'status', None) == 'Released':
            flash('Released leave requests can only be edited by an administrator.', 'warning')
            return _leave_redirect(page=page)

        employee_name = (request.form.get('employee_name') or '').strip()
        office = (request.form.get('office') or '').strip()
        leave_type = (request.form.get('leave_type') or '').strip()
        remarks = (request.form.get('remarks') or '').strip()
        barcode_value = (request.form.get('barcode') or '').strip() or None

        if not employee_name or not office or not leave_type:
            flash('Please provide Employee Name, Office, and Type.', 'danger')
            return _leave_redirect(page=page)

        subtype, subtype_detail = _extract_leave_subtype(leave_type)
        parsed_ranges = _collect_leave_ranges(form=None, allow_form_fallback=False)

        leave.employee_name = employee_name
        leave.office = office
        leave.leave_type = leave_type
        leave.remarks = remarks
        leave.barcode = barcode_value
        if subtype is not None:
            leave.subtype = subtype
        if subtype_detail is not None:
            leave.subtype_detail = subtype_detail

        if parsed_ranges:
            leave.start_date = min(start_date for start_date, _, _ in parsed_ranges)
            leave.end_date = max(end_date for _, end_date, _ in parsed_ranges)
            LeaveDateRange.query.filter_by(leave_request_id=leave.id).delete(synchronize_session=False)
            for start_date, end_date, time_mode in parsed_ranges:
                db.session.add(LeaveDateRange(
                    leave_request_id=leave.id,
                    start_date=start_date,
                    end_date=end_date,
                    time_mode=time_mode,
                ))

        db.session.commit()
        flash('Leave request updated successfully.', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(f'Error updating leave request: {str(exc)}', 'danger')

    return _leave_redirect(page=page)
