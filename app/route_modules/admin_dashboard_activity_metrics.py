from sqlalchemy import func

from app import db
from app.models import ActivityLog, LeaveRequest


def _query_activity_metrics(date_filter):
    rows = db.session.query(
        ActivityLog.action,
        func.count(ActivityLog.id).label('count'),
    ).filter(
        date_filter
    ).group_by(
        ActivityLog.action
    ).all()
    return {action: count for action, count in rows}


def _count_leave_creations(date_filter):
    try:
        return LeaveRequest.query.filter(date_filter).count()
    except Exception:
        return 0


def build_activity_metrics(today, first_day_of_month):
    daily_metrics = _query_activity_metrics(func.date(ActivityLog.timestamp) == today)
    monthly_metrics = _query_activity_metrics(func.date(ActivityLog.timestamp) >= first_day_of_month)

    daily_metrics['Leave Created'] = daily_metrics.get('Leave Created', 0) + int(
        _count_leave_creations(db.func.date(LeaveRequest.created_timestamp) == today) or 0
    )
    monthly_metrics['Leave Created'] = monthly_metrics.get('Leave Created', 0) + int(
        _count_leave_creations(db.func.date(LeaveRequest.created_timestamp) >= first_day_of_month) or 0
    )
    return daily_metrics, monthly_metrics
