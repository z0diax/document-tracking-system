from datetime import datetime
from app import db
from app.models import Document, ActivityLog

def archive_old_documents():
    """
    Archive documents created before the first day of the current month (i.e., made last month or earlier) that are not already archived.
    """
    current_date = datetime.utcnow()
    first_day_of_current_month = datetime(current_date.year, current_date.month, 1)
    old_docs = Document.query.filter(
        Document.timestamp < first_day_of_current_month,
        Document.status != 'Archived'
    ).all()

    for doc in old_docs:
        doc.status = 'Archived'
        log = ActivityLog(
            user=doc.creator,
            document_id=doc.id,
            action="Auto Archived",
            remarks="Automatically archived after one month."
        )
        db.session.add(log)
    db.session.commit()
    return f"Archived {len(old_docs)} documents."

if __name__ == '__main__':
    print(archive_old_documents())
