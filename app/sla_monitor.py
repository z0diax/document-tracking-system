from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional

from flask import current_app
from sqlalchemy.orm import joinedload

from app import db
from app.models import (
    ActivityLog,
    Document,
    EWPRecord,
    LeaveRequest,
    Notification,
    SLAAlertPreference,
    User,
)
from app.utils import calculate_business_hours

# Actions that indicate a document was reassigned or re-entered a pending queue
_DOCUMENT_STATUS_ANCHORS: Dict[str, List[str]] = {
    "Pending": ["Forwarded", "Batch Forwarded", "Resubmitted", "Created"],
}


def _load_sla_preferences() -> Dict[str, bool]:
    defaults = SLAAlertPreference.DEFAULTS.copy()
    try:
        return SLAAlertPreference.get_preferences_map()
    except Exception as exc:
        current_app.logger.warning("Unable to load SLA preferences in SLA monitor: %s", exc)
        return defaults


def run_sla_checks() -> Dict[str, Dict[str, int]]:
    """
    Entry point for the APScheduler job. Returns per-entity summaries.
    """
    now = datetime.utcnow()
    try:
        admins = _collect_admins()
        preferences = _load_sla_preferences()
        results = {
            "documents": _monitor_document_slas(
                now, admins, enabled=preferences.get("documents", True)
            ),
            "leave_requests": _monitor_leave_slas(
                now, admins, enabled=preferences.get("leave_requests", True)
            ),
            "ewp_records": _monitor_ewp_slas(
                now, admins, enabled=preferences.get("ewp_records", True)
            ),
        }

        if db.session.new or db.session.dirty or db.session.deleted:
            db.session.commit()

        _log_summary(results)
        return results
    except Exception:
        db.session.rollback()
        current_app.logger.exception("SLA monitor run failed")
        raise


def _monitor_document_slas(
    now: datetime, admins: List[User], *, enabled: bool = True
) -> Dict[str, int]:
    if not enabled:
        return _empty_summary()

    rules = _get_rules("Document")
    if not rules:
        return _empty_summary()

    statuses = [status for status in rules.keys()]
    documents = (
        Document.query.options(
            joinedload(Document.creator),
            joinedload(Document.recipient),
        )
        .filter(Document.status.in_(statuses))
        .all()
    )

    summary = _empty_summary()
    for document in documents:
        rule = rules.get(document.status)
        if not rule:
            continue

        anchor = _resolve_document_anchor(document)
        if not anchor:
            continue

        use_business = rule.get("use_business_hours", False)
        elapsed_hours = _elapsed_hours(
            anchor, now, use_business_hours=use_business
        )
        severity = _determine_severity(elapsed_hours, rule)
        if not severity:
            continue

        # Avoid duplicate alerts for the same severity after the last reassignment
        if not _log_document_activity(
            document, severity, elapsed_hours, anchor, use_business
        ):
            continue

        elapsed_label = _format_elapsed_duration(elapsed_hours, use_business)
        message = _format_document_message(
            document, severity, elapsed_label
        )
        dedupe_hours = _dedupe_window(rule, severity)
        dedupe_key = f"Document#{document.id}:{document.status}:{severity}"

        recipients: List[User] = []
        if rule.get("notify_recipient") and document.recipient:
            recipients.append(document.recipient)
        if rule.get("notify_creator") and document.creator:
            recipients.append(document.creator)
        if severity == "escalate" and rule.get("escalate_to_admins"):
            recipients.extend(admins)

        if _notify_users(recipients, message, dedupe_key, dedupe_hours, now):
            summary["alerts"] += 1
            if severity == "escalate":
                summary["escalations"] += 1
            else:
                summary["warnings"] += 1

        summary["checked"] += 1

    return summary


def _monitor_leave_slas(
    now: datetime, admins: List[User], *, enabled: bool = True
) -> Dict[str, int]:
    if not enabled:
        return _empty_summary()

    rules = _get_rules("LeaveRequest")
    if not rules:
        return _empty_summary()

    statuses = [status for status in rules.keys()]
    leaves = (
        LeaveRequest.query.options(joinedload(LeaveRequest.created_by))
        .filter(LeaveRequest.status.in_(statuses))
        .all()
    )

    summary = _empty_summary()
    for leave in leaves:
        rule = rules.get(leave.status)
        if not rule:
            continue

        anchor = leave.created_timestamp
        if not anchor:
            continue

        use_business = rule.get("use_business_hours", False)
        elapsed_hours = _elapsed_hours(
            anchor, now, use_business_hours=use_business
        )
        severity = _determine_severity(elapsed_hours, rule)
        if not severity:
            continue

        message = (
            f"SLA {severity.capitalize()}: Leave request #{leave.id} "
            f"for {leave.employee_name} has been '{leave.status}' for "
            f"{_format_elapsed_duration(elapsed_hours, use_business)}."
        )
        dedupe_hours = _dedupe_window(rule, severity)
        dedupe_key = f"LeaveRequest#{leave.id}:{leave.status}:{severity}"

        recipients: List[User] = []
        if rule.get("notify_creator") and leave.created_by:
            recipients.append(leave.created_by)
        if severity == "escalate" and rule.get("escalate_to_admins"):
            recipients.extend(admins)

        if _notify_users(recipients, message, dedupe_key, dedupe_hours, now):
            summary["alerts"] += 1
            if severity == "escalate":
                summary["escalations"] += 1
            else:
                summary["warnings"] += 1

        summary["checked"] += 1

    return summary


def _monitor_ewp_slas(
    now: datetime, admins: List[User], *, enabled: bool = True
) -> Dict[str, int]:
    if not enabled:
        return _empty_summary()

    rules = _get_rules("EWPRecord")
    if not rules:
        return _empty_summary()

    statuses = [status for status in rules.keys()]
    records = (
        EWPRecord.query.options(joinedload(EWPRecord.created_by))
        .filter(EWPRecord.status.in_(statuses))
        .all()
    )

    summary = _empty_summary()
    for record in records:
        rule = rules.get(record.status)
        if not rule:
            continue

        anchor = record.created_timestamp
        if not anchor:
            continue

        use_business = rule.get("use_business_hours", False)
        elapsed_hours = _elapsed_hours(
            anchor, now, use_business_hours=use_business
        )
        severity = _determine_severity(elapsed_hours, rule)
        if not severity:
            continue

        message = (
            f"SLA {severity.capitalize()}: EWP record #{record.id} "
            f"for {record.employee_name} has been '{record.status}' for "
            f"{_format_elapsed_duration(elapsed_hours, use_business)}."
        )
        dedupe_hours = _dedupe_window(rule, severity)
        dedupe_key = f"EWPRecord#{record.id}:{record.status}:{severity}"

        recipients: List[User] = []
        if rule.get("notify_creator") and record.created_by:
            recipients.append(record.created_by)
        if severity == "escalate" and rule.get("escalate_to_admins"):
            recipients.extend(admins)

        if _notify_users(recipients, message, dedupe_key, dedupe_hours, now):
            summary["alerts"] += 1
            if severity == "escalate":
                summary["escalations"] += 1
            else:
                summary["warnings"] += 1

        summary["checked"] += 1

    return summary


def _notify_users(
    users: Iterable[Optional[User]],
    message: str,
    dedupe_key: str,
    dedupe_hours: float,
    now: datetime,
) -> bool:
    sent_any = False
    seen_ids = set()
    for user in users:
        if not user or user.id in seen_ids:
            continue
        if getattr(user, "status", "Active") not in (None, "Active"):
            continue

        if _send_notification_once(user, message, dedupe_key, dedupe_hours, now):
            sent_any = True
        seen_ids.add(user.id)

    return sent_any


def _send_notification_once(
    user: User,
    message: str,
    dedupe_key: str,
    dedupe_hours: float,
    now: datetime,
) -> bool:
    """
    Prevent duplicate notifications within the configured window.
    """
    cutoff = now - timedelta(hours=dedupe_hours)
    existing = (
        Notification.query.filter(
            Notification.user_id == user.id,
            Notification.message.contains(dedupe_key),
            Notification.timestamp >= cutoff,
        )
        .order_by(Notification.timestamp.desc())
        .first()
    )

    if existing:
        return False

    alert = Notification(user=user, message=f"{message} [{dedupe_key}]")
    alert.timestamp = now
    db.session.add(alert)
    return True


def _resolve_document_anchor(document: Document) -> Optional[datetime]:
    actions = _DOCUMENT_STATUS_ANCHORS.get(document.status)
    if not actions:
        return document.timestamp

    anchor_log = (
        ActivityLog.query.filter(
            ActivityLog.document_id == document.id,
            ActivityLog.action.in_(actions),
        )
        .order_by(ActivityLog.timestamp.desc())
        .first()
    )

    return anchor_log.timestamp if anchor_log else document.timestamp


def _log_document_activity(
    document: Document,
    severity: str,
    elapsed_hours: float,
    anchor_time: datetime,
    use_business_hours: bool,
) -> bool:
    action = "SLA Escalation" if severity == "escalate" else "SLA Warning"
    existing = (
        ActivityLog.query.filter(
            ActivityLog.document_id == document.id,
            ActivityLog.action == action,
            ActivityLog.timestamp >= anchor_time,
        )
        .order_by(ActivityLog.timestamp.desc())
        .first()
    )

    if existing:
        return False

    actor = document.recipient or document.creator
    if not actor:
        # Allow notifications even if we cannot record history
        return True

    elapsed_label = _format_elapsed_duration(elapsed_hours, use_business_hours)
    remarks = (
        f"Automated SLA monitor flagged status '{document.status}' "
        f"after {elapsed_label}."
    )
    entry = ActivityLog(
        user=actor,
        document_id=document.id,
        action=action,
        remarks=remarks,
    )
    entry.timestamp = datetime.utcnow()
    db.session.add(entry)
    return True


def _elapsed_hours(
    anchor: datetime,
    now: datetime,
    *,
    use_business_hours: bool,
) -> float:
    if use_business_hours:
        delta = calculate_business_hours(anchor, now)
    else:
        delta = now - anchor
    return max(delta.total_seconds(), 0) / 3600.0


def _determine_severity(elapsed_hours: float, rule: Dict[str, float]) -> Optional[str]:
    escalate = rule.get("escalate_after_hours")
    warn = rule.get("warn_after_hours")

    if escalate and elapsed_hours >= escalate:
        return "escalate"
    if warn and elapsed_hours >= warn:
        return "warn"
    return None


def _dedupe_window(rule: Dict[str, float], severity: str) -> float:
    if severity == "escalate":
        return rule.get("escalation_dedupe_hours", rule.get("dedupe_hours", 12))
    return rule.get("dedupe_hours", 6)


def _get_rules(entity: str) -> Dict[str, Dict[str, float]]:
    config = current_app.config.get("SLA_RULES", {})
    return config.get(entity, {})


def _collect_admins() -> List[User]:
    return User.query.filter(
        User.is_admin.is_(True),
        User.status == "Active",
    ).all()


def _format_document_message(
    document: Document,
    severity: str,
    elapsed_label: str,
) -> str:
    return (
        f"SLA {severity.capitalize()}: Document #{document.id} "
        f"('{document.title}') assigned to {document.recipient.username if document.recipient else 'N/A'} "
        f"has been '{document.status}' for {elapsed_label}."
    )


def _empty_summary() -> Dict[str, int]:
    return {"checked": 0, "warnings": 0, "escalations": 0, "alerts": 0}


def _log_summary(results: Dict[str, Dict[str, int]]) -> None:
    total_alerts = sum(section["alerts"] for section in results.values())
    if total_alerts == 0:
        current_app.logger.debug("SLA monitor completed: no new alerts.")
        return

    current_app.logger.info("SLA monitor alerts summary: %s", results)


def _format_elapsed_duration(hours: float, use_business_hours: bool) -> str:
    """
    Present elapsed time in user-friendly terms. Business hours treat 8 hours as a day.
    """
    if hours <= 0:
        return "less than an hour"

    hours_per_day = 8 if use_business_hours else 24
    total_hours = max(hours, 0.0)

    days = int(total_hours // hours_per_day)
    remaining_hours = round(total_hours - (days * hours_per_day), 2)

    parts: List[str] = []
    if days:
        day_label = "business day" if use_business_hours else "day"
        parts.append(f"{days} {day_label}{'s' if days != 1 else ''}")

    # Determine whether to show remaining hours or minutes
    if remaining_hours >= 0.01:
        if remaining_hours >= 1 or not parts:
            rounded_hours = round(remaining_hours, 1)
            if abs(rounded_hours - round(rounded_hours)) < 0.05:
                rounded_hours = int(round(rounded_hours))
            parts.append(f"{rounded_hours} hour{'s' if rounded_hours != 1 else ''}")
        else:
            minutes = int(round(remaining_hours * 60))
            if minutes:
                parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

    if not parts:
        parts.append("less than an hour")

    return " and ".join(parts)
