from datetime import UTC, datetime

from flask import render_template

from app.models import format_timedelta
from app.route_modules.admin_dashboard_classification_metrics import (
    build_classification_breakdowns,
    build_classification_options,
)
from app.route_modules.admin_dashboard_lists import paginate_admin_lists
from app.route_modules.admin_dashboard_overview_metrics import (
    build_daily_document_series,
    build_overview_metrics,
)
from app.route_modules.admin_dashboard_activity_metrics import build_activity_metrics
from app.route_modules.admin_dashboard_release_metrics import (
    build_pending_metrics,
    build_release_metrics,
)
from app.route_modules.admin_dashboard_user_performance_metrics import build_user_metrics


MONTH_OPTIONS = [
    (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
    (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
    (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December'),
]


def _build_list_context(doc_page, activity_page, user_page, search_query):
    paginated_documents, paginated_activities, users_pagination = paginate_admin_lists(
        doc_page,
        activity_page,
        user_page,
        search_query,
    )
    return {
        'documents': paginated_documents.items,
        'doc_pagination': paginated_documents,
        'activities': paginated_activities.items,
        'recent_activities': paginated_activities.items,
        'pagination': paginated_activities,
        'activity_pagination': paginated_activities,
        'users': users_pagination.items,
        'users_pagination': users_pagination,
        'search_query': search_query,
    }


def _build_activity_context(today, first_day_of_month):
    daily_metrics, monthly_metrics = build_activity_metrics(today, first_day_of_month)
    created_daily_labels, created_daily_counts, released_daily_counts = build_daily_document_series(first_day_of_month)
    return {
        'daily_metrics': daily_metrics,
        'monthly_metrics': monthly_metrics,
        'created_daily_labels': created_daily_labels,
        'created_daily_counts': created_daily_counts,
        'released_daily_counts': released_daily_counts,
    }


def _build_performance_context():
    average_release_time, release_metrics = build_release_metrics()
    pending_documents, pending_docs_info = build_pending_metrics()
    user_metrics, leave_user_metrics = build_user_metrics()
    return {
        'average_release_time': average_release_time,
        'pending_documents': pending_documents,
        'pending_docs_info': pending_docs_info,
        'release_metrics': release_metrics,
        'user_metrics': user_metrics,
        'leave_user_metrics': leave_user_metrics,
    }


def render_admin_dashboard(doc_page, activity_page, user_page, search_query):
    today = datetime.now(UTC).date()
    first_day_of_month = today.replace(day=1)
    first_day_of_year = today.replace(month=1, day=1)

    template_context = {
        'title': 'Admin Dashboard',
        'format_timedelta': format_timedelta,
        'classification_options': build_classification_options(),
        'month_options': MONTH_OPTIONS,
        'year_options': list(range(today.year, today.year - 6, -1)),
    }
    template_context.update(_build_list_context(doc_page, activity_page, user_page, search_query))
    template_context.update(build_overview_metrics(today, first_day_of_month, first_day_of_year))
    template_context.update(build_classification_breakdowns(today, first_day_of_month))
    template_context.update(_build_activity_context(today, first_day_of_month))
    template_context.update(_build_performance_context())

    return render_template('admin_dashboard.html', **template_context)
