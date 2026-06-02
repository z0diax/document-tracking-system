from datetime import datetime, timedelta

from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from app import db
from app.models import Notification, SLAAlertPreference
from app.route_modules.reporting import _describe_sla_key, compute_duration_label as _compute_duration_label
from app.route_modules.shared import main


@main.route('/admin/sla-alerts', methods=['GET', 'POST'])
@login_required
def admin_sla_alerts():
    if not current_user.is_admin:
        flash('You are not authorized to view SLA alerts.', 'danger')
        return redirect(url_for('main.dashboard'))

    search_query = request.args.get('search', '').strip()

    if request.method == 'POST':
        search_query = request.form.get('search', '').strip() or search_query
        preferences_payload = {
            key: request.form.get(key) == 'on'
            for key in SLAAlertPreference.DEFAULTS.keys()
        }
        try:
            SLAAlertPreference.ensure_defaults()
            for category, enabled in preferences_payload.items():
                SLAAlertPreference.set_enabled(category, enabled)
            db.session.commit()
            flash('SLA notification preferences updated.', 'success')
        except Exception as exc:
            db.session.rollback()
            current_app.logger.exception('Failed to update SLA notification preferences: %s', exc)
            flash('Failed to update SLA notification preferences. Please try again.', 'danger')

        redirect_params = {}
        if search_query:
            redirect_params['search'] = search_query
        return redirect(url_for('main.admin_sla_alerts', **redirect_params))

    page = request.args.get('page', 1, type=int)
    per_page = 25

    base_query = Notification.query.options(joinedload(Notification.user)).filter(
        Notification.message.ilike('SLA%')
    )

    if search_query:
        pattern = f'%{search_query}%'
        base_query = base_query.filter(Notification.message.ilike(pattern))

    pagination = base_query.order_by(Notification.timestamp.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    alerts = []
    for alert in pagination.items:
        raw_message = (alert.message or '').strip()
        dedupe_key = None
        if raw_message.endswith(']') and '[' in raw_message:
            raw_message, tail = raw_message.rsplit('[', 1)
            raw_message = raw_message.strip()
            dedupe_key = tail.strip(' ]')

        severity = 'escalate' if 'SLA Escalate' in raw_message else (
            'warn' if 'SLA Warn' in raw_message else 'info'
        )

        key_info = _describe_sla_key(dedupe_key) if dedupe_key else None
        duration_label = _compute_duration_label(key_info) if key_info else None
        friendly_message = None
        if key_info and duration_label:
            status_phrase = key_info['status_label'].lower()
            friendly_message = (
                f"{key_info['severity_label']}: {key_info['entity']} "
                f"has been {status_phrase} for {duration_label}"
            )

        alerts.append({
            'id': alert.id,
            'user': alert.user,
            'message': raw_message,
            'dedupe_key': dedupe_key,
            'timestamp': alert.timestamp,
            'is_read': alert.is_read,
            'severity': severity,
            'key_info': key_info,
            'friendly_message': friendly_message,
            'duration_label': duration_label,
        })

    window_hours = 24
    window_start = datetime.utcnow() - timedelta(hours=window_hours)
    summary_query = Notification.query.filter(
        Notification.message.ilike('SLA%'),
        Notification.timestamp >= window_start
    )
    summary_total = summary_query.count()
    summary_escalations = summary_query.filter(
        Notification.message.ilike('%SLA Escalate%')
    ).count()
    summary_warnings = summary_query.filter(
        Notification.message.ilike('%SLA Warn%')
    ).count()

    try:
        sla_preferences = SLAAlertPreference.get_preferences_map()
    except Exception as exc:
        current_app.logger.warning('Unable to load SLA notification preferences: %s', exc)
        sla_preferences = SLAAlertPreference.DEFAULTS.copy()

    preference_labels = {
        'documents': 'Document Alerts',
        'leave_requests': 'Leave Alerts',
        'ewp_records': 'EWP Alerts',
    }

    return render_template(
        'admin_sla_alerts.html',
        alerts=alerts,
        pagination=pagination,
        search_query=search_query,
        sla_preferences=sla_preferences,
        sla_preference_labels=preference_labels,
        summary={
            'total': summary_total,
            'escalations': summary_escalations,
            'warnings': summary_warnings,
            'window_hours': window_hours
        }
    )
