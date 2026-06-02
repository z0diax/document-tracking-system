from datetime import UTC, datetime, timedelta

from sqlalchemy import func

from app import db
from app.models import Document, LeaveRequest


DOCUMENT_STATUS_FIELDS = {
    'total_pending': 'Pending',
    'total_accepted': 'Accepted',
    'total_declined': 'Declined',
    'total_released': 'Released',
    'total_archived': 'Archived',
}

DOCUMENT_CLASSIFICATION_TOTAL_FIELDS = {
    'total_communications': 'Communications',
    'total_payroll': 'Payroll',
    'total_request': 'Request',
}

DOCUMENT_SUBTYPE_FIELDS = {
    'communications_subtypes': (
        'Communications',
        (
            'Travel Order',
            'Office Order',
            'Travel Authority',
        ),
    ),
    'payroll_subtypes': (
        'Payroll',
        (
            'Salary',
            'Voucher',
            'Trust fund',
            'Terminal Pay',
            'Overtime Pay',
            'Subsistence Allowance',
            'Travel Allowance',
            'RATA',
            'Mobile Allowance',
            'Clothing Allowance',
        ),
    ),
    'request_subtypes': (
        'Request',
        (
            'Certificate of Employment',
            'Service Record',
            'Clearance',
        ),
    ),
}

LEAVE_STATUS_FIELDS = {
    'leave_total_pending': 'Pending',
    'leave_total_forcomp': 'For Computation',
    'leave_total_forsignature': 'For Signature',
    'leave_total_released': 'Released',
}
LEAVE_STATUS_ORDER = (
    'Pending',
    'For Computation',
    'For Signature',
    'Released',
)

LEAVE_TYPE_EMPLOYEE_PAGE_SIZE = 10


def _build_document_status_metrics():
    metrics = {'total_documents': Document.query.count()}
    metrics.update({
        field_name: Document.query.filter_by(status=status).count()
        for field_name, status in DOCUMENT_STATUS_FIELDS.items()
    })
    return metrics


def _build_document_classification_metrics():
    metrics = {
        field_name: Document.query.filter_by(classification=classification).count()
        for field_name, classification in DOCUMENT_CLASSIFICATION_TOTAL_FIELDS.items()
    }

    for field_name, (classification, subtypes) in DOCUMENT_SUBTYPE_FIELDS.items():
        metrics[field_name] = {
            subtype: Document.query.filter(
                Document.classification.like(f'{classification} - {subtype}%')
            ).count()
            for subtype in subtypes
        }

    try:
        metrics['others_count'] = Document.query.filter(Document.classification.like('Others%')).count()
    except Exception:
        metrics['others_count'] = 0

    return metrics


def _safe_leave_count(status=None):
    try:
        query = LeaveRequest.query
        if status is not None:
            query = query.filter_by(status=status)
        return query.count()
    except Exception:
        return 0


def _build_leave_status_distribution(filters=None):
    counts = {status: 0 for status in LEAVE_STATUS_ORDER}
    try:
        query = db.session.query(
            LeaveRequest.status,
            db.func.count(LeaveRequest.id),
        ).filter(
            LeaveRequest.status.isnot(None)
        )
        if filters:
            query = query.filter(*filters)
        rows = query.group_by(LeaveRequest.status).all()
        for status, count in rows:
            if status in counts:
                counts[status] = int(count or 0)
    except Exception:
        pass
    return counts


def _build_leave_type_metrics(filters=None):
    try:
        query = db.session.query(
            LeaveRequest.leave_type,
            db.func.count(LeaveRequest.id),
        ).filter(
            LeaveRequest.leave_type.isnot(None)
        )
        if filters:
            query = query.filter(*filters)
        leave_type_rows = query.group_by(LeaveRequest.leave_type).all()
        leave_types_labels = [name for name, count in leave_type_rows if name]
        leave_types_counts = [int(count) for name, count in leave_type_rows if name]
    except Exception:
        leave_types_labels = []
        leave_types_counts = []

    return {
        'leave_types_labels': leave_types_labels,
        'leave_types_counts': leave_types_counts,
    }


def _build_leave_type_employee_usage(filters=None):
    usage_by_leave_type = {}
    try:
        query = db.session.query(
            LeaveRequest.leave_type,
            LeaveRequest.employee_name,
            LeaveRequest.office,
            db.func.count(LeaveRequest.id).label('request_count'),
        ).filter(
            LeaveRequest.leave_type.isnot(None),
            LeaveRequest.employee_name.isnot(None),
        )
        if filters:
            query = query.filter(*filters)
        leave_usage_rows = query.group_by(
            LeaveRequest.leave_type,
            LeaveRequest.employee_name,
            LeaveRequest.office,
        ).all()
    except Exception:
        leave_usage_rows = []

    for leave_type, employee_name, office, request_count in leave_usage_rows:
        normalized_leave_type = (leave_type or '').strip()
        normalized_employee_name = (employee_name or '').strip()
        normalized_office = (office or '').strip() or 'Unknown Office'
        count_value = int(request_count or 0)

        if not normalized_leave_type or not normalized_employee_name or count_value <= 0:
            continue

        leave_type_bucket = usage_by_leave_type.setdefault(
            normalized_leave_type,
            {
                'employees': [],
                'total_requests': 0,
                'unique_employees': 0,
            },
        )
        leave_type_bucket['employees'].append({
            'employee_name': normalized_employee_name,
            'office': normalized_office,
            'request_count': count_value,
            'chart_label': f'{normalized_employee_name} ({normalized_office})',
        })
        leave_type_bucket['total_requests'] += count_value

    for leave_type_bucket in usage_by_leave_type.values():
        leave_type_bucket['employees'].sort(
            key=lambda row: (-row['request_count'], row['employee_name'].lower(), row['office'].lower())
        )
        leave_type_bucket['unique_employees'] = len(
            {row['employee_name'].casefold() for row in leave_type_bucket['employees']}
        )

    leave_type_options = sorted(
        usage_by_leave_type.keys(),
        key=lambda leave_type: (-usage_by_leave_type[leave_type]['total_requests'], leave_type.lower()),
    )

    return {
        'leave_types': usage_by_leave_type,
        'leave_type_options': leave_type_options,
    }


def _build_leave_analytics_dataset(label, filters=None):
    status_counts = _build_leave_status_distribution(filters)
    leave_type_usage = _build_leave_type_employee_usage(filters)
    leave_type_options = leave_type_usage['leave_type_options']
    leave_type_labels = list(leave_type_options)
    leave_type_counts = [
        int(leave_type_usage['leave_types'][leave_type]['total_requests'])
        for leave_type in leave_type_options
    ]
    return {
        'label': label,
        'status_counts': status_counts,
        'type_labels': leave_type_labels,
        'type_counts': leave_type_counts,
        'leave_types': leave_type_usage['leave_types'],
        'leave_type_options': leave_type_options,
    }


def _build_leave_type_employee_year_options(today):
    years = {today.year}
    try:
        created_timestamp_rows = db.session.query(LeaveRequest.created_timestamp).filter(
            LeaveRequest.created_timestamp.isnot(None)
        ).all()
    except Exception:
        created_timestamp_rows = []

    for created_timestamp, in created_timestamp_rows:
        if created_timestamp is not None:
            years.add(created_timestamp.year)

    return sorted(years, reverse=True)


def _build_leave_type_employee_usage_metrics(today, first_day_of_month, first_day_of_year):
    year_options = _build_leave_type_employee_year_options(today)
    date_range_definitions = (
        ('all_time', 'All Time', []),
        ('this_month', 'This Month', [db.func.date(LeaveRequest.created_timestamp) >= first_day_of_month]),
        ('this_year', 'This Year', [db.func.date(LeaveRequest.created_timestamp) >= first_day_of_year]),
        ('year', 'Year', None),
    )

    usage_by_range = {}
    for value, label, filters in date_range_definitions:
        if filters is None:
            usage_by_range[value] = {
                'label': label,
                'status_counts': {status: 0 for status in LEAVE_STATUS_ORDER},
                'type_labels': [],
                'type_counts': [],
                'leave_types': {},
                'leave_type_options': [],
            }
            continue
        usage_by_range[value] = _build_leave_analytics_dataset(label, filters)

    usage_by_year = {}
    for year in year_options:
        start_of_year = datetime(year, 1, 1)
        start_of_next_year = datetime(year + 1, 1, 1)
        usage_by_year[str(year)] = _build_leave_analytics_dataset(f'Year {year}', [
            LeaveRequest.created_timestamp >= start_of_year,
            LeaveRequest.created_timestamp < start_of_next_year,
        ])

    selected_leave_type_employee_date_range = 'all_time'
    selected_leave_type_employee_year = str(year_options[0]) if year_options else str(today.year)
    selected_date_range_data = usage_by_range.get(
        selected_leave_type_employee_date_range,
        {
            'label': 'All Time',
            'status_counts': {status: 0 for status in LEAVE_STATUS_ORDER},
            'type_labels': [],
            'type_counts': [],
            'leave_types': {},
            'leave_type_options': [],
        },
    )
    selected_leave_type_employee_option = (
        selected_date_range_data['leave_type_options'][0]
        if selected_date_range_data['leave_type_options']
        else ''
    )

    return {
        'leave_type_employee_usage_by_range': usage_by_range,
        'leave_type_employee_usage_by_year': usage_by_year,
        'leave_type_employee_date_range_options': [
            {'value': value, 'label': label}
            for value, label, _filters in date_range_definitions
        ],
        'leave_type_employee_year_options': year_options,
        'leave_type_employee_page_size': LEAVE_TYPE_EMPLOYEE_PAGE_SIZE,
        'selected_leave_type_employee_date_range': selected_leave_type_employee_date_range,
        'selected_leave_type_employee_year': selected_leave_type_employee_year,
        'selected_leave_type_employee_range_label': selected_date_range_data['label'],
        'selected_leave_type_employee_options': selected_date_range_data['leave_type_options'],
        'selected_leave_type_employee_option': selected_leave_type_employee_option,
        'selected_leave_type_employee_data': selected_date_range_data['leave_types'].get(
            selected_leave_type_employee_option,
            {
                'employees': [],
                'total_requests': 0,
                'unique_employees': 0,
            },
        ),
    }


def _build_leave_overview_metrics(today, first_day_of_month, first_day_of_year):
    metrics = {'leave_total_analytics': _safe_leave_count()}
    metrics.update({
        field_name: _safe_leave_count(status)
        for field_name, status in LEAVE_STATUS_FIELDS.items()
    })
    metrics.update(_build_leave_type_metrics())
    metrics.update(_build_leave_type_employee_usage_metrics(today, first_day_of_month, first_day_of_year))
    metrics['leave_analytics_by_range'] = metrics['leave_type_employee_usage_by_range']
    metrics['leave_analytics_by_year'] = metrics['leave_type_employee_usage_by_year']
    return metrics


def build_overview_metrics(today=None, first_day_of_month=None, first_day_of_year=None):
    today = today or datetime.now(UTC).date()
    first_day_of_month = first_day_of_month or today.replace(day=1)
    first_day_of_year = first_day_of_year or today.replace(month=1, day=1)

    metrics = {}
    metrics.update(_build_document_status_metrics())
    metrics.update(_build_document_classification_metrics())
    metrics.update(_build_leave_overview_metrics(today, first_day_of_month, first_day_of_year))
    return metrics


def build_daily_document_series(first_day_of_month):
    try:
        current_month_first = first_day_of_month
        if current_month_first.month == 12:
            next_month_first = current_month_first.replace(year=current_month_first.year + 1, month=1, day=1)
        else:
            next_month_first = current_month_first.replace(month=current_month_first.month + 1, day=1)
        start_dt = datetime.combine(current_month_first, datetime.min.time())
        end_dt = datetime.combine(next_month_first, datetime.min.time())

        created_rows = db.session.query(
            func.date(Document.timestamp).label('day'),
            db.func.count(Document.id),
        ).filter(
            Document.timestamp >= start_dt,
            Document.timestamp < end_dt,
        ).group_by(func.date(Document.timestamp)).all()

        released_rows = db.session.query(
            func.date(Document.released_timestamp).label('day'),
            db.func.count(Document.id),
        ).filter(
            Document.released_timestamp != None,
            Document.released_timestamp >= start_dt,
            Document.released_timestamp < end_dt,
        ).group_by(func.date(Document.released_timestamp)).all()

        def _norm_day(day_value):
            try:
                return day_value.strftime('%Y-%m-%d')
            except Exception:
                return str(day_value)

        created_map = {_norm_day(day): int(count) for day, count in created_rows}
        released_map = {_norm_day(day): int(count) for day, count in released_rows}

        created_daily_labels = []
        created_daily_counts = []
        released_daily_counts = []
        current_day = current_month_first
        while current_day < next_month_first:
            key = current_day.strftime('%Y-%m-%d')
            created_daily_labels.append(key)
            created_daily_counts.append(created_map.get(key, 0))
            released_daily_counts.append(released_map.get(key, 0))
            current_day += timedelta(days=1)
    except Exception:
        created_daily_labels = []
        created_daily_counts = []
        released_daily_counts = []

    return created_daily_labels, created_daily_counts, released_daily_counts
