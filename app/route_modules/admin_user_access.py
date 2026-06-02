from flask import jsonify
from flask_login import current_user, login_required

from app import db
from app.models import User
from app.route_modules.shared import main


@main.route('/admin/toggle_user_status/<int:user_id>', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    # Add debugging output to help diagnose issues
    print(f"Toggle user status called for user ID: {user_id}")

    if not current_user.is_admin:
        print("Unauthorized: Not an admin")
        return jsonify({'success': False, 'error': 'Unauthorized. Only administrators can modify user status.'}), 403

    try:
        user = User.query.get_or_404(user_id)
        print(f"Found user: {user.username}, current status: {user.status}")

        if user.id == current_user.id:
            print("Cannot toggle own account")
            return jsonify({'success': False, 'error': 'For security reasons, you cannot modify your own account status.'}), 400

        old_status = user.status
        if user.status == 'Active':
            user.status = 'Disabled'
        elif user.status == 'Disabled':
            user.status = 'Active'
        else:
            user.status = 'Active'

        print(f"Changing status from {old_status} to {user.status}")
        db.session.commit()

        print("Status change successful")
        return jsonify({
            'success': True,
            'newStatus': user.status,
            'oldStatus': old_status,
            'message': f"User status changed from {old_status} to {user.status}",
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error toggling user status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@main.route('/admin/toggle_rsp_tracker_access/<int:user_id>', methods=['POST'])
@login_required
def toggle_rsp_tracker_access(user_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized. Only administrators can modify RSP Tracker access.'}), 403

    try:
        user = User.query.get_or_404(user_id)

        if user.is_admin:
            return jsonify({
                'success': False,
                'error': 'Admin accounts always have RSP Tracker access.',
            }), 400

        user.can_see_rsp_tracker = not bool(user.can_see_rsp_tracker)
        db.session.commit()

        return jsonify({
            'success': True,
            'canSeeRspTracker': bool(user.can_see_rsp_tracker),
            'message': f"RSP Tracker access {'enabled' if user.can_see_rsp_tracker else 'disabled'} for {user.username}.",
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
