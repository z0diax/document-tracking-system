from datetime import datetime

from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import and_, case, or_
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import joinedload, selectinload

from app import db
from app.forms import (
    BatchDeclineDocumentForm,
    BatchForwardDocumentForm,
    DeclineDocumentForm,
    DocumentForm,
    EWPForm,
    ForwardDocumentForm,
    LEAVE_TYPE_CHOICES,
    LeaveRequestForm,
    RSPRecordForm,
)
from app.models import (
    Document,
    EWPRecord,
    LeaveRequest,
    RSPPhaseLog,
    RSPRecord,
    ReleaseBatch,
    ReleaseBatchDocument,
    format_timedelta,
    to_local_time,
)
from app.route_modules.shared import (
    ACTION_TAKEN_CHOICES,
    CLASSIFICATION_CHOICES,
    OFFICE_CHOICES,
    RSP_TOTAL_PHASES,
    STATUS_CHOICES,
    get_recipient_choices,
    main,
)
from app.utils import calculate_business_hours


def _parse_date_filter(date_str):
    if not date_str:
        return None, None
    try:
        parts = date_str.split(' to ')
        start_str = parts[0].strip() if parts else ''
        end_str = parts[1].strip() if len(parts) > 1 else ''
        fmt = '%Y-%m-%d'
        start = datetime.strptime(start_str, fmt).date() if start_str else None
        end = datetime.strptime(end_str, fmt).date() if end_str else None
        if start and not end:
            end = start
        if start and end and end < start:
            start, end = end, start
        return start, end
    except Exception:
        return None, None


@main.route('/dashboard')
@login_required
def dashboard():
    page = request.args.get('page', 1, type=int)
    view = request.args.get('view', 'created')
    search_query = request.args.get('search', '').strip()
    date_filter = request.args.get('date_filter', '').strip()
    per_page = 10

    # Restrict RSP view to users explicitly granted access (admins always allowed).
    if view == 'rsp' and not (current_user.is_admin or current_user.can_see_rsp_tracker):
        flash('You are not authorized to access the RSP Tracker section.', 'danger')
        return redirect(url_for('main.dashboard', view='created'))

    # Restrict Leave view to permitted users (admins always allowed).
    if view == 'leave' and not (current_user.is_admin or current_user.can_access_leave):
        flash('You are not authorized to access the Leave section.', 'danger')
        return redirect(url_for('main.dashboard', view='created'))

    form = DocumentForm()
    decline_form = DeclineDocumentForm()
    forward_form = ForwardDocumentForm()
    rsp_form = RSPRecordForm()
    
    # Initialize batch forms
    batch_decline_form = BatchDeclineDocumentForm()
    batch_forward_form = BatchForwardDocumentForm()
    
    form.office.choices = OFFICE_CHOICES
    form.classification.choices = CLASSIFICATION_CHOICES
    form.status.choices = STATUS_CHOICES
    form.action_taken.choices = ACTION_TAKEN_CHOICES
    form.recipient.choices = get_recipient_choices()
    rsp_form.office.choices = OFFICE_CHOICES
    
    forward_form.recipient.choices = get_recipient_choices()
    batch_forward_form.recipient.choices = get_recipient_choices()
    
    created_query = Document.query.filter(
        Document.creator_id == current_user.id,
        Document.status != 'Archived'
    )
    
    received_query = Document.query.options(joinedload(Document.creator)).filter(
        Document.recipient_id == current_user.id,
        Document.status != 'Archived'
    )
    
    if search_query:
        if view == 'received':
            received_query = received_query.filter(
                or_(
                    Document.title.ilike(f'%{search_query}%'),
                    Document.office.ilike(f'%{search_query}%'),
                    Document.classification.ilike(f'%{search_query}%'),
                    or_(
                        Document.barcode.ilike(f'%{search_query}%'),
                        Document.barcode == search_query
                    )
                )
            )
        else:  
            created_query = created_query.filter(
                or_(
                    Document.title.ilike(f'%{search_query}%'),
                    Document.office.ilike(f'%{search_query}%'),
                    Document.classification.ilike(f'%{search_query}%'),
                    or_(
                        Document.barcode.ilike(f'%{search_query}%'),
                        Document.barcode == search_query
                    )
                )
            )

    if view == 'received':
        status_order = case(
            (Document.status == 'Pending', 0),
            (Document.status == 'Accepted', 1),
            (Document.status == 'Forwarded', 2),
            (Document.status == 'Declined', 3),
            (Document.status == 'Released', 4),
            else_=5
        )
        # Ensure actionable items stay on top and Released items sink to the end
        received_pagination = received_query.order_by(status_order, Document.timestamp.desc()).paginate(
            page=page, per_page=per_page, error_out=False)
        received_documents = received_pagination.items
        created_pagination = None
        created_documents = []
    else:
        created_pagination = created_query.order_by(Document.timestamp.desc()).paginate(
            page=page, per_page=per_page, error_out=False)
        created_documents = created_pagination.items
        received_pagination = None
        received_documents = []

    for document in created_documents + received_documents:
        document.activities_json = [activity.to_dict() for activity in document.activities]

    # Prepare data for RSP view
    if view == 'rsp':
        rsp_per_page = 8
        rsp_active_tab = (request.args.get('tab') or 'ongoing').strip().lower()
        if rsp_active_tab not in {'ongoing', 'completed'}:
            rsp_active_tab = 'ongoing'
        rsp_search_query = (request.args.get('rsp_search') or '').strip()
        rsp_office_filter = (request.args.get('rsp_office') or '').strip()
        rsp_phase_filter_raw = (request.args.get('rsp_phase') or '').strip()
        rsp_phase_filter = None
        if rsp_phase_filter_raw:
            try:
                rsp_phase_filter = int(rsp_phase_filter_raw)
                if rsp_phase_filter < 1 or rsp_phase_filter > RSP_TOTAL_PHASES:
                    rsp_phase_filter = None
            except (TypeError, ValueError):
                rsp_phase_filter = None
        try:
            rsp_query = (RSPRecord.query
                         .options(selectinload(RSPRecord.phase_logs).selectinload(RSPPhaseLog.completed_by))
                         .order_by(
                             case((RSPRecord.date_posted.is_(None), 1), else_=0),
                             RSPRecord.date_posted.desc(),
                             RSPRecord.created_at.desc(),
                             RSPRecord.id.desc()
                         ))
            if rsp_search_query:
                pattern = f"%{rsp_search_query}%"
                rsp_query = rsp_query.filter(
                    or_(
                        RSPRecord.position.ilike(pattern),
                        RSPRecord.office.ilike(pattern),
                        RSPRecord.remarks.ilike(pattern)
                    )
                )
            if rsp_office_filter:
                rsp_query = rsp_query.filter(RSPRecord.office == rsp_office_filter)
            if rsp_phase_filter is not None:
                rsp_query = rsp_query.filter(RSPRecord.phase_number == rsp_phase_filter)

            # Completed state is defined by having a phase log for the final phase.
            # (Fallback: phase_number above the total phase count is also treated as completed.)
            completed_filter = or_(
                RSPRecord.phase_logs.any(RSPPhaseLog.phase_number == RSP_TOTAL_PHASES),
                RSPRecord.phase_number > RSP_TOTAL_PHASES
            )
            if rsp_active_tab == 'completed':
                rsp_query = rsp_query.filter(completed_filter)
            else:
                rsp_query = rsp_query.filter(and_(~completed_filter, RSPRecord.phase_number <= RSP_TOTAL_PHASES))
            rsp_pagination = rsp_query.paginate(page=page, per_page=rsp_per_page, error_out=False)
            rsp_records = rsp_pagination.items
        except (OperationalError, ProgrammingError) as e:
            current_app.logger.error(f"RSP view DB error: {e}")
            flash('RSP module is not initialized in the database. Please run migrations.', 'warning')
            rsp_records = []
            rsp_pagination = None
    else:
        rsp_records = []
        rsp_pagination = None
        rsp_active_tab = None
        rsp_search_query = ''
        rsp_office_filter = ''
        rsp_phase_filter = None

    # Prepare data for Leave view
    if view == 'leave':
        leave_form = LeaveRequestForm()
        leave_form.office.choices = OFFICE_CHOICES
        leave_form.leave_type.choices = LEAVE_TYPE_CHOICES

        # Initialize EWP form (for creation)
        ewp_form = EWPForm()
        ewp_form.office.choices = OFFICE_CHOICES

        start_date, end_date = _parse_date_filter(date_filter)

        try:
            leave_query = LeaveRequest.query
            if search_query:
                leave_query = leave_query.filter(
                    or_(
                        LeaveRequest.employee_name.ilike(f'%{search_query}%'),
                        LeaveRequest.office.ilike(f'%{search_query}%'),
                        LeaveRequest.leave_type.ilike(f'%{search_query}%'),
                        LeaveRequest.status.ilike(f'%{search_query}%'),
                        or_(
                            LeaveRequest.barcode.ilike(f'%{search_query}%'),
                            LeaveRequest.barcode == search_query
                        )
                    )
                )
            if start_date and end_date:
                from sqlalchemy import func
                leave_query = leave_query.filter(
                    and_(
                        func.date(LeaveRequest.created_timestamp) >= start_date,
                        func.date(LeaveRequest.created_timestamp) <= end_date
                    )
                )
            leave_query = leave_query.order_by(LeaveRequest.created_timestamp.desc())
            leave_pagination = leave_query.paginate(page=page, per_page=per_page, error_out=False)
            leave_requests = leave_pagination.items
            # Compute per-leave time-to-release visible only to the creator
            try:
                for l in leave_requests:
                    try:
                        if (getattr(l, 'released_timestamp', None) and getattr(l, 'created_timestamp', None)
                                and getattr(l, 'created_by_user_id', None) == current_user.id):
                            delta = calculate_business_hours(l.created_timestamp, l.released_timestamp)
                            l.release_delta_fmt = format_timedelta(delta)
                        else:
                            l.release_delta_fmt = None
                    except Exception:
                        l.release_delta_fmt = None
            except Exception:
                pass
        except (OperationalError, ProgrammingError) as e:
            current_app.logger.error(f"Leave view DB error: {e}")
            flash('Leave module is not initialized in the database. Please run migrations.', 'warning')
            leave_pagination = None
            leave_requests = []
 
        # EWP listing for Leave view tabbed table
        active_tab = request.args.get('tab', 'leave')
        try:
            ewp_query = EWPRecord.query
            if search_query:
                ewp_query = ewp_query.filter(
                    or_(
                        EWPRecord.employee_name.ilike(f'%{search_query}%'),
                        EWPRecord.office.ilike(f'%{search_query}%'),
                        EWPRecord.status.ilike(f'%{search_query}%'),
                        or_(
                            EWPRecord.barcode.ilike(f'%{search_query}%'),
                            EWPRecord.barcode == search_query
                        )
                    )
                )
            if start_date and end_date:
                from sqlalchemy import func
                ewp_query = ewp_query.filter(
                    and_(
                        func.date(EWPRecord.created_timestamp) >= start_date,
                        func.date(EWPRecord.created_timestamp) <= end_date
                    )
                )
            ewp_query = ewp_query.order_by(EWPRecord.created_timestamp.desc())
            ewp_pagination = ewp_query.paginate(page=page, per_page=per_page, error_out=False)
            ewp_records = ewp_pagination.items
        except (OperationalError, ProgrammingError) as e:
            current_app.logger.error(f"EWP view DB error: {e}")
            ewp_pagination = None
            ewp_records = []
    else:
        leave_form = None
        leave_pagination = None
        leave_requests = []
        ewp_form = None
        ewp_records = []
        ewp_pagination = None
        active_tab = None

    # Load release batches for Released modal (split today vs history)
    try:
        release_batches = (ReleaseBatch.query
                           .options(joinedload(ReleaseBatch.documents).joinedload(ReleaseBatchDocument.document))
                           .order_by(ReleaseBatch.release_at.desc())
                           .limit(100)
                           .all())
    except Exception as exc:
        current_app.logger.error('Unable to load release batches: %s', exc)
        release_batches = []

    def _is_today(batch_obj):
        try:
            local_rel = to_local_time(batch_obj.release_at) if batch_obj.release_at else None
            today_local = to_local_time(datetime.utcnow()).date()
            return local_rel.date() == today_local if local_rel else False
        except Exception:
            return False

    release_batches_today = [b for b in release_batches if _is_today(b)]
    release_batches_history = [b for b in release_batches if not _is_today(b)]
    release_batches_today.sort(key=lambda x: x.release_at or datetime.min, reverse=True)
    release_batches_history.sort(key=lambda x: x.release_at or datetime.min, reverse=True)

    release_batches_history_groups = []
    for batch in release_batches_history:
        try:
            local_release = to_local_time(batch.release_at) if batch.release_at else None
            month_key = local_release.strftime('%Y-%m') if local_release else 'unknown'
            month_label = local_release.strftime('%B %Y') if local_release else 'Unknown Release Month'
            day_key = local_release.strftime('%Y-%m-%d') if local_release else 'unknown'
            day_label = local_release.strftime('%b %d, %Y') if local_release else 'Unknown Release Day'
        except Exception:
            month_key = 'unknown'
            month_label = 'Unknown Release Month'
            day_key = 'unknown'
            day_label = 'Unknown Release Day'

        if release_batches_history_groups and release_batches_history_groups[-1]['key'] == month_key:
            group = release_batches_history_groups[-1]
        else:
            group = {
                'key': month_key,
                'label': month_label,
                'safe_id': month_key.replace('-', '') or 'unknown',
                'latest_release_at': batch.release_at,
                'batches': [],
                'days': [],
            }
            release_batches_history_groups.append(group)

        if group['days'] and group['days'][-1]['key'] == day_key:
            day_group = group['days'][-1]
        else:
            day_group = {
                'key': day_key,
                'label': day_label,
                'safe_id': f"{group['safe_id']}-{day_key.replace('-', '') or 'unknownday'}",
                'latest_release_at': batch.release_at,
                'batches': [],
            }
            group['days'].append(day_group)

        group['batches'].append(batch)
        day_group['batches'].append(batch)
        if batch.release_at and (group['latest_release_at'] is None or batch.release_at > group['latest_release_at']):
            group['latest_release_at'] = batch.release_at
        if batch.release_at and (day_group['latest_release_at'] is None or batch.release_at > day_group['latest_release_at']):
            day_group['latest_release_at'] = batch.release_at

    return render_template('dashboard.html',
                         title='Dashboard',
                         form=form,
                         decline_form=decline_form,
                         forward_form=forward_form,
                         batch_decline_form=batch_decline_form,
                         batch_forward_form=batch_forward_form,
                         created_documents=created_documents,
                         received_documents=received_documents,
                         created_pagination=created_pagination,
                         received_pagination=received_pagination,
                         search_query=search_query,
                         rsp_form=rsp_form,
                         rsp_records=(rsp_records if view == 'rsp' else []),
                         rsp_pagination=(rsp_pagination if view == 'rsp' else None),
                         rsp_active_tab=(rsp_active_tab if view == 'rsp' else None),
                         rsp_search_query=(rsp_search_query if view == 'rsp' else ''),
                         rsp_office_filter=(rsp_office_filter if view == 'rsp' else ''),
                         rsp_phase_filter=(rsp_phase_filter if view == 'rsp' else None),
                         rsp_total_phases=RSP_TOTAL_PHASES,
                         leave_requests=leave_requests,
                         leave_pagination=leave_pagination,
                         leave_form=leave_form,
                         ewp_form=ewp_form,
                         ewp_records=(ewp_records if view == 'leave' else []),
                         ewp_pagination=(ewp_pagination if view == 'leave' else None),
                         active_tab=(active_tab if view == 'leave' else None),
                         date_filter=date_filter,
                         release_batches=release_batches,
                         release_batches_today=release_batches_today,
                         release_batches_history=release_batches_history,
                         release_batches_history_groups=release_batches_history_groups)
