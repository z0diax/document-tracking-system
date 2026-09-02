from sqlalchemy import or_, true

from app.models import Document, ReleaseBatch, ReleaseBatchDocument


def document_access_filter(user):
    if getattr(user, 'is_admin', False):
        return true()
    return or_(
        Document.creator_id == user.id,
        Document.recipient_id == user.id,
    )


def user_can_access_document(user, document):
    if not user or not getattr(user, 'is_authenticated', False) or not document:
        return False
    if getattr(user, 'is_admin', False):
        return True
    return document.creator_id == user.id or document.recipient_id == user.id


def release_batch_access_filter(user):
    if getattr(user, 'is_admin', False):
        return true()
    return or_(
        ReleaseBatch.created_by_id == user.id,
        ReleaseBatch.documents.any(
            ReleaseBatchDocument.document.has(document_access_filter(user))
        ),
    )


def user_can_manage_release_batch(user, batch):
    if not user or not getattr(user, 'is_authenticated', False) or not batch:
        return False
    return getattr(user, 'is_admin', False) or batch.created_by_id == user.id


def visible_release_batch_links(batch, user):
    if not batch:
        return []
    if user_can_manage_release_batch(user, batch):
        return [link for link in batch.documents if link.document]
    return [
        link for link in batch.documents
        if link.document and user_can_access_document(user, link.document)
    ]
