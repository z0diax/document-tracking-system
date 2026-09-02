from flask import current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from app import db
from app.forms import LoginForm, RegistrationForm
from app.models import Notification, User
from app.route_modules.shared import main


@main.route('/')
@main.route('/home')
def home():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('main.admin_dashboard'))
        return redirect(url_for('main.overview'))

    login_form = LoginForm()
    register_form = RegistrationForm()
    return render_template('home.html', login_form=login_form, register_form=register_form)


@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    register_form = RegistrationForm()
    login_form = LoginForm()

    if register_form.validate_on_submit():
        try:
            user = User(
                username=register_form.username.data,
                email=register_form.email.data,
                password_hash=generate_password_hash(register_form.password.data),
                is_admin=False,
                status='Pending',
            )

            db.session.add(user)
            db.session.commit()

            try:
                admins = User.query.filter(User.is_admin == True).all()
                if admins:
                    for admin in admins:
                        notif_msg = f"New account '{user.username}' is awaiting approval."
                        db.session.add(Notification(user_id=admin.id, message=notif_msg))
                    db.session.commit()
                    try:
                        current_app.logger.info(
                            "Admin notifications created for new user '%s' for %s admin(s).",
                            user.username,
                            len(admins),
                        )
                    except Exception:
                        pass
                else:
                    try:
                        current_app.logger.info(
                            "No admin users found to notify for new user '%s'.",
                            user.username,
                        )
                    except Exception:
                        pass
            except Exception as notify_err:
                db.session.rollback()
                try:
                    current_app.logger.warning(
                        "Failed to create admin notifications for new user %s: %s",
                        user.username,
                        notify_err,
                    )
                except Exception:
                    pass

            flash('Registration successful! Your account is pending for approval by an administrator.', 'info')
            return redirect(url_for('main.home'))

        except IntegrityError:
            db.session.rollback()
            flash('Registration failed. Please review your username and email, then try again.', 'danger')
        except Exception as exc:
            db.session.rollback()
            current_app.logger.exception('Registration error')
            flash('Registration failed. Please try again.', 'danger')

    elif register_form.errors:
        for field, errors in register_form.errors.items():
            for error in errors:
                flash(f'Error in {field}: {error}', 'danger')

    return render_template('home.html', register_form=register_form, login_form=login_form)


@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('main.admin_dashboard'))
        return redirect(url_for('main.overview'))

    login_form = LoginForm()
    register_form = RegistrationForm()

    if login_form.validate_on_submit():
        user = User.query.filter_by(username=login_form.username.data).first()

        if user and user.check_password(login_form.password.data):
            if user.status != 'Active':
                if user.status == 'Pending':
                    flash('Your account is pending for approval by the system administrator.', 'warning')
                elif user.status in ['Disabled', 'Declined']:
                    flash(
                        'Your account has been disabled or declined. Please contact the system administrator.',
                        'danger',
                    )
                else:
                    flash('Account has an invalid status. Please contact the administrator.', 'danger')

                return render_template('home.html', login_form=login_form, register_form=register_form)

            login_result = login_user(user, remember=login_form.remember.data)
            if not login_result:
                flash('Login failed. Your account may be inactive.', 'danger')
                return render_template('home.html', login_form=login_form, register_form=register_form)

            if user.is_admin:
                return redirect(url_for('main.admin_dashboard'))
            return redirect(url_for('main.overview'))
        else:
            flash('Login unsuccessful. Please check your username and password.', 'danger')

    return render_template('home.html', login_form=login_form, register_form=register_form)


@main.route('/logout')
def logout():
    try:
        if current_user.is_authenticated:
            logout_user()
            flash('You have been logged out.', 'success')
        return redirect(url_for('main.home'))
    except Exception as exc:
        current_app.logger.error(f'Error during logout: {str(exc)}')
        flash('An error occurred during logout.', 'danger')
        return redirect(url_for('main.home')), 302


@main.route('/mark_notification_as_read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_as_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)

    if notification.user != current_user:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    notification.is_read = True
    db.session.commit()

    unread_count = Notification.query.filter_by(user=current_user, is_read=False).count()
    return jsonify({'success': True, 'unread_count': unread_count})


@main.route('/mark_all_notifications_as_read', methods=['POST'])
@login_required
def mark_all_notifications_as_read():
    try:
        unread_notifications = Notification.query.filter_by(user=current_user, is_read=False).all()

        for notification in unread_notifications:
            notification.is_read = True
        db.session.commit()
        flash('All notifications marked as read.', 'success')
    except Exception:
        db.session.rollback()
        flash('Error marking notifications as read.', 'danger')
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('main.dashboard'))


@main.route('/delete_all_notifications', methods=['POST'])
@login_required
def delete_all_notifications():
    try:
        Notification.query.filter_by(user=current_user).delete()
        db.session.commit()
        return jsonify({'success': True, 'unread_count': 0})
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception('Failed to delete notifications: %s', exc)
        return jsonify({'success': False, 'error': 'Failed to delete notifications.'}), 500


@main.route('/check_username', methods=['POST'])
def check_username():
    try:
        username = request.form.get('username', '').strip()

        if not username:
            return jsonify({'valid': False, 'message': 'Username is required'})

        if len(username) < 3:
            return jsonify({'valid': False, 'message': 'Username must be at least 3 characters long'})

        return jsonify({
            'valid': True,
            'message': 'Username format looks good. Availability is checked on submit.',
        })

    except Exception as exc:
        current_app.logger.exception('Error checking username format: %s', exc)
        return jsonify({'valid': False, 'message': 'Unable to validate username right now.'}), 500


@main.route('/check_email', methods=['POST'])
def check_email():
    try:
        email = request.form.get('email', '').strip()

        if not email:
            return jsonify({'valid': False, 'message': 'Email is required'})

        if '@' not in email or '.' not in email:
            return jsonify({'valid': False, 'message': 'Invalid email format'})

        return jsonify({
            'valid': True,
            'message': 'Email format looks good. Availability is checked on submit.',
        })

    except Exception as exc:
        current_app.logger.exception('Error checking email format: %s', exc)
        return jsonify({'valid': False, 'message': 'Unable to validate email right now.'}), 500


@main.route('/check_account_status', methods=['POST'])
def check_account_status():
    """Return a generic login guidance response without revealing account state."""
    return jsonify({
        'message': 'If the account exists, sign in to continue or contact an administrator for access issues.',
    })


@main.route('/notifications', methods=['GET'])
@login_required
def get_notifications():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    pagination = (
        Notification.query.filter_by(user=current_user, is_read=False)
        .order_by(Notification.timestamp.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    notifications = pagination.items
    data = {
        'notifications': [
            {
                'id': notification.id,
                'message': notification.message,
                'timestamp': notification.timestamp.isoformat(),
                'is_read': notification.is_read,
            }
            for notification in notifications
        ],
        'has_next': pagination.has_next,
        'next_page': pagination.next_num if pagination.has_next else None,
    }
    return jsonify(data)
