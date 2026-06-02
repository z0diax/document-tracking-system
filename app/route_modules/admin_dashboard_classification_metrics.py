from sqlalchemy import func

from app import db
from app.models import Document, LeaveRequest
from app.route_modules.shared import CLASSIFICATION_CHOICES


DOCUMENT_CLASSIFICATION_SUBTYPES = {
    'Communications': (
        'Travel Order',
        'Office Order',
        'Travel Authority',
    ),
    'Payroll': (
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
    'Request': (
        'Certificate of Employment',
        'Service Record',
        'Clearance',
    ),
    'Others': (),
}


def _query_document_class_metrics(date_filter):
    rows = db.session.query(
        Document.classification,
        db.func.count(Document.id).label('count'),
    ).filter(
        date_filter
    ).group_by(Document.classification).all()
    return {class_name: count for class_name, count in rows}


def _build_leave_summary(date_filter):
    try:
        leave_rows = db.session.query(
            LeaveRequest.leave_type,
            db.func.count(LeaveRequest.id),
        ).filter(
            date_filter
        ).group_by(LeaveRequest.leave_type).all()
        leave_subtypes = {name: int(count) for name, count in leave_rows}
    except Exception:
        leave_subtypes = {}

    try:
        leave_total = LeaveRequest.query.filter(date_filter).count()
    except Exception:
        leave_total = 0

    return leave_total, leave_subtypes


def _build_document_classification_summary(date_filter):
    summary = {}
    for classification, subtypes in DOCUMENT_CLASSIFICATION_SUBTYPES.items():
        summary[classification] = {
            'total': Document.query.filter(
                Document.classification.like(f'{classification}%'),
                date_filter,
            ).count(),
            'sub_types': {
                subtype: Document.query.filter(
                    Document.classification.like(f'{classification} - {subtype}%'),
                    date_filter,
                ).count()
                for subtype in subtypes
            },
        }
    return summary


def build_classification_breakdowns(today, first_day_of_month):
    today_document_filter = func.date(Document.timestamp) == today
    month_document_filter = func.date(Document.timestamp) >= first_day_of_month
    today_leave_filter = db.func.date(LeaveRequest.created_timestamp) == today
    month_leave_filter = db.func.date(LeaveRequest.created_timestamp) >= first_day_of_month

    today_class_metrics = _query_document_class_metrics(today_document_filter)
    monthly_class_metrics = _query_document_class_metrics(month_document_filter)

    leave_today_total, leave_today_subtypes = _build_leave_summary(today_leave_filter)
    leave_month_total, leave_month_subtypes = _build_leave_summary(month_leave_filter)

    today_class_metrics['Leave'] = today_class_metrics.get('Leave', 0) + int(leave_today_total or 0)
    monthly_class_metrics['Leave'] = monthly_class_metrics.get('Leave', 0) + int(leave_month_total or 0)

    today_classifications = _build_document_classification_summary(today_document_filter)
    today_classifications['Leave'] = {
        'total': leave_today_total,
        'sub_types': leave_today_subtypes,
    }

    monthly_classifications = _build_document_classification_summary(month_document_filter)
    monthly_classifications['Leave'] = {
        'total': leave_month_total,
        'sub_types': leave_month_subtypes,
    }

    return {
        'today_class_metrics': today_class_metrics,
        'monthly_class_metrics': monthly_class_metrics,
        'today_classifications': today_classifications,
        'monthly_classifications': monthly_classifications,
    }


def build_classification_options():
    base_classifications = [choice[0] for choice in CLASSIFICATION_CHOICES]
    try:
        dynamic_classifications = [
            row[0] for row in db.session.query(Document.classification)
            .filter(Document.classification.isnot(None))
            .distinct()
            .order_by(Document.classification)
            .all()
            if row[0]
        ]
    except Exception:
        dynamic_classifications = []
    return sorted({*base_classifications, *dynamic_classifications})
