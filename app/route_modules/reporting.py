from datetime import datetime, timedelta

from flask import flash, jsonify, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from app import db
from app.models import (
    Document,
    EWPRecord,
    LeaveRequest,
    ProcessingLog,
    User,
    format_timedelta,
    to_local_time,
)
from app.route_modules.shared import main
from app.sla_monitor import _elapsed_hours, _format_elapsed_duration, _resolve_document_anchor
from app.utils import calculate_business_hours


def _parse_iso_date(raw_value):
    try:
        return datetime.strptime(raw_value, '%Y-%m-%d')
    except Exception:
        return None


def _month_bounds(year, month, fallback=None):
    fallback = fallback or datetime.utcnow()
    try:
        start_dt = datetime(year, month, 1)
    except Exception:
        start_dt = datetime(fallback.year, fallback.month, 1)
        year = start_dt.year
        month = start_dt.month

    if month == 12:
        end_dt = datetime(year + 1, 1, 1)
    else:
        end_dt = datetime(year, month + 1, 1)
    return start_dt, end_dt


def _format_local_datetime(dt_value):
    if not dt_value:
        return 'Not available'
    try:
        return to_local_time(dt_value).strftime('%B %d, %Y at %I:%M %p')
    except Exception:
        return 'Not available'


def _format_leave_requested_dates(leave):
    try:
        date_ranges = getattr(leave, 'date_ranges', None) or []
        if date_ranges:
            formatted_ranges = []
            for date_range in date_ranges:
                if not date_range.start_date:
                    continue
                start_label = date_range.start_date.strftime('%b %d, %Y')
                end_label = (
                    date_range.end_date.strftime('%b %d, %Y')
                    if date_range.end_date and date_range.end_date != date_range.start_date
                    else start_label
                )
                if start_label == end_label:
                    formatted_ranges.append(start_label)
                else:
                    formatted_ranges.append(f'{start_label} to {end_label}')
            if formatted_ranges:
                return '; '.join(formatted_ranges)
    except Exception:
        pass

    if getattr(leave, 'start_date', None):
        start_label = leave.start_date.strftime('%b %d, %Y')
        end_value = getattr(leave, 'end_date', None) or leave.start_date
        end_label = end_value.strftime('%b %d, %Y')
        return start_label if start_label == end_label else f'{start_label} to {end_label}'
    return 'Not available'


def _resolve_leave_drilldown_range(now, date_range, selected_year):
    normalized_range = (date_range or 'all_time').strip().lower()
    if normalized_range == 'this_month':
        start_dt, end_dt = _month_bounds(now.year, now.month, fallback=now)
        return normalized_range, 'This Month', start_dt, end_dt
    if normalized_range == 'this_year':
        start_dt = datetime(now.year, 1, 1)
        end_dt = datetime(now.year + 1, 1, 1)
        return normalized_range, 'This Year', start_dt, end_dt
    if normalized_range == 'year':
        try:
            year_value = int(selected_year)
        except (TypeError, ValueError):
            year_value = now.year
        start_dt = datetime(year_value, 1, 1)
        end_dt = datetime(year_value + 1, 1, 1)
        return normalized_range, f'Year {year_value}', start_dt, end_dt
    return 'all_time', 'All Time', None, None


def _describe_sla_key(dedupe_key):
    if not dedupe_key:
        return None
    parts = dedupe_key.split(':')
    if len(parts) < 3:
        return {'raw': dedupe_key}

    entity_raw, status_raw, severity_raw = parts[0], parts[1], parts[2]

    entity_type = entity_raw
    entity_id = None
    entity_label = entity_raw
    if '#' in entity_raw:
        entity_type, id_part = entity_raw.split('#', 1)
        entity_label = f'{entity_type} #{id_part}'
        try:
            entity_id = int(id_part)
        except (TypeError, ValueError):
            entity_id = None

    status_label = status_raw.replace('_', ' ').title()
    severity_label = 'Escalation' if severity_raw.lower() == 'escalate' else severity_raw.title()

    return {
        'raw': dedupe_key,
        'entity': entity_label,
        'entity_type': entity_type,
        'entity_id': entity_id,
        'status_value': status_raw,
        'status_label': status_label,
        'severity_value': severity_raw,
        'severity_label': severity_label,
    }


def compute_duration_label(key_info):
    if not key_info:
        return None

    entity_type = key_info.get('entity_type')
    entity_id = key_info.get('entity_id')
    if not entity_type or entity_id is None:
        return None

    now = datetime.utcnow()

    try:
        if entity_type == 'Document':
            document = Document.query.get(entity_id)
            if not document:
                return None
            anchor = _resolve_document_anchor(document) or document.timestamp
            if not anchor:
                return None
            hours = _elapsed_hours(anchor, now, use_business_hours=True)
            return _format_elapsed_duration(hours, True)
        if entity_type == 'LeaveRequest':
            leave = LeaveRequest.query.get(entity_id)
            if not leave or not leave.created_timestamp:
                return None
            hours = _elapsed_hours(leave.created_timestamp, now, use_business_hours=False)
            return _format_elapsed_duration(hours, False)
        if entity_type == 'EWPRecord':
            record = EWPRecord.query.get(entity_id)
            if not record or not record.created_timestamp:
                return None
            hours = _elapsed_hours(record.created_timestamp, now, use_business_hours=False)
            return _format_elapsed_duration(hours, False)
    except Exception:
        return None

    return None


@main.route('/admin/leave-analytics/drilldown')
@login_required
def admin_leave_analytics_drilldown():
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    metric = (request.args.get('metric') or '').strip().lower()
    value = (request.args.get('value') or '').strip()
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = request.args.get('per_page', 10, type=int) or 10
    per_page = min(max(per_page, 1), 50)

    if metric not in {'status', 'type'} or not value:
        return jsonify({'success': False, 'error': 'Invalid drill-down parameters'}), 400

    now = datetime.utcnow()
    _normalized_range, range_label, start_dt, end_dt = _resolve_leave_drilldown_range(
        now,
        request.args.get('date_range'),
        request.args.get('year'),
    )

    try:
        query = LeaveRequest.query.options(
            joinedload(LeaveRequest.created_by),
            joinedload(LeaveRequest.date_ranges),
        )

        if metric == 'status':
            query = query.filter(LeaveRequest.status == value)
            title = f'Leave Requests with Status: {value}'
            metric_label = 'Status'
        else:
            query = query.filter(LeaveRequest.leave_type == value)
            title = f'Leave Requests with Type: {value}'
            metric_label = 'Leave Type'

        if start_dt is not None and end_dt is not None:
            query = query.filter(
                LeaveRequest.created_timestamp >= start_dt,
                LeaveRequest.created_timestamp < end_dt,
            )

        pagination = query.order_by(LeaveRequest.created_timestamp.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False,
        )

        records = []
        for leave in pagination.items:
            records.append({
                'id': leave.id,
                'barcode': leave.barcode or '',
                'employee_name': leave.employee_name or 'Unknown Employee',
                'office': leave.office or 'Unknown Office',
                'leave_type': leave.leave_type or 'Unknown Type',
                'status': leave.status or 'Unknown Status',
                'requested_dates': _format_leave_requested_dates(leave),
                'created_timestamp': _format_local_datetime(leave.created_timestamp),
                'released_timestamp': (
                    _format_local_datetime(leave.released_timestamp)
                    if leave.released_timestamp
                    else 'Not released'
                ),
                'created_by': leave.created_by.username if leave.created_by else 'Unknown',
            })

        return jsonify({
            'success': True,
            'title': title,
            'metric': metric,
            'metric_label': metric_label,
            'value': value,
            'range_label': range_label,
            'records': records,
            'page': pagination.page,
            'pages': pagination.pages,
            'total': pagination.total,
            'per_page': per_page,
            'has_prev': pagination.has_prev,
            'has_next': pagination.has_next,
            'prev_num': pagination.prev_num,
            'next_num': pagination.next_num,
        })
    except Exception as exc:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(exc)}), 500


@main.route('/archive')
@login_required
def archive():
    month = request.args.get('month', '')
    year = request.args.get('year', '')
    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)

    start_dt = None
    end_dt = None

    if month and year:
        try:
            month_int = int(month)
            year_int = int(year)
            start_dt, end_dt = _month_bounds(year_int, month_int)
        except Exception:
            start_dt = None
            end_dt = None
    elif year:
        try:
            year_int = int(year)
            start_dt = datetime(year_int, 1, 1)
            end_dt = datetime(year_int + 1, 1, 1)
        except Exception:
            start_dt = None
            end_dt = None

    query = Document.query.filter(
        (Document.status == 'Archived') &
        ((Document.creator == current_user) | (Document.recipient == current_user))
    )

    if search:
        query = query.filter(
            or_(
                Document.title.ilike(f'%{search}%'),
                Document.office.ilike(f'%{search}%'),
                Document.classification.ilike(f'%{search}%'),
                Document.status.ilike(f'%{search}%'),
                or_(
                    Document.barcode.ilike(f'%{search}%'),
                    Document.barcode == search,
                ),
            )
        )

    if start_dt is not None and end_dt is not None:
        query = query.filter(
            Document.timestamp >= start_dt,
            Document.timestamp < end_dt,
        )

    paginated_documents = query.order_by(Document.timestamp.desc()).paginate(
        page=page,
        per_page=10,
        error_out=False,
    )

    years_query = db.session.query(
        db.func.year(Document.timestamp).label('year')
    ).filter(
        Document.status == 'Archived',
        (Document.creator_id == current_user.id) | (Document.recipient_id == current_user.id),
    ).distinct().order_by(
        db.func.year(Document.timestamp).desc()
    )

    try:
        years = [int(year_row[0]) for year_row in years_query.all() if year_row[0]]
    except (TypeError, ValueError):
        current_year = datetime.now().year
        years = list(range(current_year, current_year - 5, -1))

    for document in paginated_documents.items:
        document.activities_json = [activity.to_dict() for activity in document.activities]

    return render_template(
        'archive.html',
        title='Archive',
        archived_documents=paginated_documents.items,
        pagination=paginated_documents,
        years=years,
        current_month=month,
        current_year=year,
        search=search,
    )


@main.route('/profile/activity_data', methods=['GET'])
@login_required
def profile_activity_data():
    try:
        now = datetime.utcnow()
        month = request.args.get('month', type=int) or now.month
        year = request.args.get('year', type=int) or now.year
        month_start, month_end = _month_bounds(year, month, fallback=now)

        doc_created_rows = db.session.query(
            func.date(Document.timestamp).label('day'),
            db.func.count(Document.id),
        ).filter(
            Document.creator_id == current_user.id,
            Document.timestamp >= month_start,
            Document.timestamp < month_end,
        ).group_by(func.date(Document.timestamp)).all()

        doc_released_rows = db.session.query(
            func.date(Document.released_timestamp).label('day'),
            db.func.count(Document.id),
        ).filter(
            Document.recipient_id == current_user.id,
            Document.released_timestamp != None,
            Document.released_timestamp >= month_start,
            Document.released_timestamp < month_end,
        ).group_by(func.date(Document.released_timestamp)).all()

        leave_created_rows = db.session.query(
            func.date(LeaveRequest.created_timestamp).label('day'),
            db.func.count(LeaveRequest.id),
        ).filter(
            LeaveRequest.created_by_user_id == current_user.id,
            LeaveRequest.created_timestamp >= month_start,
            LeaveRequest.created_timestamp < month_end,
        ).group_by(func.date(LeaveRequest.created_timestamp)).all()

        leave_released_rows = db.session.query(
            func.date(LeaveRequest.released_timestamp).label('day'),
            db.func.count(LeaveRequest.id),
        ).filter(
            LeaveRequest.created_by_user_id == current_user.id,
            LeaveRequest.released_timestamp != None,
            LeaveRequest.released_timestamp >= month_start,
            LeaveRequest.released_timestamp < month_end,
        ).group_by(func.date(LeaveRequest.released_timestamp)).all()

        def _norm_day(day_value):
            try:
                return day_value.strftime('%Y-%m-%d')
            except Exception:
                return str(day_value)

        doc_created_map = {_norm_day(day): int(count) for day, count in doc_created_rows}
        doc_released_map = {_norm_day(day): int(count) for day, count in doc_released_rows}
        leave_created_map = {_norm_day(day): int(count) for day, count in leave_created_rows}
        leave_released_map = {_norm_day(day): int(count) for day, count in leave_released_rows}

        labels = []
        doc_created = []
        doc_released = []
        leave_created = []
        leave_released = []
        current_day = month_start
        while current_day < month_end:
            key = current_day.strftime('%Y-%m-%d')
            labels.append(key)
            doc_created.append(doc_created_map.get(key, 0))
            doc_released.append(doc_released_map.get(key, 0))
            leave_created.append(leave_created_map.get(key, 0))
            leave_released.append(leave_released_map.get(key, 0))
            current_day += timedelta(days=1)

        return jsonify({
            'success': True,
            'labels': labels,
            'doc_created': doc_created,
            'doc_released': doc_released,
            'leave_created': leave_created,
            'leave_released': leave_released,
            'month': month,
            'year': year,
        })
    except Exception as exc:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(exc)}), 500


@main.route('/admin/print_text_report')
@login_required
def print_text_report():
    if not current_user.is_admin:
        flash('You are not authorized to access the admin report.', 'danger')
        return redirect(url_for('main.dashboard'))

    now = datetime.utcnow()
    include_details = request.args.get('include_details', default=1, type=int)
    autoprint = request.args.get('autoprint', default=1, type=int)
    fmt = (request.args.get('format', default='html') or 'html').lower()
    date_from_str = (request.args.get('date_from') or '').strip()
    date_to_str = (request.args.get('date_to') or '').strip()

    if date_from_str and not date_to_str:
        date_to_str = date_from_str
    if date_to_str and not date_from_str:
        date_from_str = date_to_str

    start_dt = None
    end_dt = None
    if date_from_str and date_to_str:
        date_from_value = _parse_iso_date(date_from_str)
        date_to_value = _parse_iso_date(date_to_str)
        if date_from_value and date_to_value:
            start_dt = datetime(date_from_value.year, date_from_value.month, date_from_value.day)
            end_dt = datetime(date_to_value.year, date_to_value.month, date_to_value.day) + timedelta(days=1)
        else:
            date_from_str = ''
            date_to_str = ''

    if start_dt is None or end_dt is None:
        month = request.args.get('month', type=int) or now.month
        year = request.args.get('year', type=int) or now.year
        start_dt, end_dt = _month_bounds(year, month, fallback=now)
        date_from_str = start_dt.date().isoformat()
        date_to_str = (end_dt - timedelta(days=1)).date().isoformat()

    documents_month_q = Document.query.filter(
        Document.timestamp >= start_dt,
        Document.timestamp < end_dt,
    )
    documents_created_this_month = documents_month_q.count()

    def count_class(prefix):
        return Document.query.filter(
            Document.classification.like(f'{prefix}%'),
            Document.timestamp >= start_dt,
            Document.timestamp < end_dt,
        ).count()

    try:
        leave_created_in_period = LeaveRequest.query.filter(
            LeaveRequest.created_timestamp >= start_dt,
            LeaveRequest.created_timestamp < end_dt,
        ).count()
    except Exception:
        leave_created_in_period = 0

    per_classification_counts = {
        'Communications': count_class('Communications'),
        'Payroll': count_class('Payroll'),
        'Request': count_class('Request'),
        'Others': count_class('Others'),
        'Leave': int(leave_created_in_period or 0),
    }

    classification_buckets = {
        'Communications': {'count': 0, 'total_sec': 0},
        'Payroll': {'count': 0, 'total_sec': 0},
        'Request': {'count': 0, 'total_sec': 0},
        'Others': {'count': 0, 'total_sec': 0},
        'Leave': {'count': 0, 'total_sec': 0},
    }
    classification_sub_buckets = {
        'Communications': {},
        'Payroll': {},
        'Request': {},
        'Others': {},
        'Leave': {},
    }

    docs_rel = Document.query.with_entities(
        Document.classification,
        Document.timestamp,
        Document.released_timestamp,
    ).filter(
        Document.released_timestamp != None,
        Document.released_timestamp >= start_dt,
        Document.released_timestamp < end_dt,
    ).all()

    for classification, created_at, released_at in docs_rel:
        if not created_at or not released_at:
            continue

        main = 'Others'
        try:
            if isinstance(classification, str):
                if classification.startswith('Communications'):
                    main = 'Communications'
                elif classification.startswith('Payroll'):
                    main = 'Payroll'
                elif classification.startswith('Request'):
                    main = 'Request'
        except Exception:
            main = 'Others'

        try:
            delta_td = calculate_business_hours(created_at, released_at)
        except Exception:
            delta_td = released_at - created_at

        try:
            seconds = int(delta_td.total_seconds()) if delta_td else 0
        except Exception:
            seconds = 0
        if seconds < 0:
            seconds = 0

        classification_buckets[main]['count'] += 1
        classification_buckets[main]['total_sec'] += seconds

        sub_name = classification
        try:
            if isinstance(classification, str):
                prefix = main + ' - '
                if classification.startswith(prefix):
                    sub_name = classification[len(prefix):].strip() or 'General'
                elif classification == main:
                    sub_name = 'General'
        except Exception:
            sub_name = 'General'

        sub_entry = classification_sub_buckets.setdefault(main, {}).get(sub_name)
        if not sub_entry:
            sub_entry = {'count': 0, 'total_sec': 0}
            classification_sub_buckets[main][sub_name] = sub_entry
        sub_entry['count'] += 1
        sub_entry['total_sec'] += seconds

    try:
        leaves_rel = LeaveRequest.query.with_entities(
            LeaveRequest.leave_type,
            LeaveRequest.created_timestamp,
            LeaveRequest.released_timestamp,
        ).filter(
            LeaveRequest.released_timestamp != None,
            LeaveRequest.released_timestamp >= start_dt,
            LeaveRequest.released_timestamp < end_dt,
        ).all()
    except Exception:
        leaves_rel = []

    for leave_type, created_ts, released_ts in leaves_rel:
        if not created_ts or not released_ts:
            continue

        try:
            delta_td = calculate_business_hours(created_ts, released_ts)
        except Exception:
            delta_td = released_ts - created_ts

        try:
            seconds = int(delta_td.total_seconds()) if delta_td else 0
        except Exception:
            seconds = 0
        if seconds < 0:
            seconds = 0

        classification_buckets['Leave']['count'] += 1
        classification_buckets['Leave']['total_sec'] += seconds

        subtype = leave_type or 'General'
        sub_entry = classification_sub_buckets.setdefault('Leave', {}).get(subtype)
        if not sub_entry:
            sub_entry = {'count': 0, 'total_sec': 0}
            classification_sub_buckets['Leave'][subtype] = sub_entry
        sub_entry['count'] += 1
        sub_entry['total_sec'] += seconds

    classification_processing = []
    classification_sub_processing = []
    for key in ['Communications', 'Payroll', 'Request', 'Others', 'Leave']:
        count = classification_buckets[key]['count']
        total_seconds = classification_buckets[key]['total_sec']
        avg_sec = int(total_seconds / count) if count > 0 else 0
        if count > 0:
            try:
                avg_formatted = format_timedelta(timedelta(seconds=avg_sec))
            except Exception:
                avg_formatted = str(timedelta(seconds=avg_sec))
        else:
            avg_formatted = 'No document processed yet'

        classification_processing.append({
            'classification': key,
            'count': count,
            'avg_sec': avg_sec,
            'avg_formatted': avg_formatted,
        })

        rows = []
        submap = classification_sub_buckets.get(key, {})
        if submap:
            for sub_name in sorted(submap.keys()):
                sub_count = submap[sub_name]['count']
                sub_total_seconds = submap[sub_name]['total_sec']
                sub_avg_sec = int(sub_total_seconds / sub_count) if sub_count > 0 else 0
                sub_avg_formatted = format_timedelta(timedelta(seconds=sub_avg_sec)) if sub_count > 0 else 'No document processed yet'
                rows.append({
                    'sub': sub_name,
                    'count': sub_count,
                    'avg_sec': sub_avg_sec,
                    'avg_formatted': sub_avg_formatted,
                })
        else:
            rows.append({
                'sub': '-',
                'count': 0,
                'avg_sec': 0,
                'avg_formatted': 'No document processed yet',
            })

        classification_sub_processing.append({
            'classification': key,
            'rows': rows,
        })

    def get_rankings(base_filters):
        avg_expr = db.func.avg(
            db.func.time_to_sec(
                db.func.timediff(ProcessingLog.forwarded_timestamp, ProcessingLog.accepted_timestamp)
            )
        ).label('avg_sec')

        query = db.session.query(
            User.username.label('username'),
            avg_expr,
            db.func.count(ProcessingLog.id).label('count'),
        ).join(
            User,
            User.id == ProcessingLog.user_id,
        ).filter(
            ProcessingLog.forwarded_timestamp != None
        )

        if base_filters:
            query = query.filter(*base_filters)

        query = query.group_by(User.username).having(db.func.count(ProcessingLog.id) > 0)
        best = query.order_by(db.asc(db.text('avg_sec'))).first()
        worst = query.order_by(db.desc(db.text('avg_sec'))).first()

        def normalize(row):
            if not row or row.avg_sec is None:
                return None
            try:
                seconds = int(row.avg_sec) if row.avg_sec is not None else 0
            except Exception:
                seconds = 0
            return {
                'username': row.username,
                'avg_sec': seconds,
                'avg_formatted': format_timedelta(timedelta(seconds=seconds)),
                'count': int(row.count) if getattr(row, 'count', None) is not None else 0,
            }

        return normalize(best), normalize(worst)

    monthly_best, monthly_worst = get_rankings([
        ProcessingLog.forwarded_timestamp >= start_dt,
        ProcessingLog.forwarded_timestamp < end_dt,
    ])
    overall_best, overall_worst = get_rankings([])

    user_performance = []
    leave_user_metrics_period = []
    try:
        processing_logs = ProcessingLog.query.filter(
            ProcessingLog.forwarded_timestamp != None,
            ProcessingLog.accepted_timestamp != None,
            ProcessingLog.forwarded_timestamp >= start_dt,
            ProcessingLog.forwarded_timestamp < end_dt,
        ).all()

        handled_map = {}
        for log in processing_logs:
            user_id = log.user_id
            if not user_id:
                continue
            seconds = 0
            try:
                if log.forwarded_timestamp and log.accepted_timestamp:
                    seconds = int((log.forwarded_timestamp - log.accepted_timestamp).total_seconds())
            except Exception:
                seconds = 0
            if seconds < 0:
                seconds = 0
            entry = handled_map.setdefault(user_id, {'handled': 0, 'total_sec': 0})
            entry['handled'] += 1
            entry['total_sec'] += seconds

        created_rows = Document.query.with_entities(Document.creator_id).filter(
            Document.timestamp >= start_dt,
            Document.timestamp < end_dt,
        ).all()
        created_map = {}
        for (creator_id,) in created_rows:
            if creator_id:
                created_map[creator_id] = created_map.get(creator_id, 0) + 1

        all_user_ids = set(created_map.keys()) | set(handled_map.keys())
        if all_user_ids:
            user_rows = db.session.query(User.id, User.username).filter(User.id.in_(all_user_ids)).all()
            usernames = {user_id: username for user_id, username in user_rows}
            for user_id in all_user_ids:
                created = int(created_map.get(user_id, 0))
                handled = handled_map.get(user_id, {'handled': 0, 'total_sec': 0})
                handled_count = int(handled['handled'])
                if created > 0 or handled_count > 0:
                    avg_sec = int(handled['total_sec'] / handled_count) if handled_count > 0 else 0
                    user_performance.append({
                        'username': usernames.get(user_id, f'User {user_id}'),
                        'documents_created': created,
                        'documents_handled': handled_count,
                        'avg_sec': avg_sec,
                        'avg_formatted': format_timedelta(timedelta(seconds=avg_sec)),
                    })
            user_performance.sort(key=lambda row: row['username'].lower() if isinstance(row['username'], str) else str(row['username']).lower())

        try:
            leave_rows = LeaveRequest.query.with_entities(
                LeaveRequest.created_by_user_id,
                LeaveRequest.created_timestamp,
                LeaveRequest.released_timestamp,
            ).filter(
                LeaveRequest.created_by_user_id != None,
                LeaveRequest.released_timestamp != None,
                LeaveRequest.released_timestamp >= start_dt,
                LeaveRequest.released_timestamp < end_dt,
            ).all()
        except Exception:
            leave_rows = []

        leave_aggregates = {}
        for user_id, created_ts, released_ts in leave_rows:
            if not user_id or not created_ts or not released_ts:
                continue
            try:
                delta_td = calculate_business_hours(created_ts, released_ts)
            except Exception:
                delta_td = released_ts - created_ts
            try:
                seconds = int(delta_td.total_seconds()) if delta_td else 0
            except Exception:
                seconds = 0
            if seconds < 0:
                seconds = 0
            entry = leave_aggregates.setdefault(user_id, {'count': 0, 'total_sec': 0})
            entry['count'] += 1
            entry['total_sec'] += seconds

        if leave_aggregates:
            leave_user_rows = db.session.query(User.id, User.username).filter(User.id.in_(list(leave_aggregates.keys()))).all()
            usernames = {user_id: username for user_id, username in leave_user_rows}
            for user_id, data in leave_aggregates.items():
                count = int(data['count'])
                avg_sec = int(data['total_sec'] / count) if count > 0 else 0
                leave_user_metrics_period.append({
                    'username': usernames.get(user_id, f'User {user_id}'),
                    'leaves_released': count,
                    'avg_sec': avg_sec,
                    'avg_formatted': format_timedelta(timedelta(seconds=avg_sec)),
                })
            leave_user_metrics_period.sort(key=lambda row: row['username'].lower() if isinstance(row['username'], str) else str(row['username']).lower())
    except Exception:
        user_performance = []
        leave_user_metrics_period = []

    documents_list = []
    truncated = False
    cap = 200
    if include_details:
        docs_q = documents_month_q.options(
            joinedload(Document.creator),
            joinedload(Document.recipient),
        ).order_by(Document.timestamp.desc())
        total = docs_q.count()
        if total > cap:
            truncated = True
        for document in docs_q.limit(cap).all():
            documents_list.append({
                'title': document.title,
                'office': document.office,
                'classification': document.classification,
                'creator': document.creator.username if document.creator else 'Unknown',
                'created_at': to_local_time(document.timestamp) if document.timestamp else None,
                'status': document.status,
                'barcode': document.barcode or '',
            })

    if fmt == 'txt':
        try:
            start_fmt_txt = to_local_time(start_dt).strftime('%B %d, %Y') if start_dt else ''
        except Exception:
            start_fmt_txt = start_dt.strftime('%B %d, %Y') if start_dt else ''
        try:
            end_inclusive_txt = end_dt - timedelta(days=1) if end_dt else None
            end_fmt_txt = to_local_time(end_inclusive_txt).strftime('%B %d, %Y') if end_inclusive_txt else ''
        except Exception:
            end_fmt_txt = end_inclusive_txt.strftime('%B %d, %Y') if end_inclusive_txt else ''

        if date_from_str and date_to_str:
            period_label = start_fmt_txt if date_from_str == date_to_str else f'{start_fmt_txt} to {end_fmt_txt}'
        else:
            period_label = to_local_time(start_dt).strftime('%B %Y') if start_dt else 'Selected Period'

        generated_ts = to_local_time(datetime.utcnow()).strftime('%Y-%m-%d %H:%M:%S')
        lines = [
            f'System Activity Report - {period_label}',
            f'Generated: {generated_ts}',
            '',
            'Summary',
            '-------',
            f'Documents created in period: {documents_created_this_month}',
            'Per-Classification counts (selected period):',
        ]
        for key, value in per_classification_counts.items():
            lines.append(f'  - {key}: {value}')
        lines.extend([
            '',
            f'Processing Time by Classification and Sub-types ({period_label})',
            '------------------------------------------------------',
        ])
        for group in classification_sub_processing:
            lines.append(f'  {group["classification"]}:')
            for row in group['rows']:
                lines.append(f'    - {row["sub"]}: count {row["count"]}, avg {row["avg_formatted"]}')
        lines.extend([
            '',
            'Rankings (Selected Period)',
            '--------------------------',
            f'  Top performer: {monthly_best["username"]} - {monthly_best["avg_formatted"]} (avg, {monthly_best["count"]} handled)' if monthly_best else '  Top performer: N/A',
            f'  Longest processing: {monthly_worst["username"]} - {monthly_worst["avg_formatted"]} (avg, {monthly_worst["count"]} handled)' if monthly_worst else '  Longest processing: N/A',
            '',
            'Rankings (Overall)',
            '------------------',
            f'  Top performer: {overall_best["username"]} - {overall_best["avg_formatted"]} (avg, {overall_best["count"]} handled)' if overall_best else '  Top performer: N/A',
            f'  Longest processing: {overall_worst["username"]} - {overall_worst["avg_formatted"]} (avg, {overall_worst["count"]} handled)' if overall_worst else '  Longest processing: N/A',
            '',
            'User Performance (Selected Period)',
            '----------------------------------',
        ])
        if user_performance:
            for row in user_performance:
                lines.append(f'  - {row["username"]}: created {row["documents_created"]}, handled {row["documents_handled"]}, avg {row["avg_formatted"]}')
        else:
            lines.append('  No user activity found.')
        lines.extend([
            '',
            'Leave User Performance (Selected Period)',
            '---------------------------------------',
        ])
        if leave_user_metrics_period:
            for row in leave_user_metrics_period:
                lines.append(f'  - {row["username"]}: released {row["leaves_released"]}, avg {row["avg_formatted"]}')
        else:
            lines.append('  No leave processing data found.')
        lines.append('')
        if include_details:
            lines.extend([
                'Documents Created This Month',
                '----------------------------',
            ])
            if not documents_list:
                lines.append('  No documents found.')
            else:
                for document in documents_list:
                    created_str = document['created_at'].strftime('%Y-%m-%d %H:%M') if document['created_at'] else 'N/A'
                    lines.append(f'  * {document["title"]} | {document["office"]} | {document["classification"]} | by {document["creator"]} | {created_str} | {document["status"]} | {document["barcode"]}')
                if truncated:
                    lines.extend([
                        '',
                        f'  Note: List truncated to {cap} items. Use include_details=1 and filter by month/year or export via database for full list.',
                    ])
        response = make_response('\n'.join(lines), 200)
        response.mimetype = 'text/plain; charset=utf-8'
        return response

    from_fmt = ''
    to_fmt = ''
    if start_dt:
        try:
            from_fmt = to_local_time(start_dt).strftime('%B %d, %Y')
        except Exception:
            from_fmt = start_dt.strftime('%B %d, %Y')
    if end_dt:
        try:
            end_inclusive = end_dt - timedelta(days=1)
            to_fmt = to_local_time(end_inclusive).strftime('%B %d, %Y')
        except Exception:
            to_fmt = (end_dt - timedelta(days=1)).strftime('%B %d, %Y')
    else:
        to_fmt = from_fmt

    if date_from_str and date_to_str:
        period_label = from_fmt if date_from_str == date_to_str else f'{from_fmt} to {to_fmt}'
    else:
        period_label = to_local_time(start_dt).strftime('%B %Y') if start_dt else 'Selected Period'

    return render_template(
        'report_text.html',
        title='System Activity Report',
        selected_from=date_from_str,
        selected_to=date_to_str,
        selected_from_fmt=from_fmt,
        selected_to_fmt=to_fmt,
        period_label=period_label,
        autoprint=bool(autoprint),
        include_details=bool(include_details),
        documents_created_this_month=documents_created_this_month,
        per_classification_counts=per_classification_counts,
        monthly_best=monthly_best,
        monthly_worst=monthly_worst,
        overall_best=overall_best,
        overall_worst=overall_worst,
        documents_list=documents_list,
        truncated=truncated,
        cap=cap,
        generated_at=to_local_time(datetime.utcnow()),
        user_performance=user_performance,
        leave_user_metrics_period=leave_user_metrics_period,
        classification_processing=classification_processing,
        classification_sub_processing=classification_sub_processing,
    )


__all__ = ['_describe_sla_key', 'archive', 'compute_duration_label', 'print_text_report', 'profile_activity_data']
