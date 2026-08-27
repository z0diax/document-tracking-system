from flask import flash, redirect, request, url_for
from flask_login import current_user, login_required

from app import db
from app.auto_archive import archive_old_documents
from app.route_modules.admin_dashboard_render import render_admin_dashboard
from app.route_modules.shared import main


@main.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('You are not authorized to access the admin dashboard.', 'danger')
        return redirect(url_for('main.dashboard'))

    return render_admin_dashboard(
        doc_page=request.args.get('doc_page', 1, type=int),
        activity_page=request.args.get('activity_page', 1, type=int),
        user_page=request.args.get('user_page', 1, type=int),
        search_query=request.args.get('search', '').strip(),
    )


@main.route('/admin/archive-last-month-documents', methods=['POST'])
@login_required
def admin_archive_last_month_documents():
    if not current_user.is_admin:
        flash('You are not authorized to archive documents from the admin dashboard.', 'danger')
        return redirect(url_for('main.dashboard'))

    try:
        archived_count = archive_old_documents()
        if archived_count == 0:
            flash('No documents from last month or earlier were eligible for archiving.', 'info')
        else:
            flash(f'Archived {archived_count} document(s) from last month or earlier.', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(f'Error archiving last month documents: {str(exc)}', 'danger')

    return redirect(url_for('main.admin_dashboard', _anchor='overview'))
