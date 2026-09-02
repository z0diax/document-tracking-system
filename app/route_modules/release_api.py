from datetime import datetime

from flask import abort, current_app, jsonify, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.access import (
    document_access_filter,
    release_batch_access_filter,
    user_can_access_document,
    user_can_manage_release_batch,
    visible_release_batch_links,
)
from app import db
from app.models import (
    ActivityLog,
    Document,
    Notification,
    ReleaseBatch,
    ReleaseBatchDocument,
    User,
    to_local_time,
)
from app.route_modules.shared import main
from app.theme_state import (
    ALLOWED_THEMES,
    DEFAULT_THEME,
    THEME_SEQUENCE,
    WEATHER_AUTO_THEME,
    enable_weather_theme,
    read_theme_state,
    resolve_theme_state,
    write_theme_state,
)


@main.route('/api/users/search', methods=['GET'])
@login_required
def search_recipients():
    """Search users for recipient selection (excludes current user)."""
    term = (request.args.get('q') or '').strip()
    include_recent = (request.args.get('include_recent') or '').lower() in {'1', 'true', 'yes', 'on'}
    try:
        limit = int(request.args.get('limit', 10))
    except (TypeError, ValueError):
        limit = 10
    limit = max(1, min(limit, 25))

    base_query = User.query.filter(User.id != current_user.id)
    if term:
        like_term = f'%{term}%'
        base_query = base_query.filter(User.username.ilike(like_term))
    users = base_query.order_by(User.username.asc()).limit(limit).all()

    def _serialize(user_obj):
        return {'id': user_obj.id, 'label': user_obj.username}

    recent_payload = []
    if include_recent:
        recent_ids = [
            rid for (rid,) in (
                db.session.query(Document.recipient_id)
                .filter(Document.creator_id == current_user.id)
                .filter(Document.recipient_id.isnot(None))
                .order_by(Document.timestamp.desc())
                .distinct()
                .limit(5)
            )
        ]
        if recent_ids:
            users_map = {u.id: u for u in User.query.filter(User.id.in_(recent_ids)).all()}
            recent_payload = [_serialize(users_map[rid]) for rid in recent_ids if rid in users_map]

    return jsonify({
        'results': [_serialize(u) for u in users],
        'recent': recent_payload,
    })


@main.route('/api/documents/search', methods=['GET'])
@login_required
def search_documents():
    """Search documents by title, barcode, or office within the caller's scope."""
    term = (request.args.get('q') or '').strip()
    try:
        limit = int(request.args.get('limit', 8))
    except (TypeError, ValueError):
        limit = 8
    limit = max(1, min(limit, 100))

    if len(term) < 2:
        return jsonify({'results': []})

    like_term = f'%{term}%'
    docs = (
        Document.query.filter(document_access_filter(current_user))
        .filter(
            or_(
                Document.title.ilike(like_term),
                Document.barcode.ilike(like_term),
                Document.office.ilike(like_term),
            )
        )
        .order_by(Document.timestamp.desc())
        .limit(limit)
        .all()
    )

    return jsonify({
        'results': [
            {
                'id': doc.id,
                'title': doc.title or '',
                'barcode': doc.barcode or '',
                'office': doc.office or '',
            }
            for doc in docs
        ]
    })


@main.route('/api/release_batches', methods=['GET'])
@login_required
def list_release_batches():
    """Return release batches with linked documents for the modal table."""
    try:
        limit = int(request.args.get('limit', 200))
    except (TypeError, ValueError):
        limit = 200
    limit = max(1, min(limit, 500))

    try:
        today_key = to_local_time(datetime.utcnow()).strftime('%Y-%m-%d')
    except Exception:
        today_key = datetime.utcnow().strftime('%Y-%m-%d')

    batches = (
        ReleaseBatch.query
        .filter(release_batch_access_filter(current_user))
        .options(joinedload(ReleaseBatch.documents).joinedload(ReleaseBatchDocument.document))
        .order_by(ReleaseBatch.release_at.desc())
        .limit(limit)
        .all()
    )

    def _doc_payload(link_obj):
        doc = link_obj.document
        if not doc:
            return None
        try:
            timestamp = to_local_time(doc.timestamp).strftime('%B-%d-%Y at %I:%M %p') if doc.timestamp else ''
        except Exception:
            timestamp = doc.timestamp.isoformat() if doc and doc.timestamp else ''
        return {
            'id': doc.id,
            'title': doc.title or '',
            'barcode': doc.barcode or '',
            'office': doc.office or '',
            'classification': doc.classification or '',
            'status': doc.status or '',
            'action_taken': doc.action_taken or '',
            'remarks': doc.remarks or '',
            'attachment': doc.attachment or '',
            'attachment_url': (
                url_for('main.download_document_attachment', document_id=doc.id)
                if doc.attachment and user_can_access_document(current_user, doc)
                else None
            ),
            'creator': doc.creator.username if doc.creator else '',
            'recipient': doc.recipient.username if doc.recipient else '',
            'timestamp': timestamp,
        }

    payload = []
    for batch in batches:
        try:
            release_at_iso = batch.release_at.isoformat() if batch.release_at else None
            local_release = to_local_time(batch.release_at) if batch.release_at else None
            release_at_local = local_release.isoformat() if local_release else None
            release_date_key = local_release.strftime('%Y-%m-%d') if local_release else ''
            release_date_label = local_release.strftime('%b %d, %Y') if local_release else ''
            release_month_key = local_release.strftime('%Y-%m') if local_release else ''
            release_month_label = local_release.strftime('%B %Y') if local_release else ''
        except Exception:
            release_at_iso = None
            release_at_local = None
            release_date_key = ''
            release_date_label = ''
            release_month_key = ''
            release_month_label = ''
        docs = [payload_doc for payload_doc in (_doc_payload(link) for link in visible_release_batch_links(batch, current_user)) if payload_doc]
        payload.append({
            'id': batch.id,
            'name': batch.name,
            'can_edit': user_can_manage_release_batch(current_user, batch),
            'release_at': release_at_iso,
            'release_at_local': release_at_local,
            'release_date_key': release_date_key,
            'release_date_label': release_date_label,
            'release_month_key': release_month_key,
            'release_month_label': release_month_label,
            'is_today': bool(release_date_key) and release_date_key == today_key,
            'documents': docs,
        })

    return jsonify({'results': payload})


@main.route('/api/documents/update_basic', methods=['POST'])
@login_required
def update_document_basic():
    """Update basic fields for a document the user can access."""
    doc_id = request.form.get('document_id')
    try:
        doc_id_int = int(doc_id)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Invalid document id.'}), 400

    document = Document.query.get(doc_id_int)
    if not document:
        return jsonify({'success': False, 'message': 'Document not found.'}), 404

    if document.creator_id != current_user.id and document.recipient_id != current_user.id:
        return jsonify({'success': False, 'message': 'Not authorized to edit this document.'}), 403

    title = (request.form.get('title') or '').strip()
    office = (request.form.get('office') or '').strip()
    barcode = (request.form.get('barcode') or '').strip()
    remarks = (request.form.get('remarks') or '').strip()

    try:
        if title:
            document.title = title
        if office:
            document.office = office
        document.barcode = barcode or None
        document.remarks = remarks or None
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error('Failed to update document %s: %s', doc_id_int, exc)
        return jsonify({'success': False, 'message': 'Failed to update document.'}), 500

    return jsonify({
        'success': True,
        'document': {
            'id': document.id,
            'title': document.title or '',
            'office': document.office or '',
            'barcode': document.barcode or '',
            'remarks': document.remarks or '',
        },
    })


def _serialize_doc_basic(doc_obj):
    if not doc_obj:
        return None
    try:
        timestamp = to_local_time(doc_obj.timestamp).strftime('%B-%d-%Y at %I:%M %p') if doc_obj.timestamp else ''
    except Exception:
        timestamp = doc_obj.timestamp.isoformat() if doc_obj and doc_obj.timestamp else ''
    return {
        'id': doc_obj.id,
        'title': doc_obj.title or '',
        'barcode': doc_obj.barcode or '',
        'office': doc_obj.office or '',
        'classification': doc_obj.classification or '',
        'status': doc_obj.status or '',
        'action_taken': doc_obj.action_taken or '',
        'remarks': doc_obj.remarks or '',
        'attachment': doc_obj.attachment or '',
        'attachment_url': (
            url_for('main.download_document_attachment', document_id=doc_obj.id)
            if doc_obj.attachment and user_can_access_document(current_user, doc_obj)
            else None
        ),
        'creator': doc_obj.creator.username if doc_obj.creator else '',
        'recipient': doc_obj.recipient.username if doc_obj.recipient else '',
        'timestamp': timestamp,
    }


def _get_release_accessible_docs(doc_ids_int):
    if not doc_ids_int:
        return []
    return (
        Document.query
        .filter(Document.id.in_(doc_ids_int))
        .filter(document_access_filter(current_user))
        .all()
    )


@main.route('/release_batches/<int:batch_id>/documents/add', methods=['POST'])
@login_required
def add_docs_to_release_batch(batch_id):
    batch = ReleaseBatch.query.get_or_404(batch_id)
    if not user_can_manage_release_batch(current_user, batch):
        return jsonify({'success': False, 'message': 'Not authorized to edit this batch.'}), 403
    doc_ids = request.form.getlist('document_ids[]') or request.form.getlist('document_ids') or [request.form.get('document_id')]
    doc_ids = [doc_id for doc_id in doc_ids if doc_id]
    if not doc_ids:
        return jsonify({'success': False, 'message': 'No documents provided.'}), 400
    try:
        doc_ids_int = list({int(value) for value in doc_ids})
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Invalid document ids.'}), 400

    docs = _get_release_accessible_docs(doc_ids_int)
    if not docs:
        return jsonify({'success': False, 'message': 'No accessible documents found.'}), 403

    existing_links = {link.document_id for link in batch.documents}
    release_ts = batch.release_at or datetime.utcnow()

    try:
        for doc in docs:
            if doc.id in existing_links:
                continue
            if ReleaseBatchDocument.query.filter_by(release_batch_id=batch.id, document_id=doc.id).first():
                continue
            link = ReleaseBatchDocument(batch=batch, document=doc)
            db.session.add(link)
            doc.status = 'Released'
            doc.released_timestamp = release_ts
            db.session.add(ActivityLog(
                user=current_user,
                document_id=doc.id,
                action='Batch Released',
                remarks=f"Added to batch '{batch.name}'",
            ))
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        current_app.logger.warning('IntegrityError adding docs to batch %s: %s', batch_id, exc)
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception('Failed to add docs to batch %s: %s', batch_id, exc)
        return jsonify({'success': False, 'message': 'Failed to add documents.'}), 500

    serialized_docs = []
    for link in batch.documents:
        try:
            payload = _serialize_doc_basic(link.document)
            if payload:
                serialized_docs.append(payload)
        except Exception as exc:
            current_app.logger.error(
                'Failed to serialize doc %s in batch %s: %s',
                getattr(link, 'document_id', None),
                batch_id,
                exc,
            )

    return jsonify({
        'success': True,
        'batch': {
            'id': batch.id,
            'name': batch.name,
            'release_at': batch.release_at.isoformat() if batch.release_at else None,
            'release_at_local': to_local_time(batch.release_at).isoformat() if batch.release_at else None,
        },
        'documents': serialized_docs,
    })


@main.route('/release_batches/<int:batch_id>/documents/remove', methods=['POST'])
@login_required
def remove_doc_from_release_batch(batch_id):
    batch = ReleaseBatch.query.get_or_404(batch_id)
    if not user_can_manage_release_batch(current_user, batch):
        return jsonify({'success': False, 'message': 'Not authorized to edit this batch.'}), 403
    doc_id = request.form.get('document_id')
    try:
        doc_id_int = int(doc_id)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Invalid document id.'}), 400

    link = ReleaseBatchDocument.query.filter_by(release_batch_id=batch.id, document_id=doc_id_int).first()
    if not link:
        return jsonify({'success': False, 'message': 'Document not linked to this batch.'}), 404

    try:
        db.session.delete(link)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception('Failed to remove doc %s from batch %s: %s', doc_id_int, batch_id, exc)
        return jsonify({'success': False, 'message': 'Failed to remove document.'}), 500

    serialized_docs = []
    for batch_link in batch.documents:
        try:
            payload = _serialize_doc_basic(batch_link.document)
            if payload:
                serialized_docs.append(payload)
        except Exception as exc:
            current_app.logger.error(
                'Failed to serialize doc %s in batch %s after delete: %s',
                getattr(batch_link, 'document_id', None),
                batch_id,
                exc,
            )

    return jsonify({
        'success': True,
        'batch': {
            'id': batch.id,
            'name': batch.name,
            'release_at': batch.release_at.isoformat() if batch.release_at else None,
            'release_at_local': to_local_time(batch.release_at).isoformat() if batch.release_at else None,
        },
        'documents': serialized_docs,
    })


@main.route('/release_batches/<int:batch_id>/delete', methods=['POST'])
@login_required
def delete_release_batch(batch_id):
    batch = ReleaseBatch.query.get_or_404(batch_id)
    if not user_can_manage_release_batch(current_user, batch):
        return jsonify({'success': False, 'message': 'Not authorized to delete this batch.'}), 403
    try:
        db.session.delete(batch)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error('Failed to delete batch %s: %s', batch_id, exc)
        return jsonify({'success': False, 'message': 'Failed to delete batch.'}), 500
    return jsonify({'success': True, 'batch_id': batch_id})


@main.route('/release_batches', methods=['POST'])
@login_required
def create_release_batch():
    """Create a release batch and link selected documents."""
    batch_name = (request.form.get('batch_name') or '').strip()
    doc_ids = request.form.getlist('release_doc_ids[]') or request.form.getlist('release_doc_ids')

    if not doc_ids:
        return jsonify({'success': False, 'message': 'No documents selected.'}), 400

    try:
        doc_ids_int = list({int(value) for value in doc_ids})
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Invalid document selection.'}), 400

    docs = _get_release_accessible_docs(doc_ids_int)
    if not docs:
        return jsonify({'success': False, 'message': 'No accessible documents found.'}), 403
    if len(docs) != len(doc_ids_int):
        return jsonify({'success': False, 'message': 'Some documents could not be accessed.'}), 403

    release_ts = datetime.utcnow()
    if not batch_name:
        try:
            local_ts = to_local_time(release_ts)
            batch_name = f"Release Batch - {local_ts.strftime('%d/%m/%Y %I:%M %p')}"
        except Exception:
            batch_name = f"Release Batch - {release_ts.strftime('%Y-%m-%d %I:%M %p')}"

    try:
        batch = ReleaseBatch(name=batch_name, created_by=current_user, release_at=release_ts)
        db.session.add(batch)

        for doc in docs:
            doc.status = 'Released'
            doc.released_timestamp = release_ts
            db.session.add(ReleaseBatchDocument(batch=batch, document=doc))

            if doc.creator and doc.creator != current_user:
                db.session.add(Notification(
                    user=doc.creator,
                    message=f"Your document '{doc.title}' has been released in batch '{batch_name}'.",
                ))

            db.session.add(ActivityLog(
                user=current_user,
                document_id=doc.id,
                action='Batch Released',
                remarks=f"Released via batch '{batch_name}'",
            ))

        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error('Failed to create release batch: %s', exc)
        return jsonify({'success': False, 'message': 'Failed to create release batch.'}), 500

    return jsonify({
        'success': True,
        'batch': {
            'id': batch.id,
            'name': batch.name,
            'can_edit': True,
            'release_at': batch.release_at.isoformat(),
            'release_at_local': to_local_time(batch.release_at).isoformat() if batch.release_at else None,
        },
        'documents': [_serialize_doc_basic(doc) for doc in docs],
    })


@main.route('/system-theme', methods=['GET'])
@login_required
def get_system_theme_state():
    state = resolve_theme_state(current_app)
    return jsonify({
        'theme': state.get('theme', DEFAULT_THEME),
        'effective_theme': state.get('effective_theme', state.get('theme', DEFAULT_THEME)),
        'updated_at': state.get('updated_at'),
        'updated_by': state.get('updated_by'),
        'updated_by_id': state.get('updated_by_id'),
        'location_query': state.get('location_query'),
        'location_name': state.get('location_name'),
        'weather_label': state.get('weather_label'),
        'weather_updated_at': state.get('weather_updated_at'),
    })


@main.route('/system-theme', methods=['POST'])
@login_required
def set_system_theme():
    if not current_user.is_admin:
        abort(403)

    payload = request.get_json(silent=True) or {}
    requested_theme = (payload.get('theme') or '').strip().lower()
    requested_location = (payload.get('location') or '').strip()

    current_state = read_theme_state(current_app)
    current_theme = current_state.get('theme', DEFAULT_THEME)

    if requested_theme in ('', 'toggle', 'next'):
        try:
            idx = THEME_SEQUENCE.index(current_theme)
        except ValueError:
            idx = 0
        requested_theme = THEME_SEQUENCE[(idx + 1) % len(THEME_SEQUENCE)]

    if requested_theme not in ALLOWED_THEMES:
        return jsonify({'error': 'Invalid theme selection'}), 400

    try:
        if requested_theme == WEATHER_AUTO_THEME:
            if not requested_location:
                requested_location = (current_state.get('location_query') or current_state.get('location_name') or '').strip()
            if not requested_location:
                return jsonify({'error': 'Location is required for Weather Sync.'}), 400
            state = enable_weather_theme(current_app, requested_location, current_user)
        else:
            state = write_theme_state(current_app, requested_theme, current_user)
    except Exception as exc:
        current_app.logger.error('Failed to persist system theme: %s', exc)
        return jsonify({'error': str(exc) if isinstance(exc, ValueError) else 'Unable to save theme'}), 400 if isinstance(exc, ValueError) else 500

    return jsonify({
        'theme': state.get('theme', DEFAULT_THEME),
        'effective_theme': state.get('effective_theme', state.get('theme', DEFAULT_THEME)),
        'updated_at': state.get('updated_at'),
        'updated_by': state.get('updated_by'),
        'updated_by_id': state.get('updated_by_id'),
        'location_query': state.get('location_query'),
        'location_name': state.get('location_name'),
        'weather_label': state.get('weather_label'),
        'weather_updated_at': state.get('weather_updated_at'),
    })
