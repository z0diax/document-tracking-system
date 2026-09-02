import os
from datetime import datetime

from flask import current_app, flash, jsonify, redirect, request, url_for
from flask_login import current_user, login_required

from app import db
from app.forms import (
    BatchDeclineDocumentForm,
    BatchForwardDocumentForm,
    DeclineDocumentForm,
    DocumentForm,
    ForwardDocumentForm,
    ResubmitDocumentForm,
)
from app.models import ActivityLog, Document, Notification, ProcessingLog, User
from app.route_modules.shared import (
    ACTION_TAKEN_CHOICES,
    CLASSIFICATION_CHOICES,
    OFFICE_CHOICES,
    STATUS_CHOICES,
    get_recipient_choices,
    main,
)
from app.utils import get_upload_path, get_upload_root, is_allowed_file


def _dashboard_listing_args(default_view='received'):
    return {
        'page': request.args.get('page', 1, type=int),
        'view': request.args.get('view', default_view),
        'search': request.args.get('search', ''),
    }


def _dashboard_redirect(view=None, page=None, search=None):
    kwargs = {}
    if view is not None:
        kwargs['view'] = view
    if page is not None:
        kwargs['page'] = page
    if search is not None:
        kwargs['search'] = search
    return redirect(url_for('main.dashboard', **kwargs))


def _save_document_attachment(file_storage):
    if not file_storage:
        return None
    if not is_allowed_file(file_storage.filename):
        raise ValueError('Invalid attachment file type.')
    attachment_rel = get_upload_path(file_storage.filename)
    upload_root = get_upload_root()
    file_path = os.path.join(upload_root, attachment_rel)
    os.makedirs(upload_root, exist_ok=True)
    file_storage.save(file_path)
    return attachment_rel


@main.route('/create_document', methods=['POST'])
@login_required
def create_document():
    form = DocumentForm()
    form.office.choices = OFFICE_CHOICES
    form.classification.choices = CLASSIFICATION_CHOICES
    form.status.choices = STATUS_CHOICES
    form.action_taken.choices = ACTION_TAKEN_CHOICES
    form.recipient.choices = get_recipient_choices()

    if form.validate_on_submit():
        try:
            attachment_path = None
            if form.attachment.data:
                attachment_path = _save_document_attachment(form.attachment.data)

            classification = request.form.get('full_classification') or form.classification.data
            recipient_user = User.query.get(form.recipient.data)
            barcode_value = form.barcode.data.strip() if form.barcode.data else None
            barcode_suggested_flag = request.form.get('barcode_from_suggestion') == '1'
            document = Document(
                title=form.title.data,
                office=form.office.data,
                classification=classification,
                status='Pending',
                action_taken=form.action_taken.data,
                remarks=form.remarks.data,
                attachment=attachment_path,
                barcode=barcode_value,
                creator=current_user,
                recipient=recipient_user,
            )

            db.session.add(document)
            db.session.commit()

            db.session.add(Notification(
                user=recipient_user,
                message=f'You have received a new document: {document.title}',
            ))

            db.session.add(ActivityLog(
                user=current_user,
                document_id=document.id,
                action='Created',
                remarks=form.remarks.data if form.remarks.data else '',
            ))

            if barcode_suggested_flag:
                original_barcode = (request.form.get('original_barcode') or '').strip()
                selected_barcode = barcode_value or ''
                if original_barcode and selected_barcode:
                    remark_text = f'Original: {original_barcode} - Selected: {selected_barcode}'
                elif selected_barcode:
                    remark_text = f'Selected: {selected_barcode}'
                else:
                    remark_text = 'Barcode chosen from suggestion feature'
                db.session.add(ActivityLog(
                    user=current_user,
                    document_id=document.id,
                    action='Barcode Suggested',
                    remarks=remark_text,
                ))

            db.session.commit()
            flash('Document created successfully.', 'success')
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), 'danger')
        except Exception as exc:
            db.session.rollback()
            flash(f'Error creating document: {str(exc)}', 'danger')

        return redirect(url_for('main.dashboard'))

    for field, errors in form.errors.items():
        for error in errors:
            flash(f'Error in {field}: {error}', 'danger')

    return redirect(url_for('main.dashboard'))


@main.route('/edit_document/<int:document_id>', methods=['POST'])
@login_required
def edit_document(document_id):
    document = Document.query.get_or_404(document_id)

    if document.creator != current_user:
        flash('You are not authorized to edit this document.', 'danger')
        return redirect(url_for('main.dashboard'))

    form = DocumentForm()
    form.office.choices = OFFICE_CHOICES
    form.classification.choices = CLASSIFICATION_CHOICES
    form.status.choices = STATUS_CHOICES
    form.action_taken.choices = ACTION_TAKEN_CHOICES
    form.recipient.choices = get_recipient_choices()

    if form.validate_on_submit():
        try:
            if form.attachment.data:
                document.attachment = _save_document_attachment(form.attachment.data)

            classification = request.form.get('full_classification') or form.classification.data
            barcode_value = form.barcode.data.strip() if form.barcode.data else None
            document.title = form.title.data
            document.office = form.office.data
            document.classification = classification
            document.status = form.status.data
            document.action_taken = form.action_taken.data
            document.remarks = form.remarks.data
            document.barcode = barcode_value
            document.recipient = User.query.get(form.recipient.data)

            db.session.commit()
            flash('Document updated successfully.', 'success')
            return redirect(url_for('main.dashboard'))
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), 'danger')
            return redirect(url_for('main.dashboard'))
        except Exception as exc:
            db.session.rollback()
            flash(f'Error updating document: {str(exc)}', 'danger')
            return redirect(url_for('main.dashboard'))

    for field, errors in form.errors.items():
        for error in errors:
            flash(f'Error in {field}: {error}', 'danger')

    return redirect(url_for('main.dashboard'))


@main.route('/delete_document/<int:document_id>', methods=['POST'])
@login_required
def delete_document(document_id):
    document = Document.query.get_or_404(document_id)

    if document.creator != current_user:
        flash('You are not authorized to delete this document.', 'danger')
        return redirect(url_for('main.dashboard'))

    try:
        db.session.delete(document)
        db.session.commit()
        flash('Document deleted successfully.', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(f'Error deleting document: {str(exc)}', 'danger')

    return redirect(url_for('main.dashboard'))


@main.route('/accept_document/<int:document_id>', methods=['POST'])
@login_required
def accept_document(document_id):
    listing_args = _dashboard_listing_args(default_view='received')
    document = Document.query.get_or_404(document_id)

    if document.recipient != current_user:
        flash('You are not authorized to accept this document.', 'danger')
        return _dashboard_redirect(view=listing_args['view'], page=listing_args['page'])

    if document.status not in ['Pending', 'Forwarded']:
        flash('This document cannot be accepted in its current state.', 'warning')
        return redirect(url_for('main.dashboard'))

    try:
        document.status = 'Accepted'
        document.accepted_timestamp = datetime.utcnow()

        db.session.add(Notification(
            user=document.creator,
            message=f"Your document '{document.title}' has been accepted by {current_user.username}",
        ))
        db.session.add(ActivityLog(
            user=current_user,
            document_id=document.id,
            action='Accepted',
            remarks='Document accepted',
        ))
        db.session.add(ProcessingLog(
            user_id=current_user.id,
            document_id=document.id,
            accepted_timestamp=datetime.utcnow(),
        ))

        db.session.commit()
        flash('Document accepted successfully.', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(f'Error accepting document: {str(exc)}', 'danger')

    return _dashboard_redirect(view='received', page=listing_args['page'])


@main.route('/release_document/<int:document_id>', methods=['POST'])
@login_required
def release_document(document_id):
    listing_args = _dashboard_listing_args(default_view='received')
    document = Document.query.get_or_404(document_id)

    if document.recipient != current_user:
        flash('You are not authorized to release this document.', 'danger')
        return _dashboard_redirect(view=listing_args['view'], page=listing_args['page'])

    document.status = 'Released'
    document.released_timestamp = datetime.utcnow()

    db.session.add(Notification(
        user=document.creator,
        message=f"Your document '{document.title}' has been released.",
    ))
    db.session.add(ActivityLog(
        user=current_user,
        document_id=document.id,
        action='Released',
        remarks=None,
    ))
    db.session.commit()

    flash('Document released successfully.', 'success')
    return _dashboard_redirect(view='received', page=listing_args['page'])


@main.route('/documents/<int:document_id>/toggle_no_dtas', methods=['POST'])
@login_required
def toggle_no_dtas(document_id):
    document = Document.query.get_or_404(document_id)
    if not (current_user.is_admin or current_user.id in {document.creator_id, document.recipient_id}):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    current_value = document.no_dtas_flag if document.no_dtas_flag is not None else True
    document.no_dtas_flag = not current_value
    db.session.commit()
    return jsonify({'success': True, 'no_dtas_flag': document.no_dtas_flag})


@main.route('/decline_document/<int:document_id>', methods=['POST'])
@login_required
def decline_document(document_id):
    listing_args = _dashboard_listing_args(default_view='received')
    document = Document.query.get_or_404(document_id)

    if document.recipient != current_user:
        flash('You are not authorized to decline this document.', 'danger')
        return _dashboard_redirect(view=listing_args['view'], page=listing_args['page'])

    form = DeclineDocumentForm()
    if form.validate_on_submit():
        document.status = 'Declined'
        document.remarks = form.reason.data

        db.session.add(Notification(
            user=document.creator,
            message=f"Your document '{document.title}' has been declined. Reason: {form.reason.data}",
        ))
        db.session.add(ActivityLog(
            user=current_user,
            document_id=document.id,
            action='Declined',
            remarks=form.reason.data,
        ))
        db.session.commit()

        flash('Document declined successfully.', 'success')
        return redirect(url_for('main.dashboard', page=listing_args['page']))

    flash('There was an error declining the document. Please check the form and try again.', 'danger')
    return redirect(url_for('main.dashboard', page=listing_args['page']))


@main.route('/forward_document/<int:document_id>', methods=['POST'])
@login_required
def forward_document(document_id):
    listing_args = _dashboard_listing_args(default_view='received')
    document = Document.query.get_or_404(document_id)

    if document.recipient != current_user:
        flash('You are not authorized to forward this document.', 'danger')
        return _dashboard_redirect(view=listing_args['view'], page=listing_args['page'])

    if document.status not in ['Accepted', 'Forwarded']:
        flash('Document must be accepted before forwarding.', 'warning')
        return redirect(url_for('main.dashboard'))

    form = ForwardDocumentForm()
    form.recipient.choices = get_recipient_choices()

    if form.validate_on_submit():
        try:
            new_recipient_id = form.recipient.data
            document.recipient_id = new_recipient_id
            document.status = 'Pending'
            document.action_taken = form.action_taken.data
            document.remarks = form.remarks.data
            document.forwarded_timestamp = datetime.utcnow()

            new_recipient_user = User.query.get(new_recipient_id)
            db.session.add(Notification(
                user=new_recipient_user,
                message=f"Document '{document.title}' has been forwarded to you by {current_user.username}",
            ))
            db.session.add(ActivityLog(
                user=current_user,
                document_id=document.id,
                action='Forwarded',
                remarks=f'Forwarded to {new_recipient_user.username}',
            ))

            processing_log = (
                ProcessingLog.query
                .filter_by(document_id=document.id, forwarded_timestamp=None)
                .order_by(ProcessingLog.accepted_timestamp.desc())
                .first()
            )
            if processing_log:
                processing_log.forwarded_timestamp = datetime.utcnow()
            else:
                db.session.add(ProcessingLog(
                    user_id=current_user.id,
                    document_id=document.id,
                    accepted_timestamp=datetime.utcnow(),
                    forwarded_timestamp=datetime.utcnow(),
                ))

            db.session.commit()
            flash('Document forwarded successfully.', 'success')
        except Exception as exc:
            db.session.rollback()
            flash(f'Error forwarding document: {str(exc)}', 'danger')

        return _dashboard_redirect(view='received', page=listing_args['page'])

    return redirect(url_for('main.dashboard', page=listing_args['page']))


@main.route('/resubmit_document/<int:document_id>', methods=['POST'])
@login_required
def resubmit_document(document_id):
    listing_args = _dashboard_listing_args(default_view='created')
    document = Document.query.get_or_404(document_id)
    form = ResubmitDocumentForm()

    if document.creator != current_user:
        flash('You are not authorized to resubmit this document.', 'danger')
        return _dashboard_redirect(view=listing_args['view'], page=listing_args['page'])

    if document.status != 'Declined':
        flash('This document cannot be resubmitted because it is not declined.', 'warning')
        return redirect(url_for('main.dashboard'))

    if form.validate_on_submit():
        try:
            document.status = 'Pending'
            document.action_taken = form.action_taken.data
            document.remarks = form.remarks.data

            db.session.add(ActivityLog(
                user=current_user,
                document_id=document.id,
                action='Resubmitted',
                remarks=form.remarks.data,
            ))
            db.session.commit()

            flash('Document resubmitted successfully.', 'success')
        except Exception as exc:
            db.session.rollback()
            flash(f'Error resubmitting document: {str(exc)}', 'danger')

    return redirect(url_for('main.dashboard'))


@main.route('/archive_document/<int:document_id>', methods=['POST'])
@login_required
def archive_document(document_id):
    document = Document.query.get_or_404(document_id)

    if document.creator != current_user and document.recipient != current_user:
        flash('You are not authorized to archive this document.', 'danger')
        return redirect(url_for('main.dashboard'))

    try:
        document.status = 'Archived'
        db.session.add(ActivityLog(
            user=current_user,
            document_id=document.id,
            action='Archived',
            remarks='Document archived',
        ))
        db.session.commit()

        flash('Document archived successfully.', 'success')
        return redirect(url_for('main.archive'))
    except Exception as exc:
        db.session.rollback()
        flash(f'Error archiving document: {str(exc)}', 'danger')
        return redirect(url_for('main.dashboard'))


@main.route('/unarchive_document/<int:document_id>', methods=['POST'])
@login_required
def unarchive_document(document_id):
    document = Document.query.get_or_404(document_id)

    if document.creator != current_user and document.recipient != current_user:
        flash('You are not authorized to unarchive this document.', 'danger')
        return redirect(url_for('main.archive'))

    try:
        document.status = 'Pending'
        db.session.commit()

        db.session.add(ActivityLog(
            user=current_user,
            document_id=document.id,
            action='Unarchived',
            remarks='Document restored from archive',
        ))
        db.session.commit()

        flash('Document unarchived successfully.', 'success')
        return redirect(url_for('main.dashboard'))
    except Exception as exc:
        db.session.rollback()
        flash(f'Error unarchiving document: {str(exc)}', 'danger')
        return redirect(url_for('main.archive'))


@main.route('/batch_accept_documents', methods=['POST'])
@login_required
def batch_accept_documents():
    """Accept multiple documents at once."""
    listing_args = _dashboard_listing_args(default_view='received')
    document_ids = request.form.getlist('document_ids')
    if not document_ids:
        flash('No documents selected for batch accept.', 'warning')
        return _dashboard_redirect(**listing_args)

    try:
        document_ids = [int(doc_id) for doc_id in document_ids]
    except ValueError:
        flash('Invalid document selection.', 'danger')
        return _dashboard_redirect(**listing_args)

    success_count = 0
    error_count = 0

    for doc_id in document_ids:
        try:
            document = Document.query.get(doc_id)
            if not document:
                error_count += 1
                continue

            if document.recipient != current_user:
                error_count += 1
                continue

            if document.status not in ['Pending', 'Forwarded']:
                error_count += 1
                continue

            document.status = 'Accepted'
            document.accepted_timestamp = datetime.utcnow()

            db.session.add(Notification(
                user=document.creator,
                message=f"Your document '{document.title}' has been accepted by {current_user.username}",
            ))
            db.session.add(ActivityLog(
                user=current_user,
                document_id=document.id,
                action='Batch Accepted',
                remarks='Document accepted via batch operation',
            ))
            db.session.add(ProcessingLog(
                user_id=current_user.id,
                document_id=document.id,
                accepted_timestamp=datetime.utcnow(),
            ))

            success_count += 1
        except Exception as exc:
            error_count += 1
            current_app.logger.error(f'Error in batch accept for document {doc_id}: {str(exc)}')

    try:
        db.session.commit()
        if success_count > 0:
            flash(f'Successfully accepted {success_count} document(s).', 'success')
        if error_count > 0:
            flash(f'Failed to accept {error_count} document(s).', 'warning')
    except Exception as exc:
        db.session.rollback()
        flash(f'Error processing batch accept: {str(exc)}', 'danger')

    return _dashboard_redirect(**listing_args)


@main.route('/batch_decline_documents', methods=['POST'])
@login_required
def batch_decline_documents():
    """Decline multiple documents at once."""
    listing_args = _dashboard_listing_args(default_view='received')
    form = BatchDeclineDocumentForm()

    if not form.validate_on_submit():
        flash('Please provide a reason for declining the documents.', 'danger')
        return _dashboard_redirect(**listing_args)

    document_ids = request.form.getlist('document_ids')
    if not document_ids:
        flash('No documents selected for batch decline.', 'warning')
        return _dashboard_redirect(**listing_args)

    try:
        document_ids = [int(doc_id) for doc_id in document_ids]
    except ValueError:
        flash('Invalid document selection.', 'danger')
        return _dashboard_redirect(**listing_args)

    success_count = 0
    error_count = 0
    reason = form.reason.data

    for doc_id in document_ids:
        try:
            document = Document.query.get(doc_id)
            if not document:
                error_count += 1
                continue

            if document.recipient != current_user:
                error_count += 1
                continue

            document.status = 'Declined'
            document.remarks = reason

            db.session.add(Notification(
                user=document.creator,
                message=f"Your document '{document.title}' has been declined. Reason: {reason}",
            ))
            db.session.add(ActivityLog(
                user=current_user,
                document_id=document.id,
                action='Batch Declined',
                remarks=reason,
            ))

            success_count += 1
        except Exception as exc:
            error_count += 1
            current_app.logger.error(f'Error in batch decline for document {doc_id}: {str(exc)}')

    try:
        db.session.commit()
        if success_count > 0:
            flash(f'Successfully declined {success_count} document(s).', 'success')
        if error_count > 0:
            flash(f'Failed to decline {error_count} document(s).', 'warning')
    except Exception as exc:
        db.session.rollback()
        flash(f'Error processing batch decline: {str(exc)}', 'danger')

    return _dashboard_redirect(**listing_args)


@main.route('/batch_forward_documents', methods=['POST'])
@login_required
def batch_forward_documents():
    """Forward multiple documents at once."""
    listing_args = _dashboard_listing_args(default_view='received')
    form = BatchForwardDocumentForm()
    form.recipient.choices = get_recipient_choices()

    if not form.validate_on_submit():
        flash('Please provide valid recipient and action for forwarding the documents.', 'danger')
        return _dashboard_redirect(**listing_args)

    document_ids = request.form.getlist('document_ids')
    if not document_ids:
        flash('No documents selected for batch forward.', 'warning')
        return _dashboard_redirect(**listing_args)

    try:
        document_ids = [int(doc_id) for doc_id in document_ids]
    except ValueError:
        flash('Invalid document selection.', 'danger')
        return _dashboard_redirect(**listing_args)

    success_count = 0
    error_count = 0
    new_recipient_id = form.recipient.data
    action_taken = form.action_taken.data
    remarks = form.remarks.data

    new_recipient_user = User.query.get(new_recipient_id)
    if not new_recipient_user:
        flash('Invalid recipient selected.', 'danger')
        return _dashboard_redirect(**listing_args)

    for doc_id in document_ids:
        try:
            document = Document.query.get(doc_id)
            if not document:
                error_count += 1
                continue

            if document.recipient != current_user:
                error_count += 1
                continue

            if document.status not in ['Accepted', 'Forwarded']:
                error_count += 1
                continue

            document.recipient_id = new_recipient_id
            document.status = 'Pending'
            document.action_taken = action_taken
            document.remarks = remarks
            document.forwarded_timestamp = datetime.utcnow()

            db.session.add(Notification(
                user=new_recipient_user,
                message=f"Document '{document.title}' has been forwarded to you by {current_user.username}",
            ))
            db.session.add(ActivityLog(
                user=current_user,
                document_id=document.id,
                action='Batch Forwarded',
                remarks=f'Forwarded to {new_recipient_user.username}',
            ))

            processing_log = (
                ProcessingLog.query
                .filter_by(document_id=document.id, forwarded_timestamp=None)
                .order_by(ProcessingLog.accepted_timestamp.desc())
                .first()
            )
            if processing_log:
                processing_log.forwarded_timestamp = datetime.utcnow()
            else:
                db.session.add(ProcessingLog(
                    user_id=current_user.id,
                    document_id=document.id,
                    accepted_timestamp=datetime.utcnow(),
                    forwarded_timestamp=datetime.utcnow(),
                ))

            success_count += 1
        except Exception as exc:
            error_count += 1
            current_app.logger.error(f'Error in batch forward for document {doc_id}: {str(exc)}')

    try:
        db.session.commit()
        if success_count > 0:
            flash(
                f'Successfully forwarded {success_count} document(s) to {new_recipient_user.username}.',
                'success',
            )
        if error_count > 0:
            flash(f'Failed to forward {error_count} document(s).', 'warning')
    except Exception as exc:
        db.session.rollback()
        flash(f'Error processing batch forward: {str(exc)}', 'danger')

    return _dashboard_redirect(**listing_args)


@main.route('/batch_release_documents', methods=['POST'])
@login_required
def batch_release_documents():
    """Release multiple documents at once."""
    listing_args = _dashboard_listing_args(default_view='received')
    document_ids = request.form.getlist('document_ids')
    if not document_ids:
        flash('No documents selected for batch release.', 'warning')
        return _dashboard_redirect(**listing_args)

    try:
        document_ids = [int(doc_id) for doc_id in document_ids]
    except ValueError:
        flash('Invalid document selection.', 'danger')
        return _dashboard_redirect(**listing_args)

    success_count = 0
    error_count = 0

    for doc_id in document_ids:
        try:
            document = Document.query.get(doc_id)
            if not document:
                error_count += 1
                continue

            if document.recipient != current_user:
                error_count += 1
                continue

            document.status = 'Released'
            document.released_timestamp = datetime.utcnow()

            db.session.add(Notification(
                user=document.creator,
                message=f"Your document '{document.title}' has been released.",
            ))
            db.session.add(ActivityLog(
                user=current_user,
                document_id=document.id,
                action='Batch Released',
                remarks='Document released via batch operation',
            ))

            success_count += 1
        except Exception as exc:
            error_count += 1
            current_app.logger.error(f'Error in batch release for document {doc_id}: {str(exc)}')

    try:
        db.session.commit()
        if success_count > 0:
            flash(f'Successfully released {success_count} document(s).', 'success')
        if error_count > 0:
            flash(f'Failed to release {error_count} document(s).', 'warning')
    except Exception as exc:
        db.session.rollback()
        flash(f'Error processing batch release: {str(exc)}', 'danger')

    return _dashboard_redirect(**listing_args)
