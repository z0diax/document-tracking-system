from flask import flash, redirect, request, url_for
from flask_login import current_user, login_required

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
