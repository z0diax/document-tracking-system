from datetime import datetime

from flask import flash, redirect, request, url_for
from flask_login import current_user, login_required

from app import db
from app.forms import RSPRecordForm
from app.models import RSPPhaseLog, RSPRecord
from app.route_modules.shared import OFFICE_CHOICES, RSP_TOTAL_PHASES, get_rsp_phase_name, main


def _rsp_view_args():
    page = request.form.get('page', 1, type=int)
    tab = (request.form.get('tab') or 'ongoing').strip().lower()
    if tab not in {'ongoing', 'completed'}:
        tab = 'ongoing'
    return {
        'page': page,
        'tab': tab,
        'rsp_search': (request.form.get('rsp_search') or '').strip(),
        'rsp_office': (request.form.get('rsp_office') or '').strip(),
        'rsp_phase': (request.form.get('rsp_phase') or '').strip(),
    }


def _redirect_to_rsp_dashboard(tab=None, page=None, **kwargs):
    args = {
        'view': 'rsp',
        'tab': tab if tab is not None else kwargs.pop('tab', 'ongoing'),
        'page': page if page is not None else kwargs.pop('page', 1),
        'rsp_search': kwargs.pop('rsp_search', ''),
        'rsp_office': kwargs.pop('rsp_office', ''),
        'rsp_phase': kwargs.pop('rsp_phase', ''),
    }
    args.update(kwargs)
    return redirect(url_for('main.dashboard', **args))


@main.route('/rsp/create', methods=['POST'])
@login_required
def create_rsp():
    form = RSPRecordForm()
    form.office.choices = OFFICE_CHOICES
    view_args = _rsp_view_args()

    if not (current_user.is_admin or current_user.can_see_rsp_tracker):
        flash('You are not authorized to create RSP records.', 'danger')
        return redirect(url_for('main.dashboard', view='created'))

    if form.validate_on_submit():
        try:
            posted_date = form.date_posted.data
            phase_start_at = (
                datetime.combine(posted_date, datetime.min.time())
                if posted_date is not None else datetime.utcnow()
            )
            record = RSPRecord(
                position=(form.position.data or '').strip(),
                office=form.office.data,
                remarks=((form.remarks.data or '').strip() or None),
                date_posted=posted_date,
                phase_number=1,
                phase_started_at=phase_start_at,
                created_by_user_id=current_user.id,
            )
            db.session.add(record)
            db.session.commit()
            flash('RSP record created successfully.', 'success')
            return _redirect_to_rsp_dashboard(
                tab='ongoing',
                page=1,
                rsp_search=view_args['rsp_search'],
                rsp_office=view_args['rsp_office'],
                rsp_phase=view_args['rsp_phase'],
            )
        except Exception as exc:
            db.session.rollback()
            flash(f'Error creating RSP record: {str(exc)}', 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'Error in {field}: {error}', 'danger')

    return _redirect_to_rsp_dashboard(**view_args)


@main.route('/rsp/<int:rsp_id>/advance', methods=['POST'])
@login_required
def advance_rsp_phase(rsp_id):
    view_args = _rsp_view_args()
    record = RSPRecord.query.get_or_404(rsp_id)

    if not (current_user.is_admin or current_user.can_see_rsp_tracker):
        flash('You are not authorized to update RSP records.', 'danger')
        return redirect(url_for('main.dashboard', view='created'))

    if not (current_user.is_admin or record.created_by_user_id == current_user.id):
        flash('You are not authorized to update this RSP record.', 'danger')
        return _redirect_to_rsp_dashboard(**view_args)

    current_phase = record.phase_number or 1
    final_phase_logged = any((log.phase_number == RSP_TOTAL_PHASES) for log in (record.phase_logs or []))

    if final_phase_logged or current_phase > RSP_TOTAL_PHASES:
        flash('This RSP is already completed.', 'warning')
        return _redirect_to_rsp_dashboard(
            tab='completed',
            page=1,
            rsp_search=view_args['rsp_search'],
            rsp_office=view_args['rsp_office'],
            rsp_phase=view_args['rsp_phase'],
        )

    if current_phase >= RSP_TOTAL_PHASES:
        flash('This RSP is already at Phase 12. Click Complete to finish the process.', 'warning')
        return _redirect_to_rsp_dashboard(**view_args)

    try:
        now = datetime.utcnow()
        phase_log = RSPPhaseLog(
            rsp_record_id=record.id,
            phase_number=current_phase,
            phase_name=get_rsp_phase_name(current_phase),
            completed_at=now,
            completed_by_user_id=current_user.id,
        )
        db.session.add(phase_log)

        next_phase = current_phase + 1
        record.phase_number = min(next_phase, RSP_TOTAL_PHASES)
        if record.date_posted is None and record.phase_started_at:
            record.date_posted = record.phase_started_at.date()
        db.session.commit()
        flash(f'Advanced to phase {record.phase_number}.', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(f'Error advancing phase: {str(exc)}', 'danger')

    return _redirect_to_rsp_dashboard(**view_args)


@main.route('/rsp/<int:rsp_id>/complete', methods=['POST'])
@login_required
def complete_rsp(rsp_id):
    view_args = _rsp_view_args()
    record = RSPRecord.query.get_or_404(rsp_id)

    if not (current_user.is_admin or current_user.can_see_rsp_tracker):
        flash('You are not authorized to update RSP records.', 'danger')
        return redirect(url_for('main.dashboard', view='created'))

    if not (current_user.is_admin or record.created_by_user_id == current_user.id):
        flash('You are not authorized to update this RSP record.', 'danger')
        return _redirect_to_rsp_dashboard(**view_args)

    current_phase = record.phase_number or 1
    final_phase_logged = any((log.phase_number == RSP_TOTAL_PHASES) for log in (record.phase_logs or []))

    if final_phase_logged or current_phase > RSP_TOTAL_PHASES:
        flash('This RSP is already completed.', 'warning')
        return _redirect_to_rsp_dashboard(
            tab='completed',
            page=1,
            rsp_search=view_args['rsp_search'],
            rsp_office=view_args['rsp_office'],
            rsp_phase=view_args['rsp_phase'],
        )

    if current_phase < RSP_TOTAL_PHASES:
        flash(f'You can only complete this process at Phase {RSP_TOTAL_PHASES}.', 'warning')
        return _redirect_to_rsp_dashboard(**view_args)

    try:
        now = datetime.utcnow()
        phase_log = RSPPhaseLog(
            rsp_record_id=record.id,
            phase_number=RSP_TOTAL_PHASES,
            phase_name=get_rsp_phase_name(RSP_TOTAL_PHASES),
            completed_at=now,
            completed_by_user_id=current_user.id,
        )
        db.session.add(phase_log)
        record.phase_number = RSP_TOTAL_PHASES
        if record.date_posted is None and record.phase_started_at:
            record.date_posted = record.phase_started_at.date()
        db.session.commit()
        flash('RSP process marked as completed.', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(f'Error completing RSP process: {str(exc)}', 'danger')

    return _redirect_to_rsp_dashboard(
        tab='completed',
        page=1,
        rsp_search=view_args['rsp_search'],
        rsp_office=view_args['rsp_office'],
        rsp_phase=view_args['rsp_phase'],
    )


@main.route('/rsp/<int:rsp_id>/delete', methods=['POST'])
@login_required
def delete_rsp(rsp_id):
    view_args = _rsp_view_args()
    record = RSPRecord.query.get_or_404(rsp_id)

    if not (current_user.is_admin or current_user.can_see_rsp_tracker):
        flash('You are not authorized to delete RSP records.', 'danger')
        return redirect(url_for('main.dashboard', view='created'))

    if not (current_user.is_admin or record.created_by_user_id == current_user.id):
        flash('You are not authorized to delete this RSP record.', 'danger')
        return _redirect_to_rsp_dashboard(**view_args)

    try:
        db.session.delete(record)
        db.session.commit()
        flash('RSP record deleted.', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(f'Error deleting RSP record: {str(exc)}', 'danger')

    return _redirect_to_rsp_dashboard(**view_args)
