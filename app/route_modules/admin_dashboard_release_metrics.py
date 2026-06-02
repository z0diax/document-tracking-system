from datetime import UTC, datetime, timedelta

from app.models import Document
from app.utils import calculate_business_hours


def build_release_metrics():
    released_docs = Document.query.filter_by(status='Released').order_by(Document.released_timestamp.desc()).all()

    total_release_time = timedelta()
    valid_release_count = 0
    release_metrics = []
    for document in released_docs:
        if document.released_timestamp and document.timestamp:
            release_time = calculate_business_hours(document.timestamp, document.released_timestamp)
            total_release_time += release_time
            valid_release_count += 1
            release_metrics.append({
                'title': document.title,
                'creator': document.creator.username,
                'handler': document.recipient.username,
                'release_time': release_time,
            })

    avg_release_time = (total_release_time / valid_release_count) if valid_release_count > 0 else timedelta()
    return avg_release_time, release_metrics


def build_pending_metrics():
    pending_documents = Document.query.filter_by(status='Pending').order_by(Document.timestamp.asc()).limit(5).all()
    now = datetime.now(UTC)
    pending_docs_info = [{
        'title': document.title,
        'creator': document.creator.username,
        'assigned_to': document.recipient.username,
        'created_date': document.timestamp,
        'pending_time': calculate_business_hours(document.timestamp, now),
    } for document in pending_documents]
    return pending_documents, pending_docs_info
