from datetime import datetime

def auto_archive_documents():
    """
    Archives documents created in previous months.
    """
    from app import db  # Delayed import to avoid circular dependency
    from app.models import Document

    # Get the current month and year
    current_date = datetime.utcnow()
    current_month = current_date.month
    current_year = current_date.year

    # Find documents created in previous months
    documents_to_archive = Document.query.filter(
        (Document.timestamp < datetime(current_year, current_month, 1)) & 
        (Document.status != 'archived')  # Avoid re-archiving already archived documents
    ).all()

    # Archive the documents
    for document in documents_to_archive:
        document.status = 'archived'
        db.session.commit()

    print(f"Archived {len(documents_to_archive)} documents.")
