from sqlalchemy import or_

from app.models import ActivityLog, Document, User


def paginate_admin_lists(doc_page, activity_page, user_page, search_query):
    documents_query = Document.query
    if search_query:
        documents_query = documents_query.filter(
            or_(
                Document.title.ilike(f'%{search_query}%'),
                Document.office.ilike(f'%{search_query}%'),
                Document.classification.ilike(f'%{search_query}%'),
                Document.status.ilike(f'%{search_query}%'),
                or_(
                    Document.barcode.ilike(f'%{search_query}%'),
                    Document.barcode == search_query,
                ),
            )
        )

    paginated_documents = documents_query.order_by(Document.timestamp.desc()).paginate(
        page=doc_page,
        per_page=10,
        error_out=False,
    )

    activities_query = ActivityLog.query.join(
        Document,
        ActivityLog.document_id == Document.id,
    ).join(
        User,
        ActivityLog.user_id == User.id,
    ).order_by(
        ActivityLog.timestamp.desc()
    )
    paginated_activities = activities_query.paginate(
        page=activity_page,
        per_page=10,
        error_out=False,
    )

    users_pagination = User.query.order_by(User.id).paginate(
        page=user_page,
        per_page=10,
        error_out=False,
    )

    return paginated_documents, paginated_activities, users_pagination
