from datetime import datetime

from flask import jsonify
from flask_login import current_user, login_required

from app import db
from app.models import ActivityLog, Document, Notification, ProcessingLog, User, format_timedelta
from app.route_modules.shared import main


@main.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        print("Unauthorized deletion attempt by non-admin user:", current_user.username)
        return jsonify({'success': False, 'error': 'Unauthorized. Only administrators can delete user accounts.'}), 403

    try:
        print(f"Attempting to delete user ID: {user_id}")
        user = User.query.get_or_404(user_id)
        print(f"Found user: {user.username} (ID: {user.id})")

        if user.id == current_user.id:
            print(f"Admin {current_user.username} attempted to delete their own account")
            return jsonify({'success': False, 'error': 'You cannot delete your own account for security reasons.'}), 400

        document_count = Document.query.filter((Document.creator_id == user.id) | (Document.recipient_id == user.id)).count()
        if document_count > 0:
            print(f"Cannot delete user {user.username} - has {document_count} associated documents")
            return jsonify({
                'success': False,
                'error': f'Cannot delete this user because they have {document_count} associated documents. Transfer or delete these documents first.',
            }), 400

        try:
            notification_count = Notification.query.filter_by(user_id=user.id).count()
            if notification_count > 0:
                print(f"Deleting {notification_count} notifications for user {user.username}")
                Notification.query.filter_by(user_id=user.id).delete()
                print(f"Successfully deleted {notification_count} notifications")
        except Exception as notification_error:
            db.session.rollback()
            print(f"Error deleting notifications: {str(notification_error)}")
            return jsonify({'success': False, 'error': f'Error deleting notifications: {str(notification_error)}'}), 500

        try:
            log_count = ProcessingLog.query.filter_by(user_id=user.id).count()
            if log_count > 0:
                print(f"Deleting {log_count} processing logs for user {user.username}")
                ProcessingLog.query.filter_by(user_id=user.id).delete()
                print(f"Successfully deleted {log_count} processing logs")
        except Exception as log_error:
            db.session.rollback()
            print(f"Error deleting processing logs: {str(log_error)}")
            return jsonify({'success': False, 'error': f'Error deleting processing logs: {str(log_error)}'}), 500

        try:
            activity_count = ActivityLog.query.filter_by(user_id=user.id).count()
            if activity_count > 0:
                print(f"Deleting {activity_count} activity logs for user {user.username}")
                ActivityLog.query.filter_by(user_id=user.id).delete()
                print(f"Successfully deleted {activity_count} activity logs")
        except Exception as activity_error:
            db.session.rollback()
            print(f"Error deleting activity logs: {str(activity_error)}")
            return jsonify({'success': False, 'error': f'Error deleting activity logs: {str(activity_error)}'}), 500

        username = user.username
        db.session.delete(user)
        db.session.commit()
        print(f"User {username} successfully deleted")

        return jsonify({
            'success': True,
            'message': f'User {username} has been successfully deleted',
        })
    except Exception as e:
        db.session.rollback()
        error_message = str(e)
        print(f"Error deleting user: {error_message}")
        return jsonify({'success': False, 'error': f'An error occurred: {error_message}'}), 500


@main.route('/admin/approve_user/<int:user_id>', methods=['POST'])
@login_required
def approve_user(user_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    try:
        user = User.query.get_or_404(user_id)
        print(f"Found user to approve: {user.username}, current status: {user.status}")

        user.status = 'Active'
        db.session.commit()
        print("Successfully updated user status to Active")

        return jsonify({
            'success': True,
            'message': f"User {user.username} has been approved successfully.",
        })
    except Exception as e:
        db.session.rollback()
        error_message = str(e)
        print(f"Error in approve_user: {error_message}")
        return jsonify({'success': False, 'error': error_message}), 500


@main.route('/admin/decline_user/<int:user_id>', methods=['POST'])
@login_required
def decline_user(user_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    try:
        user = User.query.get_or_404(user_id)
        print(f"Found user to decline: {user.username}, current status: {user.status}")

        user.status = 'Disabled'
        db.session.commit()
        print("Successfully updated user status to Disabled")

        try:
            notification = Notification(
                user_id=user.id,
                message="Your account registration has been declined and disabled. Please contact the administrator for more information.",
            )
            db.session.add(notification)
            db.session.commit()
            print("Successfully created notification for user")
        except Exception as notification_error:
            print(f"Warning: Could not create notification: {str(notification_error)}")

        return jsonify({
            'success': True,
            'message': f"User {user.username} has been declined and disabled.",
        })
    except Exception as e:
        db.session.rollback()
        error_message = str(e)
        print(f"Error in decline_user: {error_message}")
        return jsonify({'success': False, 'error': error_message}), 500


@main.route('/admin/user_metrics/<int:user_id>', methods=['GET'])
@login_required
def user_metrics_details(user_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    try:
        user = User.query.get_or_404(user_id)

        today = datetime.utcnow().date()
        first_day_of_month = today.replace(day=1)

        documents_processed_this_month = db.session.query(
            db.func.count(ProcessingLog.id)
        ).filter(
            ProcessingLog.user_id == user_id,
            ProcessingLog.forwarded_timestamp != None,
            db.func.date(ProcessingLog.forwarded_timestamp) >= first_day_of_month,
        ).scalar() or 0

        avg_processing_time_seconds = db.session.query(
            db.func.avg(
                db.func.time_to_sec(
                    db.func.timediff(ProcessingLog.forwarded_timestamp, ProcessingLog.accepted_timestamp)
                )
            )
        ).filter(
            ProcessingLog.user_id == user_id,
            ProcessingLog.forwarded_timestamp != None,
        ).scalar()

        monthly_avg_processing_time_seconds = db.session.query(
            db.func.avg(
                db.func.time_to_sec(
                    db.func.timediff(ProcessingLog.forwarded_timestamp, ProcessingLog.accepted_timestamp)
                )
            )
        ).filter(
            ProcessingLog.user_id == user_id,
            ProcessingLog.forwarded_timestamp != None,
            db.func.date(ProcessingLog.forwarded_timestamp) >= first_day_of_month,
        ).scalar()

        documents_created_overall = Document.query.filter_by(creator_id=user_id).count()
        documents_created_this_month = Document.query.filter(
            Document.creator_id == user_id,
            db.func.date(Document.timestamp) >= first_day_of_month,
        ).count()

        avg_sec = int(avg_processing_time_seconds) if avg_processing_time_seconds else 0
        monthly_avg_sec = int(monthly_avg_processing_time_seconds) if monthly_avg_processing_time_seconds else 0

        return jsonify({
            'success': True,
            'user': {'id': user.id, 'username': user.username},
            'documents_processed_this_month': int(documents_processed_this_month),
            'documents_created_overall': documents_created_overall,
            'documents_created_this_month': documents_created_this_month,
            'average_processing_time_seconds': avg_sec,
            'average_processing_time_formatted': format_timedelta(avg_sec),
            'monthly_average_processing_time_seconds': monthly_avg_sec,
            'monthly_average_processing_time_formatted': format_timedelta(monthly_avg_sec),
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
