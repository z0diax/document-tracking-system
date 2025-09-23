from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session, jsonify, make_response, render_template_string, send_from_directory, abort
from flask_login import login_user, current_user, logout_user, login_required
from app import db
from app.forms import RegistrationForm, LoginForm, DocumentForm, DeclineDocumentForm, ForwardDocumentForm, ResubmitDocumentForm, LeaveRequestForm, EWPForm, EmployeeForm, LEAVE_TYPE_CHOICES, BatchDeclineDocumentForm, BatchForwardDocumentForm
from app.models import User, Document, ActivityLog, Notification, LeaveRequest, LeaveDateRange, EWPRecord, Employee, to_local_time, format_timedelta

from werkzeug.utils import secure_filename
from datetime import timedelta, datetime
import os
import csv
import pytz
from sqlalchemy import or_, case, extract, and_, text
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import OperationalError, ProgrammingError
import json
from werkzeug.security import generate_password_hash, check_password_hash
import mimetypes
from app.utils import get_upload_path, get_file_url, calculate_business_hours
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

# form choices
OFFICE_CHOICES = [
('CMO','CMO'),('CMO - CARPOOL','CMO - CARPOOL'),('CMO - YOUTH','CMO - YOUTH'),('CMO - NORTH','CMO - NORTH'),('CMO - SUPPLY','CMO - SUPPLY'),
('CADMO','CADMO'),('SP','SP'),('CPDO','CPDO'),('CLGOO','CLGOO'),('CTO','CTO'),('CAO','CAO'),('CASSO','CASSO'),('CBO','CBO'),('HRMDO','HRMDO'),('CCRO','CCRO'),
('CDO','CDO'),('CHO','CHO'),('TCH','TCH'),('CPO','CPO'),('CSWDO','CSWDO'),('CEO','CEO'),('CARCHTO','CARCHTO'),('CGSO','CGSO'),('CENRO','CENRO'),('CAGRIO','CAGRIO'),
('CVO','CVO'),('EED','EED'),('CIAS','CIAS'),('TOMECO','TOMECO'),('CIO','CIO'),('CHCDO','CHCDO'),('CDRRMO','CDRRMO'),('CCDLAO','CCDLAO'),('CTOO','CTOO'),('CLO','CLO'),
('CMISO','CMISO'),('CLEP','CLEP'),('SPORTS','SPORTS'),('BPLD','BPLD'),('FLET','FLET'),('TACRU','TACRU'),('CNO','CNO'),('TNSH','TNSH'),('PDAO','PDAO'),('OSCA','OSCA'),
('TCPO','TCPO'),('PESO','PESO'),('TCCC','TCCC'),('TNBT','TNBT'),('BAC','BAC'), ('DILG', 'DILG')
]

CLASSIFICATION_CHOICES = [
    ('Communications', 'Communications'), 
    ('Payroll', 'Payroll'), 
    ('Request', 'Request'),
    ('Others', 'Others')
]

STATUS_CHOICES = [('For Checking', 'For Checking'), ('For Signature', 'For Signature'), ('Pending', 'Pending'), ('Declined', 'Declined')]

ACTION_TAKEN_CHOICES = [
    ('Noted', 'Noted'), 
    ('Signed', 'Signed'), 
    ('Approved', 'Approved'), 
    ('Verified', 'Verified'), 
    ('For Review', 'For Review'), 
    ('For Revision', 'For Revision'), 
    ('For Approval', 'For Approval'), 
    ('Endorsed', 'Endorsed')
]

main = Blueprint('main', __name__)

# function to set recipient choices
def get_recipient_choices():
    """Return list of recipient choices excluding current user"""
    if not current_user.is_authenticated:
        return []
    return [(user.id, user.username) for user in User.query.filter(User.id != current_user.id).all()]

# Employee Records routes

@main.route('/employees')
@login_required
def employee_list():
    # Initialize Employee form for Add/Edit modals and make available even on errors
    form = EmployeeForm()
    form.office.choices = OFFICE_CHOICES
    try:
        if not current_user.is_admin:
            flash('You are not authorized to access Employee Records.', 'danger')
            return redirect(url_for('main.dashboard'))

        search_query = request.args.get('search', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = 10

        try:
            query = Employee.query

            if search_query:
                query = query.filter(
                    or_(
                        Employee.employee_name.ilike(f'%{search_query}%'),
                        Employee.bio_number.ilike(f'%{search_query}%'),
                        Employee.office.ilike(f'%{search_query}%'),
                        Employee.position.ilike(f'%{search_query}%'),
                        Employee.status.ilike(f'%{search_query}%')
                    )
                )

            pagination = query.order_by(Employee.bio_number.asc()).paginate(page=page, per_page=per_page, error_out=False)
            employees = pagination.items
        except (OperationalError, ProgrammingError) as e:
            try:
                current_app.logger.error(f"Employee list DB error: {e}")
            except Exception:
                pass
            flash('Employee module is not initialized in the database. Please run migrations.', 'warning')
            pagination = None
            employees = []

        return render_template('employee_records.html',
                               title='Onboarding',
                               employees=employees,
                               pagination=pagination,
                               search_query=search_query,
                               form=form)
    except Exception as e:
        try:
            current_app.logger.error(f"Unexpected error in /employees: {e}")
        except Exception:
            pass
        flash('Unexpected error loading Employee Records.', 'danger')
        # Best-effort fallback render
        return render_template('employee_records.html',
                               title='Onboarding',
                               employees=[],
                               pagination=None,
                               search_query=request.args.get('search', '').strip(),
                               form=form)

@main.route('/employees/add', methods=['GET', 'POST'])
@login_required
def add_employee():
    if not current_user.is_admin:
        flash('You are not authorized to add employees.', 'danger')
        return redirect(url_for('main.employee_list'))

    form = EmployeeForm()
    form.office.choices = OFFICE_CHOICES

    if form.validate_on_submit():
        try:
            existing = Employee.query.filter_by(bio_number=form.bio_number.data.strip()).first()
            if existing:
                flash(f'Biometric number is already taken by employee {existing.employee_name}.', 'danger')
                return redirect(url_for('main.employee_list'))

            employee = Employee(
                bio_number=form.bio_number.data.strip(),
                employee_name=form.employee_name.data.strip(),
                office=form.office.data,
                position=form.position.data,
                status=form.status.data
            )
            db.session.add(employee)
            db.session.commit()
            flash('Employee added successfully.', 'success')
            return redirect(url_for('main.employee_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding employee: {str(e)}', 'danger')

    return render_template('employee_form.html', title='Add Employee', form=form)

@main.route('/employees/edit/<int:employee_id>', methods=['GET', 'POST'])
@login_required
def edit_employee(employee_id):
    if not current_user.is_admin:
        flash('You are not authorized to edit employees.', 'danger')
        return redirect(url_for('main.employee_list'))

    employee = Employee.query.get_or_404(employee_id)
    form = EmployeeForm(obj=employee)
    form.office.choices = OFFICE_CHOICES

    if form.validate_on_submit():
        try:
            # Check for duplicate bio_number if changed
            if employee.bio_number != form.bio_number.data.strip():
                existing = Employee.query.filter_by(bio_number=form.bio_number.data.strip()).first()
                if existing:
                    flash(f'Biometric number is already taken by employee {existing.employee_name}.', 'danger')
                    return redirect(url_for('main.employee_list'))

            employee.bio_number = form.bio_number.data.strip()
            employee.employee_name = form.employee_name.data.strip()
            employee.office = form.office.data
            employee.position = form.position.data
            employee.status = form.status.data

            db.session.commit()
            flash('Employee updated successfully.', 'success')
            return redirect(url_for('main.employee_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating employee: {str(e)}', 'danger')

    return render_template('employee_form.html', title='Edit Employee', form=form, employee=employee)

@main.route('/employees/delete/<int:employee_id>', methods=['POST'])
@login_required
def delete_employee(employee_id):
    if not current_user.is_admin:
        flash('You are not authorized to delete employees.', 'danger')
        return redirect(url_for('main.employee_list'))

    employee = Employee.query.get_or_404(employee_id)
    try:
        db.session.delete(employee)
        db.session.commit()
        flash('Employee deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting employee: {str(e)}', 'danger')

    return redirect(url_for('main.employee_list'))


@main.route('/employees/check_bio_number', methods=['POST'])
@login_required
def check_bio_number():
    """Validate Employee biometric (bio_number) availability. Optional exclude_id for edit forms."""
    if not current_user.is_admin:
        return jsonify({'valid': False, 'message': 'Unauthorized'}), 403
    try:
        bio = (request.form.get('bio_number') or '').strip()
        exclude_id = request.form.get('exclude_id', type=int)
        if not bio:
            return jsonify({'valid': False, 'message': 'Biometric number is required'})
        existing = Employee.query.filter_by(bio_number=bio).first()
        if existing and (exclude_id is None or existing.id != exclude_id):
            return jsonify({
                'valid': False,
                'message': f'Biometric number is already taken by employee {existing.employee_name}',
                'employee_name': existing.employee_name
            })
        return jsonify({'valid': True, 'message': 'Biometric number is available'})
    except Exception as e:
        try:
            current_app.logger.error(f"Error in check_bio_number: {e}")
        except Exception:
            pass
        return jsonify({'valid': False, 'message': 'Server error'}), 500


@main.app_template_filter('escapejs')
def escapejs_filter(value):
    return json.dumps(value)[1:-1] 

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
            # Simplest approach possible - create user directly from form
            user = User(
                username=register_form.username.data,
                email=register_form.email.data,
                password_hash=generate_password_hash(register_form.password.data),
                is_admin=False,
                status='Pending'
            )
            
            db.session.add(user)
            db.session.commit()

            print(f"User registered successfully: {user.username} (status: {user.status})")

            # Notify all admins about the new pending user
            try:
                admins = User.query.filter(User.is_admin == True).all()
                if admins:
                    for admin in admins:
                        notif_msg = f"New account '{user.username}' is awaiting approval."
                        # Use user_id explicitly to avoid any potential relationship issues
                        db.session.add(Notification(user_id=admin.id, message=notif_msg))
                    db.session.commit()
                    try:
                        current_app.logger.info(f"Admin notifications created for new user '{user.username}' for {len(admins)} admin(s).")
                    except Exception:
                        pass
                else:
                    try:
                        current_app.logger.info(f"No admin users found to notify for new user '{user.username}'.")
                    except Exception:
                        pass
            except Exception as notify_err:
                # Roll back only the notification transaction so user creation remains intact
                db.session.rollback()
                try:
                    current_app.logger.warning(f"Failed to create admin notifications for new user {user.username}: {notify_err}")
                except Exception:
                    pass
            
            flash("Registration successful! Your account is pending for approval by an administrator.", "info")
            return redirect(url_for("main.home"))
            
        except Exception as e:
            db.session.rollback()
            error_message = str(e)
            print(f"Registration error: {error_message}")
            flash(f"Registration failed: {error_message}", "danger")
    
    elif register_form.errors:
        for field, errors in register_form.errors.items():
            for error in errors:
                flash(f"Error in {field}: {error}", "danger")
    
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
            # debug output
            print(f"DEBUG: User '{user.username}' trying to log in with status '{user.status}'")
            
            # STRICT status check - only 'Active' users allowed
            if user.status != 'Active':
                if user.status == 'Pending':
                    flash('Your account is pending for approval by the system administrator.', 'warning')
                    print(f"DEBUG: Login rejected - User '{user.username}' has 'Pending' status")
                elif user.status in ['Disabled', 'Declined']:
                    flash('Your account has been disabled or declined. Please contact the system administrator.', 'danger')
                    print(f"DEBUG: Login rejected - User '{user.username}' has '{user.status}' status")
                else:
                    flash('Account has an invalid status. Please contact the administrator.', 'danger')
                    print(f"DEBUG: Login rejected - User '{user.username}' has invalid status '{user.status}'")
                
                return render_template('home.html', login_form=login_form, register_form=register_form)
            
            # If status is 'Active', proceed with login
            print(f"DEBUG: User '{user.username}' confirmed Active, attempting login")
            
            login_result = login_user(user, remember=login_form.remember.data)
            if not login_result:
                flash('Login failed. Your account may be inactive.', 'danger')
                print(f"DEBUG: Flask-login rejected user '{user.username}' - login_user() returned False")
                return render_template('home.html', login_form=login_form, register_form=register_form)
            
            print(f"DEBUG: User '{user.username}' logged in successfully")
            
            if user.is_admin:
                return redirect(url_for('main.admin_dashboard'))
            return redirect(url_for('main.overview'))
        else:
            flash('Login unsuccessful. Please check your username and password.', 'danger')

    return render_template('home.html', login_form=login_form, register_form=register_form)

@main.route('/dashboard')
@login_required
def dashboard():
    page = request.args.get('page', 1, type=int)
    view = request.args.get('view', 'created')
    search_query = request.args.get('search', '').strip()
    per_page = 10

    # Restrict Leave view to permitted users
    if view == 'leave' and not current_user.can_access_leave:
        flash('You are not authorized to access the Leave section.', 'danger')
        return redirect(url_for('main.dashboard', view='created'))

    form = DocumentForm()
    decline_form = DeclineDocumentForm()
    forward_form = ForwardDocumentForm()
    
    # Initialize batch forms
    batch_decline_form = BatchDeclineDocumentForm()
    batch_forward_form = BatchForwardDocumentForm()
    
    form.office.choices = OFFICE_CHOICES
    form.classification.choices = CLASSIFICATION_CHOICES
    form.status.choices = STATUS_CHOICES
    form.action_taken.choices = ACTION_TAKEN_CHOICES
    form.recipient.choices = get_recipient_choices()
    
    forward_form.recipient.choices = get_recipient_choices()
    batch_forward_form.recipient.choices = get_recipient_choices()
    
    created_query = Document.query.filter(
        Document.creator_id == current_user.id,
        Document.status != 'Archived'
    )
    
    received_query = Document.query.options(joinedload(Document.creator)).filter(
        Document.recipient_id == current_user.id,
        Document.status != 'Archived'
    )
    
    if search_query:
        if view == 'received':
            received_query = received_query.filter(
                or_(
                    Document.title.ilike(f'%{search_query}%'),
                    Document.office.ilike(f'%{search_query}%'),
                    Document.classification.ilike(f'%{search_query}%'),
                    or_(
                        Document.barcode.ilike(f'%{search_query}%'),
                        Document.barcode == search_query
                    )
                )
            )
        else:  
            created_query = created_query.filter(
                or_(
                    Document.title.ilike(f'%{search_query}%'),
                    Document.office.ilike(f'%{search_query}%'),
                    Document.classification.ilike(f'%{search_query}%'),
                    or_(
                        Document.barcode.ilike(f'%{search_query}%'),
                        Document.barcode == search_query
                    )
                )
            )

    if view == 'received':
        received_pagination = received_query.order_by(Document.timestamp.desc()).paginate(
            page=page, per_page=per_page, error_out=False)
        received_documents = received_pagination.items
        created_pagination = None
        created_documents = []
    else:
        created_pagination = created_query.order_by(Document.timestamp.desc()).paginate(
            page=page, per_page=per_page, error_out=False)
        created_documents = created_pagination.items
        received_pagination = None
        received_documents = []

    for document in created_documents + received_documents:
        document.activities_json = [activity.to_dict() for activity in document.activities]

    # Prepare data for Leave view
    if view == 'leave':
        leave_form = LeaveRequestForm()
        leave_form.office.choices = OFFICE_CHOICES
        leave_form.leave_type.choices = LEAVE_TYPE_CHOICES

        # Initialize EWP form (for creation)
        ewp_form = EWPForm()
        ewp_form.office.choices = OFFICE_CHOICES

        try:
            leave_query = LeaveRequest.query
            if search_query:
                leave_query = leave_query.filter(
                    or_(
                        LeaveRequest.employee_name.ilike(f'%{search_query}%'),
                        LeaveRequest.office.ilike(f'%{search_query}%'),
                        LeaveRequest.leave_type.ilike(f'%{search_query}%'),
                        LeaveRequest.status.ilike(f'%{search_query}%'),
                        or_(
                            LeaveRequest.barcode.ilike(f'%{search_query}%'),
                            LeaveRequest.barcode == search_query
                        )
                    )
                )
            leave_query = leave_query.order_by(LeaveRequest.created_timestamp.desc())
            leave_pagination = leave_query.paginate(page=page, per_page=per_page, error_out=False)
            leave_requests = leave_pagination.items
            # Compute per-leave time-to-release visible only to the creator
            try:
                for l in leave_requests:
                    try:
                        if (getattr(l, 'released_timestamp', None) and getattr(l, 'created_timestamp', None)
                                and getattr(l, 'created_by_user_id', None) == current_user.id):
                            delta = calculate_business_hours(l.created_timestamp, l.released_timestamp)
                            l.release_delta_fmt = format_timedelta(delta)
                        else:
                            l.release_delta_fmt = None
                    except Exception:
                        l.release_delta_fmt = None
            except Exception:
                pass
        except (OperationalError, ProgrammingError) as e:
            current_app.logger.error(f"Leave view DB error: {e}")
            flash('Leave module is not initialized in the database. Please run migrations.', 'warning')
            leave_pagination = None
            leave_requests = []

        # EWP listing for Leave view tabbed table
        active_tab = request.args.get('tab', 'leave')
        try:
            ewp_query = EWPRecord.query
            if search_query:
                ewp_query = ewp_query.filter(
                    or_(
                        EWPRecord.employee_name.ilike(f'%{search_query}%'),
                        EWPRecord.office.ilike(f'%{search_query}%'),
                        EWPRecord.status.ilike(f'%{search_query}%'),
                        or_(
                            EWPRecord.barcode.ilike(f'%{search_query}%'),
                            EWPRecord.barcode == search_query
                        )
                    )
                )
            ewp_query = ewp_query.order_by(EWPRecord.created_timestamp.desc())
            ewp_pagination = ewp_query.paginate(page=page, per_page=per_page, error_out=False)
            ewp_records = ewp_pagination.items
        except (OperationalError, ProgrammingError) as e:
            current_app.logger.error(f"EWP view DB error: {e}")
            ewp_pagination = None
            ewp_records = []
    else:
        leave_form = None
        leave_pagination = None
        leave_requests = []
        ewp_form = None
        ewp_records = []
        ewp_pagination = None
        active_tab = None

    return render_template('dashboard.html',
                         title='Dashboard',
                         form=form,
                         decline_form=decline_form,
                         forward_form=forward_form,
                         batch_decline_form=batch_decline_form,
                         batch_forward_form=batch_forward_form,
                         created_documents=created_documents,
                         received_documents=received_documents,
                         created_pagination=created_pagination,
                         received_pagination=received_pagination,
                         search_query=search_query,
                         leave_requests=leave_requests,
                         leave_pagination=leave_pagination,
                         leave_form=leave_form,
                         ewp_form=ewp_form,
                         ewp_records=(ewp_records if view == 'leave' else []),
                         ewp_pagination=(ewp_pagination if view == 'leave' else None),
                         active_tab=(active_tab if view == 'leave' else None))

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
                file = form.attachment.data
                attachment_path = get_upload_path(file.filename)
                file_path = os.path.join(current_app.root_path, attachment_path)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                file.save(file_path)

            classification = request.form.get('full_classification')
            if not classification:
                classification = form.classification.data

            recipient_user = User.query.get(form.recipient.data)
            barcode_value = form.barcode.data.strip() if form.barcode.data else None
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
                recipient=recipient_user
            )

            db.session.add(document)
            db.session.commit()

            # notification for recipient
            notification = Notification(
                user=recipient_user,
                message=f"You have received a new document: {document.title}"
            )
            db.session.add(notification)

            activity_log = ActivityLog(
                user=current_user,
                document_id=document.id,
                action="Created",
                remarks=form.remarks.data if form.remarks.data else ""
            )
            db.session.add(activity_log)
            db.session.commit()

            flash('Document created successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating document: {str(e)}', 'danger')
            
        return redirect(url_for('main.dashboard'))

    for field, errors in form.errors.items():
        for error in errors:
            flash(f'Error in {field}: {error}', 'danger')
    
    return redirect(url_for('main.dashboard'))

# LeaveRequest create endpoint
@main.route('/leave_request/create', methods=['POST'])
@login_required
def create_leave_request():
    form = LeaveRequestForm()

    # Permission check for Leave module access
    if not current_user.can_access_leave:
        flash('You are not authorized to access the Leave section.', 'danger')
        return redirect(url_for('main.dashboard', view='created'))

    form.office.choices = OFFICE_CHOICES
    # Ensure choices are set during POST handling to pass WTForms validation
    try:
        form.leave_type.choices = LEAVE_TYPE_CHOICES
    except Exception:
        form.leave_type.choices = [(v, v) for v in [
            'COC', 'Vacation Leave', 'Mandatory/Forced Leave', 'Sick Leave', 'Maternity Leave',
            'Paternity Leave', 'Special Privilege Leave', 'Solo Parent Leave', 'Study Leave',
            '10-Day VAWC Leave', 'Rehabilitation Privilege', 'Special Leave Benefits for Women',
            'Special Emergency (Calamity)', 'Adoption Leave', 'Others'
        ]]
    if form.validate_on_submit():
        try:
            # Collect ranges from the new range inputs (Flatpickr), fallback to legacy fields
            range_strs = [r.strip() for r in request.form.getlist('date_range') if (r or '').strip()]

            def _parse_range(r: str):
                parts = r.split(' to ')
                start_str = (parts[0] or '').strip() if parts else ''
                end_str = (parts[1] or '').strip() if len(parts) > 1 else ''
                from datetime import datetime as _dt
                fmt = '%Y-%m-%d'
                start = _dt.strptime(start_str, fmt).date() if start_str else None
                end = _dt.strptime(end_str, fmt).date() if end_str else None
                # If only one date selected, treat as single-day leave
                if start and not end:
                    end = start
                # Normalize if user picked reversed order
                if start and end and end < start:
                    start, end = end, start
                return start, end

            # Fallback to the legacy hidden/DateField values if no ranges provided
            if not range_strs and (form.start_date.data or form.end_date.data):
                s = form.start_date.data
                e = form.end_date.data or form.start_date.data
                if s:
                    range_strs = [f"{s.strftime('%Y-%m-%d')} to {e.strftime('%Y-%m-%d')}"]

            # Parse and normalize ranges with aligned time modes per range
            time_modes = [ (tm or '').strip() for tm in request.form.getlist('time_mode_range') ]
            allowed_tm = {'FULL_DAY', 'AM_HALF', 'PM_HALF'}
            parsed_ranges = []
            for idx, r in enumerate(range_strs):
                start, end = _parse_range(r)
                if not start:
                    continue
                tm = time_modes[idx] if idx < len(time_modes) else 'FULL_DAY'
                if tm not in allowed_tm:
                    tm = 'FULL_DAY'
                parsed_ranges.append((start, (end or start), tm))

            if not parsed_ranges:
                flash('Please select at least one valid date range.', 'danger')
                return redirect(url_for('main.dashboard', view='leave'))

            # Compute overall bounds for parent record
            parent_start = min(s for s, _, __ in parsed_ranges)
            parent_end = max(e for _, e, __ in parsed_ranges)

            barcode_value = (form.barcode.data or '').strip() or None

            # Determine subtype and subtype_detail based on selected leave_type and submitted UI fields
            lt = (form.leave_type.data or '').strip()
            subtype = None
            subtype_detail = None
            try:
                if lt in ('Vacation Leave', 'Special Privilege Leave'):
                    subtype = (request.form.get('vacation_spl_subtype') or '').strip() or None
                    subtype_detail = (request.form.get('vacation_spl_detail') or '').strip() or None
                elif lt == 'Sick Leave':
                    subtype = (request.form.get('sick_leave_subtype') or '').strip() or None
                    subtype_detail = (request.form.get('sick_leave_detail') or '').strip() or None
                elif lt == 'Special Leave Benefits for Women':
                    # Keep subtype same as type for clarity; details captured from textbox
                    subtype = 'Special Leave Benefits for Women'
                    subtype_detail = (request.form.get('slbw_details') or '').strip() or None
                elif lt == 'Study Leave':
                    subtype = (request.form.get('study_leave_purpose') or '').strip() or None
                elif lt == 'Others':
                    subtype = (request.form.get('others_subtype') or '').strip() or None
            except Exception:
                # Fail-safe: do not block creation on UI extras
                subtype = subtype if subtype else None
                subtype_detail = subtype_detail if subtype_detail else None

            leave = LeaveRequest(
                barcode=barcode_value,
                employee_name=form.employee_name.data.strip(),
                office=form.office.data,
                leave_type=lt,
                subtype=subtype,
                subtype_detail=subtype_detail,
                status='For Computation',
                remarks=form.remarks.data,
                created_by_user_id=current_user.id,
                start_date=parent_start,
                end_date=parent_end
            )
            db.session.add(leave)
            db.session.flush()  # ensure leave.id

            # Create individual date ranges
            for s, e, tm in parsed_ranges:
                dr = LeaveDateRange(
                    leave_request_id=leave.id,
                    start_date=s,
                    end_date=e,
                    time_mode=tm
                )
                db.session.add(dr)

            db.session.commit()
            flash('Leave record successfully created.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating leave request: {str(e)}', 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'Error in {field}: {error}', 'danger')
    return redirect(url_for('main.dashboard', view='leave', tab='leave'))

# EWP create endpoint
@main.route('/ewp/create', methods=['POST'])
@login_required
def create_ewp():
    """
    Create an EWP record from the EWP tab in the Leave modal.
    Permissions: requires can_access_leave.
    """
    if not current_user.can_access_leave:
        flash('You are not authorized to access the Leave/EWP section.', 'danger')
        return redirect(url_for('main.dashboard', view='created'))

    form = EWPForm()
    form.office.choices = OFFICE_CHOICES

    if form.validate_on_submit():
        try:
            # Robust decimal parsing and quantization to 2 places
            raw_amount = (request.form.get('amount') or '').strip()
            normalized_amount = raw_amount.replace(',', '')
            amount_val = Decimal(normalized_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            record = EWPRecord(
                barcode=(form.barcode.data or '').strip() or None,
                employee_name=form.employee_name.data.strip(),
                office=form.office.data,
                amount=amount_val,
                purpose=(form.purpose.data or '').strip() or None,
                remarks=(form.remarks.data or '').strip() or None,
                status='For Computation',
                created_by_user_id=current_user.id,
                created_timestamp=datetime.utcnow()
            )
            db.session.add(record)
            db.session.commit()
            flash('EWP record created successfully.', 'success')
        except (InvalidOperation, ValueError):
            db.session.rollback()
            flash('Invalid amount value.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating EWP record: {str(e)}', 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'Error in {field}: {error}', 'danger')

    return redirect(url_for('main.dashboard', view='leave', tab='ewp'))

# EWP management endpoints
@main.route('/ewp/update_status/<int:ewp_id>', methods=['POST'])
@login_required
def update_ewp_status(ewp_id):
    page = request.args.get('page', 1, type=int)
    if not current_user.can_access_leave:
        flash('You are not authorized to access the Leave/EWP section.', 'danger')
        return redirect(url_for('main.dashboard', view='leave', tab='ewp', page=page))
    try:
        record = EWPRecord.query.get_or_404(ewp_id)
        new_status = (request.form.get('status') or '').strip()
        remarks = (request.form.get('remarks') or '').strip()
        valid_statuses = {'Pending', 'For Computation', 'Released'}
        if new_status not in valid_statuses:
            flash('Invalid status selection.', 'danger')
            return redirect(url_for('main.dashboard', view='leave', tab='ewp', page=page))
        record.status = new_status
        if new_status in ('Pending', 'Released') and remarks != '':
            record.remarks = remarks
        db.session.commit()
        flash('EWP status updated.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating EWP status: {str(e)}', 'danger')
    return redirect(url_for('main.dashboard', view='leave', tab='ewp', page=page))

@main.route('/ewp/edit/<int:ewp_id>', methods=['POST'])
@login_required
def edit_ewp(ewp_id):
    page = request.args.get('page', 1, type=int)
    if not (current_user.is_admin or current_user.can_access_leave):
        flash('You are not authorized to access the Leave/EWP section.', 'danger')
        return redirect(url_for('main.dashboard', view='leave', tab='ewp', page=page))
    try:
        record = EWPRecord.query.get_or_404(ewp_id)
        if not (current_user.is_admin or (record.created_by_user_id == current_user.id and current_user.can_access_leave)):
            flash('You are not authorized to edit this EWP record.', 'danger')
            return redirect(url_for('main.dashboard', view='leave', tab='ewp', page=page))
        if (not current_user.is_admin) and getattr(record, 'status', None) == 'Released':
            flash('Released EWP records can only be edited by an administrator.', 'warning')
            return redirect(url_for('main.dashboard', view='leave', tab='ewp', page=page))

        employee_name = (request.form.get('employee_name') or '').strip()
        barcode_value = (request.form.get('barcode') or '').strip() or None
        office = (request.form.get('office') or '').strip()
        amount_str = (request.form.get('amount') or '').strip()
        purpose = (request.form.get('purpose') or '').strip() or None
        remarks = (request.form.get('remarks') or '').strip() or None

        if not employee_name or not office:
            flash('Please provide Name and Office.', 'danger')
            return redirect(url_for('main.dashboard', view='leave', tab='ewp', page=page))

        # Parse amount if provided; preserve existing if blank
        if amount_str != '':
            try:
                normalized_amount = amount_str.replace(',', '')
                amount_val = Decimal(normalized_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            except (InvalidOperation, ValueError):
                flash('Invalid amount value.', 'danger')
                return redirect(url_for('main.dashboard', view='leave', tab='ewp', page=page))
            record.amount = amount_val

        record.employee_name = employee_name
        record.barcode = barcode_value
        record.office = office
        record.purpose = purpose
        record.remarks = remarks

        db.session.commit()
        flash('EWP record updated successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating EWP record: {str(e)}', 'danger')
    return redirect(url_for('main.dashboard', view='leave', tab='ewp', page=page))

@main.route('/ewp/delete/<int:ewp_id>', methods=['POST'])
@login_required
def delete_ewp(ewp_id):
    page = request.args.get('page', 1, type=int)
    if not (current_user.is_admin or current_user.can_access_leave):
        flash('You are not authorized to access the Leave/EWP section.', 'danger')
        return redirect(url_for('main.dashboard', view='leave', tab='ewp', page=page))
    try:
        record = EWPRecord.query.get_or_404(ewp_id)
        if not (current_user.is_admin or (record.created_by_user_id == current_user.id and current_user.can_access_leave)):
            flash('You are not authorized to delete this EWP record.', 'danger')
            return redirect(url_for('main.dashboard', view='leave', tab='ewp', page=page))
        if (not current_user.is_admin) and getattr(record, 'status', None) == 'Released':
            flash('Released EWP records can only be deleted by an administrator.', 'warning')
            return redirect(url_for('main.dashboard', view='leave', tab='ewp', page=page))

        db.session.delete(record)
        db.session.commit()
        flash('EWP record deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting EWP record: {str(e)}', 'danger')
    return redirect(url_for('main.dashboard', view='leave', tab='ewp', page=page))

@main.route('/leave_request/delete/<int:leave_id>', methods=['POST'])
@login_required
def delete_leave_request(leave_id):
    """
    Delete a leave request.
    Allowed for:
      - Admins, or
      - The creator of the leave request who also has can_access_leave.
    Non-admins cannot delete Released requests.
    """
    page = request.args.get('page', 1, type=int)
    try:
        leave = LeaveRequest.query.get_or_404(leave_id)

        # Authorization: Admin OR (creator with can_access_leave)
        if not (current_user.is_admin or (current_user.can_access_leave and leave.created_by_user_id == current_user.id)):
            flash('You are not authorized to delete this leave request.', 'danger')
            return redirect(url_for('main.dashboard', view='leave', page=page))

        # Additional safeguard: only admins can delete Released requests
        if (not current_user.is_admin) and getattr(leave, 'status', None) == 'Released':
            flash('Released leave requests can only be deleted by an administrator.', 'warning')
            return redirect(url_for('main.dashboard', view='leave', page=page))

        db.session.delete(leave)
        db.session.commit()
        flash('Leave request deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting leave request: {str(e)}', 'danger')
    return redirect(url_for('main.dashboard', view='leave', page=page))

@main.route('/leave_request/release/<int:leave_id>', methods=['POST'])
@login_required
def release_leave_request(leave_id):
    """
    Mark a leave request as Released and set its released timestamp.
    Allowed for any authenticated user as per requirements.
    """
    page = request.args.get('page', 1, type=int)

    # Permission check for Leave module access
    if not current_user.can_access_leave:
        flash('You are not authorized to access the Leave section.', 'danger')
        return redirect(url_for('main.dashboard', view='leave', page=page))
    try:
        leave = LeaveRequest.query.get_or_404(leave_id)
        if leave.status == 'Released':
            flash('Leave request is already released.', 'info')
            return redirect(url_for('main.dashboard', view='leave', page=page))

        leave.status = 'Released'
        leave.released_timestamp = datetime.utcnow()
        db.session.commit()
        flash('Leave request released successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error releasing leave request: {str(e)}', 'danger')
    return redirect(url_for('main.dashboard', view='leave', page=page))

@main.route('/leave_request/update_status/<int:leave_id>', methods=['POST'])
@login_required
def update_leave_request_status(leave_id):
    """
    Update a leave request's status via dropdown. Allowed for any authenticated user.
    Accepted statuses: Pending, For Computation, For Signature, Released.
    When setting to Released, released_timestamp is set to now if not already present.
    """
    page = request.args.get('page', 1, type=int)

    # Permission check for Leave module access
    if not current_user.can_access_leave:
        flash('You are not authorized to access the Leave section.', 'danger')
        return redirect(url_for('main.dashboard', view='leave', page=page))

    new_status = (request.form.get('status') or '').strip()
    remarks = (request.form.get('remarks') or '').strip()
    valid_statuses = {'Pending', 'For Computation', 'For Signature', 'Released'}
    if new_status not in valid_statuses:
        flash('Invalid status selection.', 'danger')
        return redirect(url_for('main.dashboard', view='leave', page=page))
    try:
        leave = LeaveRequest.query.get_or_404(leave_id)
        leave.status = new_status
        # Persist remarks for Pending, For Signature and Released only when a non-empty value is provided
        if new_status in ('Pending', 'For Signature', 'Released') and remarks != '':
            leave.remarks = remarks
        if new_status == 'Released' and not leave.released_timestamp:
            leave.released_timestamp = datetime.utcnow()
        db.session.commit()
        flash('Leave request status updated.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating status: {str(e)}', 'danger')
    return redirect(url_for('main.dashboard', view='leave', page=page))

@main.route('/leave_request/edit/<int:leave_id>', methods=['POST'])
@login_required
def edit_leave_request(leave_id):
    """
    Edit an existing leave request.
    Allowed for:
      - Admins, or
      - The creator of the leave request who also has can_access_leave.
    Non-admins cannot edit Released requests.
    """
    page = request.args.get('page', 1, type=int)

    # Permission check for Leave module access
    if not current_user.can_access_leave and not current_user.is_admin:
        flash('You are not authorized to access the Leave section.', 'danger')
        return redirect(url_for('main.dashboard', view='leave', page=page))

    try:
        leave = LeaveRequest.query.get_or_404(leave_id)

        # Authorization: Admin OR (creator with can_access_leave)
        if not (current_user.is_admin or (current_user.can_access_leave and leave.created_by_user_id == current_user.id)):
            flash('You are not authorized to edit this leave request.', 'danger')
            return redirect(url_for('main.dashboard', view='leave', page=page))

        # Additional safeguard: only admins can edit Released requests
        if (not current_user.is_admin) and getattr(leave, 'status', None) == 'Released':
            flash('Released leave requests can only be edited by an administrator.', 'warning')
            return redirect(url_for('main.dashboard', view='leave', page=page))

        # Parse core fields
        employee_name = (request.form.get('employee_name') or '').strip()
        office = (request.form.get('office') or '').strip()
        leave_type = (request.form.get('leave_type') or '').strip()
        remarks = (request.form.get('remarks') or '').strip()
        barcode_value = (request.form.get('barcode') or '').strip() or None

        # Basic validation
        if not employee_name or not office or not leave_type:
            flash('Please provide Employee Name, Office, and Type.', 'danger')
            return redirect(url_for('main.dashboard', view='leave', page=page))

        # Determine subtype and subtype_detail based on selected leave_type and submitted UI fields
        subtype = None
        subtype_detail = None
        try:
            if leave_type in ('Vacation Leave', 'Special Privilege Leave'):
                subtype = (request.form.get('vacation_spl_subtype') or '').strip() or None
                subtype_detail = (request.form.get('vacation_spl_detail') or '').strip() or None
            elif leave_type == 'Sick Leave':
                subtype = (request.form.get('sick_leave_subtype') or '').strip() or None
                subtype_detail = (request.form.get('sick_leave_detail') or '').strip() or None
            elif leave_type == 'Special Leave Benefits for Women':
                # Keep subtype same as type for clarity; details captured from textbox
                subtype = 'Special Leave Benefits for Women'
                subtype_detail = (request.form.get('slbw_details') or '').strip() or None
            elif leave_type == 'Study Leave':
                subtype = (request.form.get('study_leave_purpose') or '').strip() or None
            elif leave_type == 'Others':
                subtype = (request.form.get('others_subtype') or '').strip() or None
        except Exception:
            # Do not block edit on UI extras
            pass

        # Collect ranges from the range inputs (Flatpickr), if provided
        range_strs = [r.strip() for r in request.form.getlist('date_range') if (r or '').strip()]

        def _parse_range(r: str):
            parts = r.split(' to ')
            start_str = (parts[0] or '').strip() if parts else ''
            end_str = (parts[1] or '').strip() if len(parts) > 1 else ''
            from datetime import datetime as _dt
            fmt = '%Y-%m-%d'
            start = _dt.strptime(start_str, fmt).date() if start_str else None
            end = _dt.strptime(end_str, fmt).date() if end_str else None
            # If only one date selected, treat as single-day leave
            if start and not end:
                end = start
            # Normalize if user picked reversed order
            if start and end and end < start:
                start, end = end, start
            return start, end

        # Parse and normalize ranges with aligned time modes per range
        time_modes = [ (tm or '').strip() for tm in request.form.getlist('time_mode_range') ]
        allowed_tm = {'FULL_DAY', 'AM_HALF', 'PM_HALF'}
        parsed_ranges = []
        for idx, r in enumerate(range_strs):
            s, e = _parse_range(r)
            if not s:
                continue
            tm = time_modes[idx] if idx < len(time_modes) else 'FULL_DAY'
            if tm not in allowed_tm:
                tm = 'FULL_DAY'
            parsed_ranges.append((s, (e or s), tm))

        # Update parent fields
        leave.employee_name = employee_name
        leave.office = office
        leave.leave_type = leave_type
        leave.remarks = remarks
        leave.barcode = barcode_value
        # Only update subtype fields if provided; otherwise preserve existing values
        if subtype is not None:
            leave.subtype = subtype
        if subtype_detail is not None:
            leave.subtype_detail = subtype_detail

        # If ranges provided, replace existing ranges and recompute overall bounds
        if parsed_ranges:
            # Compute overall bounds for parent record
            parent_start = min(s for s, _, __ in parsed_ranges)
            parent_end = max(e for _, e, __ in parsed_ranges)
            leave.start_date = parent_start
            leave.end_date = parent_end

            # Remove existing date ranges and insert new ones
            LeaveDateRange.query.filter_by(leave_request_id=leave.id).delete(synchronize_session=False)
            for s, e, tm in parsed_ranges:
                dr = LeaveDateRange(
                    leave_request_id=leave.id,
                    start_date=s,
                    end_date=e,
                    time_mode=tm
                )
                db.session.add(dr)

        db.session.commit()
        flash('Leave request updated successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating leave request: {str(e)}', 'danger')

    return redirect(url_for('main.dashboard', view='leave', page=page))

@main.route('/edit_document/<int:document_id>', methods=['POST'])
@login_required
def edit_document(document_id):
    document = Document.query.get_or_404(document_id)

    if document.creator != current_user:
        flash('You are not authorized to edit this document.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    if document.status == 'Released':
        flash('Released documents cannot be edited.', 'warning')
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
                file = form.attachment.data
                filename = secure_filename(file.filename)
                attachment_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(attachment_path)
                document.attachment = attachment_path

            classification = request.form.get('full_classification')
            if not classification:
                classification = form.classification.data

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
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating document: {str(e)}', 'danger')
            return redirect(url_for('main.dashboard'))
    
    # If form validation fails, show specific errors
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
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting document: {str(e)}', 'danger')
    
    return redirect(url_for('main.dashboard'))

from app.forms import DeclineDocumentForm, DocumentForm

@main.route('/accept_document/<int:document_id>', methods=['POST'])
@login_required
def accept_document(document_id):
    page = request.args.get('page', 1, type=int)
    view = request.args.get('view', 'received')
    document = Document.query.get_or_404(document_id)

    if document.recipient != current_user:
        flash('You are not authorized to accept this document.', 'danger')
        return redirect(url_for('main.dashboard', view=view, page=page))

    if document.status not in ['Pending', 'Forwarded']:
        flash('This document cannot be accepted in its current state.', 'warning')
        return redirect(url_for('main.dashboard'))

    try:
        document.status = 'Accepted'
        document.accepted_timestamp = datetime.utcnow()

        # Create notification for document creator
        notification = Notification(
            user=document.creator,
            message=f"Your document '{document.title}' has been accepted by {current_user.username}"
        )
        db.session.add(notification)

        # Log the acceptance action
        activity_log = ActivityLog(
            user=current_user,
            document_id=document.id,
            action="Accepted",
            remarks="Document accepted"
        )
        db.session.add(activity_log)

        # Insert ProcessingLog record
        from app.models import ProcessingLog
        processing_log = ProcessingLog(
            user_id=current_user.id,
            document_id=document.id,
            accepted_timestamp=datetime.utcnow()
        )
        db.session.add(processing_log)

        db.session.commit()

        flash('Document accepted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error accepting document: {str(e)}', 'danger')

    return redirect(url_for('main.dashboard', view='received', page=page))

@main.route('/release_document/<int:document_id>', methods=['POST'])
@login_required
def release_document(document_id):
    page = request.args.get('page', 1, type=int)
    view = request.args.get('view', 'received')
    document = Document.query.get_or_404(document_id)

    if document.recipient != current_user:
        flash('You are not authorized to release this document.', 'danger')
        return redirect(url_for('main.dashboard', view=view, page=page))

    document.status = 'Released'
    document.released_timestamp = datetime.utcnow()  # Add timestamp

    # Create notification for document creator
    notification = Notification(
        user=document.creator,
        message=f"Your document '{document.title}' has been released."
    )

    # Log the action
    activity_log = ActivityLog(
        user=current_user,
        document_id=document.id,
        action="Released",
        remarks=None
    )

    # Save all changes in a single transaction
    db.session.add(notification)
    db.session.add(activity_log)
    db.session.commit()

    flash('Document released successfully.', 'success')
    return redirect(url_for('main.dashboard', view='received', page=page))

@main.route('/decline_document/<int:document_id>', methods=['POST'])
@login_required
def decline_document(document_id):
    page = request.args.get('page', 1, type=int)
    view = request.args.get('view', 'received')
    document = Document.query.get_or_404(document_id)

    # Ensure only the recipient can decline the document
    if document.recipient != current_user:
        flash('You are not authorized to decline this document.', 'danger')
        return redirect(url_for('main.dashboard', view=view, page=page))

    form = DeclineDocumentForm()

    if form.validate_on_submit():
        document.status = 'Declined'
        document.remarks = form.reason.data
        
        # Create notification for document creator
        notification = Notification(
            user=document.creator, 
            message=f"Your document '{document.title}' has been declined. Reason: {form.reason.data}" 
        )
        
        # Save both document update and notification
        db.session.add(notification)
        db.session.commit()

        activity_log = ActivityLog(
            user=current_user,
            document_id=document.id,
            action="Declined",
            remarks=form.reason.data
        )
        db.session.add(activity_log)
        db.session.commit()

        flash('Document declined successfully.', 'success')
        return redirect(url_for('main.dashboard', page=page))

    flash('There was an error declining the document. Please check the form and try again.', 'danger')
    return redirect(url_for('main.dashboard', page=page))

@main.route('/forward_document/<int:document_id>', methods=['POST'])
@login_required
def forward_document(document_id):
    page = request.args.get('page', 1, type=int)
    view = request.args.get('view', 'received')
    document = Document.query.get_or_404(document_id)

    # Allow forwarding only if current user is the recipient and document is accepted
    if document.recipient != current_user:
        flash('You are not authorized to forward this document.', 'danger')
        return redirect(url_for('main.dashboard', view=view, page=page))

    if document.status not in ['Accepted', 'Forwarded']:
        flash('Document must be accepted before forwarding.', 'warning')
        return redirect(url_for('main.dashboard'))

    form = ForwardDocumentForm()
    form.recipient.choices = get_recipient_choices()

    if form.validate_on_submit():
        try:
            new_recipient_id = form.recipient.data
            previous_recipient = document.recipient
            document.recipient_id = new_recipient_id
            document.status = 'Pending'
            document.action_taken = form.action_taken.data
            document.remarks = form.remarks.data
            # set the forwarded timestamp
            document.forwarded_timestamp = datetime.utcnow()

            # Notify the new recipient
            new_recipient_user = User.query.get(new_recipient_id)
            notification = Notification(
                user=new_recipient_user,
                message=f"Document '{document.title}' has been forwarded to you by {current_user.username}"
            )
            db.session.add(notification)

            # Log the forwarding action
            activity_log = ActivityLog(
                user=current_user,
                document_id=document.id,
                action="Forwarded",
                remarks=f"Forwarded to {new_recipient_user.username}"
            )
            db.session.add(activity_log)

            # Update forwarded timestamp in ProcessingLog
            from app.models import ProcessingLog
            processing_log = (ProcessingLog.query
                              .filter_by(document_id=document.id, forwarded_timestamp=None)
                              .order_by(ProcessingLog.accepted_timestamp.desc())
                              .first())
            if processing_log:
                processing_log.forwarded_timestamp = datetime.utcnow()
            else:
                # Create a new record if not found
                processing_log = ProcessingLog(
                    user_id=current_user.id,
                    document_id=document.id,
                    accepted_timestamp=datetime.utcnow(),
                    forwarded_timestamp=datetime.utcnow()
                )
                db.session.add(processing_log)

            db.session.commit()

            flash('Document forwarded successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error forwarding document: {str(e)}', 'danger')

        return redirect(url_for('main.dashboard', view='received', page=page))

    return redirect(url_for('main.dashboard', page=page))

@main.route('/resubmit_document/<int:document_id>', methods=['POST'])
@login_required
def resubmit_document(document_id):
    page = request.args.get('page', 1, type=int)
    view = request.args.get('view', 'created')
    document = Document.query.get_or_404(document_id)
    form = ResubmitDocumentForm()

    # creator can resubmit the document
    if document.creator != current_user:
        flash('You are not authorized to resubmit this document.', 'danger')
        return redirect(url_for('main.dashboard', view=view, page=page))

    # Ensure the document is in the "declined" state
    if document.status != 'Declined':
        flash('This document cannot be resubmitted because it is not declined.', 'warning')
        return redirect(url_for('main.dashboard'))

    if form.validate_on_submit():
        try:
            # Update document
            document.status = 'Pending'
            document.action_taken = form.action_taken.data
            document.remarks = form.remarks.data
            
            # Create activity log
            activity_log = ActivityLog(
                user=current_user,
                document_id=document.id,
                action="Resubmitted",
                remarks=form.remarks.data
            )
            
            db.session.add(activity_log)
            db.session.commit()

            flash('Document resubmitted successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error resubmitting document: {str(e)}', 'danger')
            
    return redirect(url_for('main.dashboard'))

@main.route('/archive_document/<int:document_id>', methods=['POST'])
@login_required
def archive_document(document_id):
    document = Document.query.get_or_404(document_id)

    # only the creator or recipient can archive the document
    if document.creator != current_user and document.recipient != current_user:
        flash('You are not authorized to archive this document.', 'danger')
        return redirect(url_for('main.dashboard'))

    try:
        # Archive the document
        document.status = 'Archived'
        db.session.commit()

        # Log the archiving action
        activity_log = ActivityLog(
            user=current_user,
            document_id=document.id,
            action="Archived",
            remarks="Document archived"
        )
        db.session.add(activity_log)
        db.session.commit()

        flash('Document archived successfully.', 'success')
        return redirect(url_for('main.archive'))  # Redirect to archive
    except Exception as e:
        db.session.rollback()
        flash(f'Error archiving document: {str(e)}', 'danger')
        return redirect(url_for('main.dashboard'))

from sqlalchemy import or_

@main.route('/archive')
@login_required
def archive():
    # Get filter parameters - prioritize month/year over date range
    month = request.args.get('month', '')
    year = request.args.get('year', '')
    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)

    start_dt = None
    end_dt = None

    # Prioritize month/year filtering
    if month and year:
        try:
            m = int(month)
            y = int(year)
            start_dt = datetime(y, m, 1)
            if m == 12:
                end_dt = datetime(y + 1, 1, 1)
            else:
                end_dt = datetime(y, m + 1, 1)
        except Exception:
            start_dt = None
            end_dt = None
    elif year:
        try:
            y = int(year)
            start_dt = datetime(y, 1, 1)
            end_dt = datetime(y + 1, 1, 1)
        except Exception:
            start_dt = None
            end_dt = None

    query = Document.query.filter(
        (Document.status == 'Archived') &
        ((Document.creator == current_user) | (Document.recipient == current_user))
    )

    # Apply search if provided
    if search:
        query = query.filter(
            or_(
                Document.title.ilike(f'%{search}%'),
                Document.office.ilike(f'%{search}%'),
                Document.classification.ilike(f'%{search}%'),
                Document.status.ilike(f'%{search}%'),
                or_(
                    Document.barcode.ilike(f'%{search}%'),
                    Document.barcode == search
                )
            )
        )

    # Apply date range filter if available
    if start_dt is not None and end_dt is not None:
        query = query.filter(
            Document.timestamp >= start_dt,
            Document.timestamp < end_dt
        )

    paginated_documents = query.order_by(Document.timestamp.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    years_query = db.session.query(
        db.func.year(Document.timestamp).label('year')
    ).filter(
        Document.status=='Archived',
        (Document.creator_id == current_user.id) | (Document.recipient_id == current_user.id)
    ).distinct().order_by(
        db.func.year(Document.timestamp).desc()
    )
    
    try:
        years = [int(year[0]) for year in years_query.all() if year[0]]
    except (TypeError, ValueError):
        years = []
        current_year = datetime.now().year
        years = list(range(current_year, current_year-5, -1))

    for document in paginated_documents.items:
        document.activities_json = [activity.to_dict() for activity in document.activities]

    return render_template('archive.html', 
                         title='Archive', 
                         archived_documents=paginated_documents.items,
                         pagination=paginated_documents,
                         years=years,
                         current_month=month,
                         current_year=year,
                         search=search)

@main.route('/unarchive_document/<int:document_id>', methods=['POST'])
@login_required
def unarchive_document(document_id):
    document = Document.query.get_or_404(document_id)

    if document.creator != current_user and document.recipient != current_user:
        flash('You are not authorized to unarchive this document.', 'danger')
        return redirect(url_for('main.archive'))

    try:
        # Restore the document to its previous status or set to 'Pending'
        document.status = 'Pending'
        db.session.commit()

        # Log the unarchiving action
        activity_log = ActivityLog(
            user=current_user,
            document_id=document.id,
            action="Unarchived",
            remarks="Document restored from archive"
        )
        db.session.add(activity_log)
        db.session.commit()

        flash('Document unarchived successfully.', 'success')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error unarchiving document: {str(e)}', 'danger')
        return redirect(url_for('main.archive'))

from datetime import datetime, timedelta
from sqlalchemy import func

@main.route('/admin')
@login_required
def admin_dashboard():
    from app.models import format_timedelta, Document  # Added Document import
    if not current_user.is_admin:
        flash('You are not authorized to access the admin dashboard.', 'danger')
        return redirect(url_for('main.dashboard'))

    # Get separate page for documents, activities and users
    doc_page = request.args.get('doc_page', 1, type=int)
    activity_page = request.args.get('activity_page', 1, type=int)
    user_page = request.args.get('user_page', 1, type=int)  
    search_query = request.args.get('search', '').strip()
    
    # Documents pagination
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
                    Document.barcode == search_query
                )
            )
        )
    paginated_documents = documents_query.order_by(Document.timestamp.desc()).paginate(
        page=doc_page, per_page=10, error_out=False
    )

    # Activities pagination
    activities_query = ActivityLog.query\
        .join(Document, ActivityLog.document_id == Document.id)\
        .join(User, ActivityLog.user_id == User.id)\
        .order_by(ActivityLog.timestamp.desc())
    
    paginated_activities = activities_query.paginate(
        page=activity_page, 
        per_page=10, 
        error_out=False
    )

    # Users pagination
    users_query = User.query.order_by(User.id)
    users_pagination = users_query.paginate(
        page=user_page, per_page=10, error_out=False
    )

    # Total documents by status
    total_documents = Document.query.count()
    total_pending = Document.query.filter_by(status='Pending').count()
    total_accepted = Document.query.filter_by(status='Accepted').count()
    total_declined = Document.query.filter_by(status='Declined').count()
    total_released = Document.query.filter_by(status='Released').count()
    total_archived = Document.query.filter_by(status='Archived').count()

    # Add classification counts
    total_communications = Document.query.filter_by(classification='Communications').count()
    total_payroll = Document.query.filter_by(classification='Payroll').count()
    total_request = Document.query.filter_by(classification='Request').count()

    # Classification distributions with sub-classifications
    communications_subtypes = {
        'Travel Order': Document.query.filter(Document.classification.like('Communications - Travel Order%')).count(),
        'Office Order': Document.query.filter(Document.classification.like('Communications - Office Order%')).count(),
        'Travel Authority': Document.query.filter(Document.classification.like('Communications - Travel Authority%')).count(),
    }
    
    payroll_subtypes = {
        'Salary': Document.query.filter(Document.classification.like('Payroll - Salary%')).count(),
        'Voucher': Document.query.filter(Document.classification.like('Payroll - Voucher%')).count(),
        'Trust fund': Document.query.filter(Document.classification.like('Payroll - Trust fund%')).count(),
        'Terminal Pay': Document.query.filter(Document.classification.like('Payroll - Terminal Pay%')).count(),
        'Overtime Pay': Document.query.filter(Document.classification.like('Payroll - Overtime Pay%')).count(),
        'Subsistence Allowance': Document.query.filter(Document.classification.like('Payroll - Subsistence Allowance%')).count(),
        'Travel Allowance': Document.query.filter(Document.classification.like('Payroll - Travel Allowance%')).count(),
        'RATA': Document.query.filter(Document.classification.like('Payroll - RATA%')).count(),
        'Mobile Allowance': Document.query.filter(Document.classification.like('Payroll - Mobile Allowance%')).count(),
    }
    
    request_subtypes = {
        'Certificate of Employment': Document.query.filter(Document.classification.like('Request - Certificate of Employment%')).count(),
        'Service Record': Document.query.filter(Document.classification.like('Request - Service Record%')).count(),
        'Clearance': Document.query.filter(Document.classification.like('Request - Clearance%')).count(),
    }

    # Totals used for Document Analytics grouped chart
    try:
        others_count = Document.query.filter(Document.classification.like('Others%')).count()
    except Exception:
        others_count = 0

    # Leave analytics totals
    try:
        leave_total_analytics = LeaveRequest.query.count()
    except Exception:
        leave_total_analytics = 0

    # Leave status distribution
    try:
        leave_total_pending = LeaveRequest.query.filter_by(status='Pending').count()
    except Exception:
        leave_total_pending = 0
    try:
        leave_total_forcomp = LeaveRequest.query.filter_by(status='For Computation').count()
    except Exception:
        leave_total_forcomp = 0
    try:
        leave_total_forsignature = LeaveRequest.query.filter_by(status='For Signature').count()
    except Exception:
        leave_total_forsignature = 0
    try:
        leave_total_released = LeaveRequest.query.filter_by(status='Released').count()
    except Exception:
        leave_total_released = 0

    # Leave type distribution (overall)
    try:
        leave_type_rows = db.session.query(
            LeaveRequest.leave_type,
            db.func.count(LeaveRequest.id)
        ).group_by(LeaveRequest.leave_type).all()
        leave_types_labels = [name for name, cnt in leave_type_rows if name]
        leave_types_counts = [int(cnt) for name, cnt in leave_type_rows if name]
    except Exception:
        leave_types_labels = []
        leave_types_counts = []

    # Calculate average time to release
    released_docs = Document.query.filter_by(status='Released').all()
    total_release_time = timedelta()
    valid_release_count = 0

    for doc in released_docs:
        if doc.released_timestamp and doc.timestamp:
            total_release_time += calculate_business_hours(doc.timestamp, doc.released_timestamp)
            valid_release_count += 1

    avg_release_time = (total_release_time / valid_release_count) if valid_release_count > 0 else timedelta()

    # Calculate user handling times (time between acceptance and forwarding)
    users = User.query.all()
    user_metrics_loop = []
    for user in users:
        handled_docs = Document.query.filter(Document.recipient_id == user.id).all()
        total_handling_time = timedelta()
        handled_count = 0
        for doc in handled_docs:
            if doc.accepted_timestamp and doc.forwarded_timestamp:
                total_handling_time += calculate_business_hours(doc.accepted_timestamp, doc.forwarded_timestamp)
                handled_count += 1
        avg_handling_time = (total_handling_time / handled_count) if handled_count > 0 else timedelta()
        user_metrics_loop.append({
            'username': user.username,
            'avg_handling_time': avg_handling_time,
            'documents_handled': handled_count
        })

    # Calculate release metrics
    release_metrics = []
    for doc in released_docs:
        if doc.released_timestamp and doc.timestamp:
            release_metrics.append({
                'document_title': doc.title,
                'processing_time': doc.released_timestamp - doc.timestamp
            })

    # Get longest pending documents
    pending_documents = Document.query.filter_by(status='Pending')\
           .order_by(Document.timestamp.asc())\
        .limit(5)\
        .all()

    # Get today's date in UTC
    today = datetime.utcnow().date()
    first_day_of_month = today.replace(day=1)

    # Daily activity metrics
    daily_activities = db.session.query( # type: ignore
        ActivityLog.action, # type: ignore
        func.count(ActivityLog.id).label('count')
    ).filter(
        func.date(ActivityLog.timestamp) == today
    ).group_by(
        ActivityLog.action
    ).all()

    # Monthly activity metrics
    monthly_activities = db.session.query( # type: ignore
        ActivityLog.action, # type: ignore
        func.count(ActivityLog.id).label('count')
    ).filter(
        func.date(ActivityLog.timestamp) >= first_day_of_month
    ).group_by(
        ActivityLog.action
    ).all()

    # Format the metrics data
    daily_metrics = {action: count for action, count in daily_activities}
    monthly_metrics = {action: count for action, count in monthly_activities}

    # Augment metrics with LeaveRequest creations
    try:
        leave_created_today = LeaveRequest.query.filter(
            db.func.date(LeaveRequest.created_timestamp) == today
        ).count()
    except Exception:
        leave_created_today = 0

    try:
        leave_created_month = LeaveRequest.query.filter(
            db.func.date(LeaveRequest.created_timestamp) >= first_day_of_month
        ).count()
    except Exception:
        leave_created_month = 0

    daily_metrics['Leave Created'] = daily_metrics.get('Leave Created', 0) + int(leave_created_today or 0)
    monthly_metrics['Leave Created'] = monthly_metrics.get('Leave Created', 0) + int(leave_created_month or 0)

    # Calculate average time to release with user info
    released_docs = Document.query.filter_by(status='Released')\
        .order_by(Document.released_timestamp.desc())\
        .all()
    
    release_metrics = []
    for doc in released_docs:
        if doc.released_timestamp and doc.timestamp:
            release_time = calculate_business_hours(doc.timestamp, doc.released_timestamp)
            release_metrics.append({
                'title': doc.title,
                'creator': doc.creator.username,
                'handler': doc.recipient.username,
                'release_time': release_time
            })

    # Get longest pending documents with user info
    pending_documents = Document.query.filter_by(status='Pending')\
        .order_by(Document.timestamp.asc())\
        .limit(5)\
        .all()

    # Format pending documents for template
    pending_docs_info = [{
        'title': doc.title,
        'creator': doc.creator.username,
        'assigned_to': doc.recipient.username,
        'created_date': doc.timestamp,
        'pending_time': calculate_business_hours(doc.timestamp, datetime.utcnow())
    } for doc in pending_documents]


    from app.models import ProcessingLog
    user_metrics = (
        db.session.query(
            User.username,
            db.func.count(ProcessingLog.id).label('documents_handled'),
            db.func.avg(
                db.func.time_to_sec(
                    db.func.timediff(ProcessingLog.forwarded_timestamp, ProcessingLog.accepted_timestamp)
                )
            ).label('avg_processing_time')  # Changed to use MySQL/MariaDB compatible functions
        )
        .join(ProcessingLog, ProcessingLog.user_id == User.id)
        .filter(ProcessingLog.forwarded_timestamp != None)
        .group_by(User.username)
        .all()
    )

    # Leave performance by creator (created -> released)
    try:
        leave_user_metrics = (
            db.session.query(
                User.username.label('username'),
                db.func.count(LeaveRequest.id).label('leaves_released'),
                db.func.avg(
                    db.func.time_to_sec(
                        db.func.timediff(LeaveRequest.released_timestamp, LeaveRequest.created_timestamp)
                    )
                ).label('avg_processing_time')
            )
            .join(LeaveRequest, LeaveRequest.created_by_user_id == User.id)
            .filter(LeaveRequest.released_timestamp != None)
            .group_by(User.username)
            .all()
        )
    except Exception:
        leave_user_metrics = []

    # Get today's classifications count
    today = datetime.utcnow().date()
    today_classifications = db.session.query(
        Document.classification,
        db.func.count(Document.id).label('count')
    ).filter(
        db.func.date(Document.timestamp) == today
    ).group_by(Document.classification).all()

    # Get this month's classifications count
    first_day_of_month = today.replace(day=1)
    monthly_classifications = db.session.query(
        Document.classification,
        db.func.count(Document.id).label('count')
    ).filter(
        db.func.date(Document.timestamp) >= first_day_of_month
    ).group_by(Document.classification).all()

    # Format the data for tables and charts
    today_class_metrics = {class_name: count for class_name, count in today_classifications}
    monthly_class_metrics = {class_name: count for class_name, count in monthly_classifications}

    # Include Leave in classification metrics (today and this month)
    try:
        leave_today_count = LeaveRequest.query.filter(
            db.func.date(LeaveRequest.created_timestamp) == today
        ).count()
    except Exception:
        leave_today_count = 0

    try:
        leave_month_count = LeaveRequest.query.filter(
            db.func.date(LeaveRequest.created_timestamp) >= first_day_of_month
        ).count()
    except Exception:
        leave_month_count = 0

    today_class_metrics['Leave'] = today_class_metrics.get('Leave', 0) + int(leave_today_count or 0)
    monthly_class_metrics['Leave'] = monthly_class_metrics.get('Leave', 0) + int(leave_month_count or 0)

    # Get today's classifications with sub-types
    # Prepare LeaveRequest breakdowns for today and this month
    try:
        leave_today_rows = db.session.query(
            LeaveRequest.leave_type,
            db.func.count(LeaveRequest.id)
        ).filter(
            db.func.date(LeaveRequest.created_timestamp) == today
        ).group_by(LeaveRequest.leave_type).all()
        leave_today_subtypes = {name: int(cnt) for name, cnt in leave_today_rows}
    except Exception:
        leave_today_subtypes = {}
    try:
        leave_today_total = LeaveRequest.query.filter(
            db.func.date(LeaveRequest.created_timestamp) == today
        ).count()
    except Exception:
        leave_today_total = 0
    try:
        leave_month_rows = db.session.query(
            LeaveRequest.leave_type,
            db.func.count(LeaveRequest.id)
        ).filter(
            db.func.date(LeaveRequest.created_timestamp) >= first_day_of_month
        ).group_by(LeaveRequest.leave_type).all()
        leave_month_subtypes = {name: int(cnt) for name, cnt in leave_month_rows}
    except Exception:
        leave_month_subtypes = {}
    try:
        leave_month_total = LeaveRequest.query.filter(
            db.func.date(LeaveRequest.created_timestamp) >= first_day_of_month
        ).count()
    except Exception:
        leave_month_total = 0

    today_classifications = {
        'Communications': {
            'total': Document.query.filter(
                Document.classification.like('Communications%'),
                func.date(Document.timestamp) == today
            ).count(),
            'sub_types': {
                'Travel Order': Document.query.filter(
                    Document.classification.like('Communications - Travel Order%'),
                    func.date(Document.timestamp) == today
                ).count(),
                'Office Order': Document.query.filter(
                    Document.classification.like('Communications - Office Order%'),
                    func.date(Document.timestamp) == today
                ).count(),
                'Travel Authority': Document.query.filter(
                    Document.classification.like('Communications - Travel Authority%'),
                    func.date(Document.timestamp) == today
                ).count()
            }
        },
        'Payroll': {
            'total': Document.query.filter(
                Document.classification.like('Payroll%'),
                func.date(Document.timestamp) == today
            ).count(),
            'sub_types': {
                'Salary': Document.query.filter(
                    Document.classification.like('Payroll - Salary%'),
                    func.date(Document.timestamp) == today
                ).count(),
                'Voucher': Document.query.filter(
                    Document.classification.like('Payroll - Voucher%'),
                    func.date(Document.timestamp) == today
                ).count(),
                'Trust fund': Document.query.filter(
                    Document.classification.like('Payroll - Trust fund%'),
                    func.date(Document.timestamp) == today
                ).count(),
                'Terminal Pay': Document.query.filter(
                    Document.classification.like('Payroll - Terminal Pay%'),
                    func.date(Document.timestamp) == today
                ).count(),
                'Overtime Pay': Document.query.filter(
                    Document.classification.like('Payroll - Overtime Pay%'),
                    func.date(Document.timestamp) == today
                ).count()
            }
        },
        'Request': {
            'total': Document.query.filter(
                Document.classification.like('Request%'),
                func.date(Document.timestamp) == today
            ).count(),
            'sub_types': {
                'Certificate of Employment': Document.query.filter(
                    Document.classification.like('Request - Certificate of Employment%'),
                    func.date(Document.timestamp) == today
                ).count(),
                'Service Record': Document.query.filter(
                    Document.classification.like('Request - Service Record%'),
                    func.date(Document.timestamp) == today
                ).count(),
                'Clearance': Document.query.filter(
                    Document.classification.like('Request - Clearance%'),
                    func.date(Document.timestamp) == today
                ).count()
            }
        },
        'Others': {
            'total': Document.query.filter(
                Document.classification.like('Others%'),
                func.date(Document.timestamp) == today
            ).count(),
            'sub_types': {}
        },
        'Leave': {
            'total': leave_today_total,
            'sub_types': leave_today_subtypes
        }
    }

    # Monthly classifications with same structure
    monthly_classifications = {
        'Communications': {
            'total': Document.query.filter(
                Document.classification.like('Communications%'),
                func.date(Document.timestamp) >= first_day_of_month
            ).count(),
            'sub_types': {
                'Travel Order': Document.query.filter(
                    Document.classification.like('Communications - Travel Order%'),
                    func.date(Document.timestamp) >= first_day_of_month
                ).count(),
                'Office Order': Document.query.filter(
                    Document.classification.like('Communications - Office Order%'),
                    func.date(Document.timestamp) >= first_day_of_month
                ).count(),
                'Travel Authority': Document.query.filter(
                    Document.classification.like('Communications - Travel Authority%'),
                    func.date(Document.timestamp) >= first_day_of_month
                ).count()
            }
        },
        'Payroll': {
            'total': Document.query.filter(
                Document.classification.like('Payroll%'),
                func.date(Document.timestamp) >= first_day_of_month
            ).count(),
            'sub_types': {
                'Salary': Document.query.filter(
                    Document.classification.like('Payroll - Salary%'),
                    func.date(Document.timestamp) >= first_day_of_month
                ).count(),
                'Voucher': Document.query.filter(
                    Document.classification.like('Payroll - Voucher%'),
                    func.date(Document.timestamp) >= first_day_of_month
                ).count(),
                'Trust fund': Document.query.filter(
                    Document.classification.like('Payroll - Trust fund%'),
                    func.date(Document.timestamp) >= first_day_of_month
                ).count(),
                'Terminal Pay': Document.query.filter(
                    Document.classification.like('Payroll - Terminal Pay%'),
                    func.date(Document.timestamp) >= first_day_of_month
                ).count(),
                'Overtime Pay': Document.query.filter(
                    Document.classification.like('Payroll - Overtime Pay%'),
                    func.date(Document.timestamp) >= first_day_of_month
                ).count()
            }
        },
        'Request': {
            'total': Document.query.filter(
                Document.classification.like('Request%'),
                func.date(Document.timestamp) >= first_day_of_month
            ).count(),
            'sub_types': {
                'Certificate of Employment': Document.query.filter(
                    Document.classification.like('Request - Certificate of Employment%'),
                    func.date(Document.timestamp) >= first_day_of_month
                ).count(),
                'Service Record': Document.query.filter(
                    Document.classification.like('Request - Service Record%'),
                    func.date(Document.timestamp) >= first_day_of_month
                ).count(),
                'Clearance': Document.query.filter(
                    Document.classification.like('Request - Clearance%'),
                    func.date(Document.timestamp) >= first_day_of_month
                ).count()
            }
        },
        'Others': {
            'total': Document.query.filter(
                Document.classification.like('Others%'),
                func.date(Document.timestamp) >= first_day_of_month
            ).count(),
            'sub_types': {}
        },
        'Leave': {
            'total': leave_month_total,
            'sub_types': leave_month_subtypes
        }
    }

    # Build daily created vs released series for current month
    try:
        current_month_first = first_day_of_month
        if current_month_first.month == 12:
            next_month_first = current_month_first.replace(year=current_month_first.year + 1, month=1, day=1)
        else:
            next_month_first = current_month_first.replace(month=current_month_first.month + 1, day=1)
        start_dt = datetime.combine(current_month_first, datetime.min.time())
        end_dt = datetime.combine(next_month_first, datetime.min.time())

        created_rows = db.session.query(
            func.date(Document.timestamp).label('day'),
            db.func.count(Document.id)
        ).filter(
            Document.timestamp >= start_dt,
            Document.timestamp < end_dt
        ).group_by(func.date(Document.timestamp)).all()

        released_rows = db.session.query(
            func.date(Document.released_timestamp).label('day'),
            db.func.count(Document.id)
        ).filter(
            Document.released_timestamp != None,
            Document.released_timestamp >= start_dt,
            Document.released_timestamp < end_dt
        ).group_by(func.date(Document.released_timestamp)).all()

        def _norm_day(d):
            try:
                return d.strftime('%Y-%m-%d')
            except Exception:
                return str(d)

        created_map = {_norm_day(d): int(c) for d, c in created_rows}
        released_map = {_norm_day(d): int(c) for d, c in released_rows}

        created_daily_labels = []
        created_daily_counts = []
        released_daily_counts = []
        cur = current_month_first
        while cur < next_month_first:
            key = cur.strftime('%Y-%m-%d')
            created_daily_labels.append(key)
            created_daily_counts.append(created_map.get(key, 0))
            released_daily_counts.append(released_map.get(key, 0))
            cur += timedelta(days=1)
    except Exception:
        created_daily_labels = []
        created_daily_counts = []
        released_daily_counts = []

    return render_template(
        'admin_dashboard.html',
        title='Admin Dashboard',
        total_documents=total_documents,
        total_pending=total_pending,
        total_accepted=total_accepted,
        total_declined=total_declined,
        total_released=total_released,
        total_archived=total_archived,
        average_release_time=avg_release_time,
        pending_documents=pending_documents,
        user_metrics=user_metrics,
        leave_user_metrics=leave_user_metrics,
        total_communications=total_communications,
        total_payroll=total_payroll,
        total_request=total_request,
        recent_activities=paginated_activities.items,
        pagination=paginated_activities,
        format_timedelta=format_timedelta,
        documents=paginated_documents.items,
        doc_pagination=paginated_documents,
        activities=paginated_activities.items,
        activity_pagination=paginated_activities,
        users=users_pagination.items,  # Add users items
        users_pagination=users_pagination,  # Add users pagination
        search_query=search_query,
        daily_metrics=daily_metrics,
        monthly_metrics=monthly_metrics,
        release_metrics=release_metrics,
        pending_docs_info=pending_docs_info,
        communications_subtypes=communications_subtypes,
        payroll_subtypes=payroll_subtypes,
        request_subtypes=request_subtypes,
        others_count=others_count,
        leave_total_analytics=leave_total_analytics,
        today_class_metrics=today_class_metrics,
        monthly_class_metrics=monthly_class_metrics,
        today_classifications=today_classifications,
        monthly_classifications=monthly_classifications,
        created_daily_labels=created_daily_labels,
        created_daily_counts=created_daily_counts,
        released_daily_counts=released_daily_counts,
        leave_total_pending=leave_total_pending,
        leave_total_forcomp=leave_total_forcomp,
        leave_total_forsignature=leave_total_forsignature,
        leave_total_released=leave_total_released,
        leave_types_labels=leave_types_labels,
        leave_types_counts=leave_types_counts
    )

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
        
        print(f"Status change successful")
        return jsonify({
            'success': True, 
            'newStatus': user.status, 
            'oldStatus': old_status,
            'message': f"User status changed from {old_status} to {user.status}"
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error toggling user status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
        
        # Don't allow deleting own account
        if user.id == current_user.id:
            print(f"Admin {current_user.username} attempted to delete their own account")
            return jsonify({'success': False, 'error': 'You cannot delete your own account for security reasons.'}), 400
        
        # Check if user has any documents
        document_count = Document.query.filter((Document.creator_id == user.id) | (Document.recipient_id == user.id)).count()
        if document_count > 0:
            print(f"Cannot delete user {user.username} - has {document_count} associated documents")
            return jsonify({
                'success': False, 
                'error': f'Cannot delete this user because they have {document_count} associated documents. Transfer or delete these documents first.'
            }), 400
        
        # Delete notifications
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
        
        # Delete processing logs
        from app.models import ProcessingLog
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
        
        # Delete activity logs where user is the actor
        from app.models import ActivityLog
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
        
        # Now delete the user
        username = user.username
        db.session.delete(user)
        db.session.commit()
        print(f"User {username} successfully deleted")
        
        return jsonify({
            'success': True, 
            'message': f'User {username} has been successfully deleted'
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
        # Step 1: Get the user and perform basic validation
        user = User.query.get_or_404(user_id)
        print(f"Found user to approve: {user.username}, current status: {user.status}")
        
        # Step 2: Change status to Active
        user.status = 'Active'
        db.session.commit()
        print(f"Successfully updated user status to Active")
        
        # Step 3: Notification creation removed to avoid persistent notifications
        
        return jsonify({
            'success': True, 
            'message': f"User {user.username} has been approved successfully."
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
        # Step 1: Get the user and perform basic validation
        user = User.query.get_or_404(user_id)
        print(f"Found user to decline: {user.username}, current status: {user.status}")
        
        # Step 2: Change status to Disabled
        user.status = 'Disabled'
        db.session.commit()
        print(f"Successfully updated user status to Disabled")
        
        # Step 3: Create notification in a separate try block
        try:
            notification = Notification(
                user_id=user.id,  # Use user_id instead of user object
                message="Your account registration has been declined and disabled. Please contact the administrator for more information."
            )
            db.session.add(notification)
            db.session.commit()
            print(f"Successfully created notification for user")
        except Exception as notification_error:
            print(f"Warning: Could not create notification: {str(notification_error)}")
            # Continue even if notification creation fails
        
        return jsonify({
            'success': True,
            'message': f"User {user.username} has been declined and disabled."
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
        from app.models import ProcessingLog, User, format_timedelta, Document
        user = User.query.get_or_404(user_id)

        today = datetime.utcnow().date()
        first_day_of_month = today.replace(day=1)

        # Count of documents processed this month (forwarded completed)
        documents_processed_this_month = db.session.query(
            db.func.count(ProcessingLog.id)
        ).filter(
            ProcessingLog.user_id == user_id,
            ProcessingLog.forwarded_timestamp != None,
            db.func.date(ProcessingLog.forwarded_timestamp) >= first_day_of_month
        ).scalar() or 0

        # Overall average processing time in seconds for this user
        avg_processing_time_seconds = db.session.query(
            db.func.avg(
                db.func.time_to_sec(
                    db.func.timediff(ProcessingLog.forwarded_timestamp, ProcessingLog.accepted_timestamp)
                )
            )
        ).filter(
            ProcessingLog.user_id == user_id,
            ProcessingLog.forwarded_timestamp != None
        ).scalar()

        # Monthly average processing time in seconds for this user
        monthly_avg_processing_time_seconds = db.session.query(
            db.func.avg(
                db.func.time_to_sec(
                    db.func.timediff(ProcessingLog.forwarded_timestamp, ProcessingLog.accepted_timestamp)
                )
            )
        ).filter(
            ProcessingLog.user_id == user_id,
            ProcessingLog.forwarded_timestamp != None,
            db.func.date(ProcessingLog.forwarded_timestamp) >= first_day_of_month
        ).scalar()

        # New: Count of documents created overall by the user
        documents_created_overall = Document.query.filter_by(creator_id=user_id).count()

        # New: Count of documents created by the user this month
        documents_created_this_month = Document.query.filter(
            Document.creator_id == user_id,
            db.func.date(Document.timestamp) >= first_day_of_month
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
            'monthly_average_processing_time_formatted': format_timedelta(monthly_avg_sec)
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@main.route('/profile/activity_data', methods=['GET'])
@login_required
def profile_activity_data():
    try:
        # Include Document and LeaveRequest for per-day metrics
        from app.models import Document, LeaveRequest

        # Default to current UTC month if not provided
        now = datetime.utcnow()
        month = request.args.get('month', type=int) or now.month
        year = request.args.get('year', type=int) or now.year

        # Compute month start and exclusive end (first day of next month)
        try:
            month_start = datetime(year, month, 1)
            if month == 12:
                month_end = datetime(year + 1, 1, 1)
            else:
                month_end = datetime(year, month + 1, 1)
        except Exception:
            # Fallback to current month if inputs invalid
            month_start = datetime(now.year, now.month, 1)
            if now.month == 12:
                month_end = datetime(now.year + 1, 1, 1)
            else:
                month_end = datetime(now.year, now.month + 1, 1)

        # Documents Created by current user (per day)
        doc_created_rows = db.session.query(
            func.date(Document.timestamp).label('day'),
            db.func.count(Document.id)
        ).filter(
            Document.creator_id == current_user.id,
            Document.timestamp >= month_start,
            Document.timestamp < month_end
        ).group_by(func.date(Document.timestamp)).all()

        # Documents Released handled by current user (per day)
        doc_released_rows = db.session.query(
            func.date(Document.released_timestamp).label('day'),
            db.func.count(Document.id)
        ).filter(
            Document.recipient_id == current_user.id,
            Document.released_timestamp != None,
            Document.released_timestamp >= month_start,
            Document.released_timestamp < month_end
        ).group_by(func.date(Document.released_timestamp)).all()

        # Leave Created by current user
        leave_created_rows = db.session.query(
            func.date(LeaveRequest.created_timestamp).label('day'),
            db.func.count(LeaveRequest.id)
        ).filter(
            LeaveRequest.created_by_user_id == current_user.id,
            LeaveRequest.created_timestamp >= month_start,
            LeaveRequest.created_timestamp < month_end
        ).group_by(func.date(LeaveRequest.created_timestamp)).all()

        # Leave Released for leaves created by current user
        leave_released_rows = db.session.query(
            func.date(LeaveRequest.released_timestamp).label('day'),
            db.func.count(LeaveRequest.id)
        ).filter(
            LeaveRequest.created_by_user_id == current_user.id,
            LeaveRequest.released_timestamp != None,
            LeaveRequest.released_timestamp >= month_start,
            LeaveRequest.released_timestamp < month_end
        ).group_by(func.date(LeaveRequest.released_timestamp)).all()

        def _norm_day(d):
            try:
                return d.strftime('%Y-%m-%d')
            except Exception:
                return str(d)

        doc_created_map = {_norm_day(d): int(c) for d, c in doc_created_rows}
        doc_released_map = {_norm_day(d): int(c) for d, c in doc_released_rows}
        leave_created_map = {_norm_day(d): int(c) for d, c in leave_created_rows}
        leave_released_map = {_norm_day(d): int(c) for d, c in leave_released_rows}

        # Build full-month arrays
        labels = []
        doc_created = []
        doc_released = []
        leave_created = []
        leave_released = []
        cur = month_start
        while cur < month_end:
            key = cur.strftime('%Y-%m-%d')
            labels.append(key)
            doc_created.append(doc_created_map.get(key, 0))
            doc_released.append(doc_released_map.get(key, 0))
            leave_created.append(leave_created_map.get(key, 0))
            leave_released.append(leave_released_map.get(key, 0))
            cur += timedelta(days=1)

        return jsonify({
            'success': True,
            'labels': labels,
            'doc_created': doc_created,
            'doc_released': doc_released,
            'leave_created': leave_created,
            'leave_released': leave_released,
            'month': month,
            'year': year
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@main.route('/logout')
def logout():
    try:
        if current_user.is_authenticated:
            logout_user()
            flash('You have been logged out.', 'success')
        return redirect(url_for('main.home'))
    except Exception as e:
        current_app.logger.error(f"Error during logout: {str(e)}")
        flash('An error occurred during logout.', 'danger')
        return redirect(url_for('main.home')), 302

from app.models import Notification

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
        unread_notifications = Notification.query.filter_by(
            user=current_user,
            is_read=False
        ).all()

        for notification in unread_notifications:
            notification.is_read = True 
        db.session.commit()
        flash('All notifications marked as read.', 'success')
    except Exception as e:
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
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@main.route('/check_username', methods=['POST'])
def check_username():
    try:
        username = request.form.get('username', '').strip()
        
        # Log the request for debugging
        print(f"Checking username availability: {username}")
        
        if not username:
            return jsonify({'valid': False, 'message': 'Username is required'})
        
        if len(username) < 3:
            return jsonify({'valid': False, 'message': 'Username must be at least 3 characters long'})
        
        user = User.query.filter_by(username=username).first()
        
        if user:
            return jsonify({'valid': False, 'message': 'This username is already taken'})
        
        return jsonify({'valid': True, 'message': 'Username is available'})
    
    except Exception as e:
        print(f"Error checking username: {str(e)}")
        return jsonify({'valid': False, 'message': f'Server error: {str(e)}'}), 500

@main.route('/check_email', methods=['POST'])
def check_email():
    try:
        email = request.form.get('email', '').strip()
        
        # Log the request for debugging
        print(f"Checking email availability: {email}")
        
        if not email:
            return jsonify({'valid': False, 'message': 'Email is required'})
        
        # Basic email validation
        if '@' not in email or '.' not in email:
            return jsonify({'valid': False, 'message': 'Invalid email format'})
        
        # Check if email exists in database
        existing_user = User.query.filter_by(email=email).first()
        
        if existing_user:
            return jsonify({'valid': False, 'message': 'Email is already registered'})
        
        return jsonify({'valid': True, 'message': 'Email is available'})
    
    except Exception as e:
        print(f"Error checking email: {str(e)}")
        return jsonify({'valid': False, 'message': f'Server error: {str(e)}'}), 500

@main.route('/check_account_status', methods=['POST'])
def check_account_status():
    """Check a user's account status without logging in"""
    username = request.form.get('username', '').strip()
    if not username:
        return jsonify({'exists': False})
    
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'exists': False})
    
    return jsonify({
        'exists': True,
        'status': user.status
    })

@main.route('/notifications', methods=['GET'])
@login_required
def get_notifications():
    page = request.args.get('page', 1, type=int)
    per_page = 10  # adjust as needed
    pagination = Notification.query.filter_by(
        user=current_user,
        is_read=False
    ).order_by(Notification.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    notifications = pagination.items
    data = {
        'notifications': [{
            'id': n.id,
            'message': n.message,
            'timestamp': n.timestamp.isoformat(),
            'is_read': n.is_read
        } for n in notifications],
        'has_next': pagination.has_next,
        'next_page': pagination.next_num if pagination.has_next else None
    }
    return jsonify(data)

@main.route('/overview')
@login_required
def overview():
    from datetime import datetime
    from app.models import to_local_time
    current_time = to_local_time(datetime.utcnow())
    return render_template('overview.html', 
                         title='Overview',
                         user_name=current_user.username if current_user.is_authenticated else 'Guest',
                         current_time=current_time)

@main.route('/get_document_activities/<int:document_id>')
@login_required
def get_document_activities(document_id):
    """Endpoint to fetch document activities for the admin dashboard modal"""
    try:
        if not current_user.is_admin:
            return jsonify({'error': 'Unauthorized access'}), 403
            
        document = Document.query.get_or_404(document_id)
        
        # Get activities with error handling for to_dict()
        activities = ActivityLog.query.filter_by(document_id=document_id).order_by(ActivityLog.timestamp.desc()).all()
        activity_dicts = []
        
        for activity in activities:
            try:
                activity_dict = {
                    'id': activity.id,
                    'timestamp': to_local_time(activity.timestamp).strftime('%B %d, %Y at %I:%M %p') if activity.timestamp else 'Unknown',
                    'action': activity.action,
                    'remarks': activity.remarks,
                    'user': {'username': activity.user.username} if activity.user else None
                }
                activity_dicts.append(activity_dict)
            except Exception as e:
                print(f"Error serializing activity {activity.id}: {str(e)}")
                # Add a placeholder for failed activities
                activity_dicts.append({
                    'id': activity.id,
                    'timestamp': 'Error parsing timestamp',
                    'action': activity.action or 'Unknown action',
                    'remarks': 'Error retrieving details',
                    'user': {'username': 'Unknown'}
                })
        
        return jsonify({
            'document_id': document_id,
            'activities': activity_dicts
        })
    except Exception as e:
        print(f"Error in get_document_activities: {str(e)}")
        return jsonify({
            'error': 'An error occurred while fetching activities',
            'message': str(e)
        }), 500

@main.route('/check_barcode', methods=['POST'])
@login_required
def check_barcode():
    """Check if a barcode is available and suggest alternatives if taken"""
    barcode = request.form.get('barcode', '').strip()
    
    if not barcode:
        return jsonify({
            'valid': False, 
            'message': 'Barcode is required',
            'suggestions': []
        })
    
    # Check if barcode exists
    existing_document = Document.query.filter_by(barcode=barcode).first()
    
    if not existing_document:
        return jsonify({
            'valid': True,
            'message': 'Barcode is available',
            'suggestions': []
        })
    
    # Generate suggestions
    suggestions = []
    
    # Try adding "-A", "-B", etc. and other variations
    suffixes = ["-A", "-B", "-C", "A", "B", "C", "_1", "_2", "_3"]
    for suffix in suffixes:
        suggestion = barcode + suffix
        if not Document.query.filter_by(barcode=suggestion).first():
            suggestions.append(suggestion)
            # Limit to 5 suggestions
            if len(suggestions) >= 5:
                break
    
    return jsonify({
        'valid': False,
        'message': 'This barcode is already in use',
        'suggestions': suggestions
    })

import os
import mimetypes
from pathlib import Path
from flask import current_app, send_from_directory, abort


@main.route('/uploads/<filename>')
@login_required
def serve_file(filename):
    try:
        # Secure the filename and create safe paths
        safe_filename = secure_filename(filename)
        uploads_dir = os.path.join(current_app.root_path, 'uploads')
        
        # Create uploads directory if it doesn't exist
        Path(uploads_dir).mkdir(parents=True, exist_ok=True)
        
        # Build and validate file path
        file_path = os.path.join(uploads_dir, safe_filename)
        absolute_path = os.path.abspath(file_path)
        
        # Security check - prevent directory traversal
        if not absolute_path.startswith(os.path.abspath(uploads_dir)):
            current_app.logger.error(f"Directory traversal attempt: {filename}")
            abort(403)
        
        if not os.path.isfile(absolute_path):
            current_app.logger.error(f"File not found: {absolute_path}")
            abort(404)
            
        # Set correct MIME type
        mime_type = 'application/pdf' if filename.lower().endswith('.pdf') else 'application/octet-stream'
        
        return send_from_directory(
            directory=uploads_dir,
            path=safe_filename,
            mimetype=mime_type,
            as_attachment=False,
            download_name=safe_filename
        )
        
    except Exception as e:
        current_app.logger.error(f"Error serving file {filename}: {str(e)}")
        abort(500)

import os
from flask import send_from_directory, current_app, url_for
from werkzeug.utils import secure_filename

def get_file_download_url(filename):
    """Generate proper URL for file download"""
    if not filename:
        return None
    # Remove any path components and get just the filename
    safe_filename = os.path.basename(secure_filename(filename))
    return url_for('main.serve_file', filename=safe_filename)

from flask import send_file

@main.route('/admin/print_text_report')
@login_required
def print_text_report():
    """
    Admin-only, print-ready detailed text report.
    Query params:
      - month, year: integers; defaults to current month/year
      - include_details: 1|0 (default 1). When 1, include up to 200 documents list for the month.
      - autoprint: 1|0 (default 1). When 1, HTML page triggers window.print() on load.
      - format: html|txt (default html). 'txt' returns text/plain content.
    """
    # Security
    if not current_user.is_admin:
        flash('You are not authorized to access the admin report.', 'danger')
        return redirect(url_for('main.dashboard'))

    # Parse inputs
    now = datetime.utcnow()
    include_details = request.args.get('include_details', default=1, type=int)
    autoprint = request.args.get('autoprint', default=1, type=int)
    fmt = (request.args.get('format', default='html') or 'html').lower()

    # Date range support (preferred); fallback to month/year
    date_from_str = (request.args.get('date_from') or '').strip()
    date_to_str = (request.args.get('date_to') or '').strip()

    # Normalize partial inputs: if only one is provided, use it for both
    if date_from_str and not date_to_str:
        date_to_str = date_from_str
    if date_to_str and not date_from_str:
        date_from_str = date_to_str

    start_dt = None
    end_dt = None

    def _parse_date(s: str):
        try:
            return datetime.strptime(s, '%Y-%m-%d')
        except Exception:
            return None

    if date_from_str and date_to_str:
        df = _parse_date(date_from_str)
        dt = _parse_date(date_to_str)
        if df and dt:
            # Bounds are [start, end)
            start_dt = datetime(df.year, df.month, df.day)
            # end is next day midnight of date_to to make [start,end)
            end_dt = datetime(dt.year, dt.month, dt.day) + timedelta(days=1)
        else:
            # Invalid date strings; clear and fallback to month/year
            date_from_str = ''
            date_to_str = ''

    if start_dt is None or end_dt is None:
        # Fallback to month/year if date range not provided/invalid
        month = request.args.get('month', type=int) or now.month
        year = request.args.get('year', type=int) or now.year
        try:
            start_dt = datetime(year, month, 1)
        except Exception:
            start_dt = datetime(now.year, now.month, 1)
            year = start_dt.year
            month = start_dt.month
        if month == 12:
            end_dt = datetime(year + 1, 1, 1)
        else:
            end_dt = datetime(year, month + 1, 1)
        # Populate defaults for date inputs from computed month bounds
        date_from_str = start_dt.date().isoformat()
        date_to_str = (end_dt - timedelta(days=1)).date().isoformat()

    # Data computations
    # 1) Documents created in selected month
    documents_month_q = Document.query.filter(
        Document.timestamp >= start_dt,
        Document.timestamp < end_dt
    )
    documents_created_this_month = documents_month_q.count()

    # 2) Per-classification counts for selected month
    def count_class(prefix: str) -> int:
        return Document.query.filter(
            Document.classification.like(f'{prefix}%'),
            Document.timestamp >= start_dt,
            Document.timestamp < end_dt
        ).count()

    # Include Leave requests created within the selected period
    try:
        leave_created_in_period = LeaveRequest.query.filter(
            LeaveRequest.created_timestamp >= start_dt,
            LeaveRequest.created_timestamp < end_dt
        ).count()
    except Exception:
        leave_created_in_period = 0

    per_classification_counts = {
        'Communications': count_class('Communications'),
        'Payroll': count_class('Payroll'),
        'Request': count_class('Request'),
        'Others': count_class('Others'),
        'Leave': int(leave_created_in_period or 0)
    }

    # New: Processing time by classification (released within period, business hours)
    classification_buckets = {
        'Communications': {'count': 0, 'total_sec': 0},
        'Payroll': {'count': 0, 'total_sec': 0},
        'Request': {'count': 0, 'total_sec': 0},
        'Others': {'count': 0, 'total_sec': 0},
        'Leave': {'count': 0, 'total_sec': 0}
    }
    # Track per sub-classification aggregates under each main classification
    classification_sub_buckets = {
        'Communications': {},
        'Payroll': {},
        'Request': {},
        'Others': {},
        'Leave': {}
    }
    docs_rel = (
        Document.query
        .with_entities(Document.classification, Document.timestamp, Document.released_timestamp)
        .filter(
            Document.released_timestamp != None,
            Document.released_timestamp >= start_dt,
            Document.released_timestamp < end_dt
        ).all()
    )
    for cls, created_at, released_at in docs_rel:
        if not created_at or not released_at:
            continue
        main = 'Others'
        try:
            if isinstance(cls, str):
                if cls.startswith('Communications'):
                    main = 'Communications'
                elif cls.startswith('Payroll'):
                    main = 'Payroll'
                elif cls.startswith('Request'):
                    main = 'Request'
        except Exception:
            main = 'Others'
        try:
            delta_td = calculate_business_hours(created_at, released_at)
        except Exception:
            delta_td = (released_at - created_at)
        try:
            sec = int(delta_td.total_seconds()) if delta_td else 0
        except Exception:
            sec = 0
        if sec < 0:
            sec = 0
        classification_buckets[main]['count'] += 1
        classification_buckets[main]['total_sec'] += sec
        # Determine sub-classification label
        sub_name = cls
        try:
            if isinstance(cls, str):
                prefix = main + ' - '
                if cls.startswith(prefix):
                    sub_name = cls[len(prefix):].strip() or 'General'
                elif cls == main:
                    sub_name = 'General'
                else:
                    sub_name = cls
        except Exception:
            sub_name = 'General'
        subs = classification_sub_buckets.get(main, {})
        entry = subs.get(sub_name)
        if not entry:
            entry = {'count': 0, 'total_sec': 0}
            subs[sub_name] = entry
            classification_sub_buckets[main] = subs
        entry['count'] += 1
        entry['total_sec'] += sec

    # Include LeaveRequest processing (released within period)
    try:
        leaves_rel = (
            LeaveRequest.query
            .with_entities(LeaveRequest.leave_type, LeaveRequest.created_timestamp, LeaveRequest.released_timestamp)
            .filter(
                LeaveRequest.released_timestamp != None,
                LeaveRequest.released_timestamp >= start_dt,
                LeaveRequest.released_timestamp < end_dt
            ).all()
        )
    except Exception:
        leaves_rel = []

    for leave_type, created_ts, released_ts in leaves_rel:
        if not created_ts or not released_ts:
            continue
        main = 'Leave'
        try:
            delta_td = calculate_business_hours(created_ts, released_ts)
        except Exception:
            delta_td = (released_ts - created_ts)
        try:
            sec = int(delta_td.total_seconds()) if delta_td else 0
        except Exception:
            sec = 0
        if sec < 0:
            sec = 0
        # Update main bucket
        bucket = classification_buckets.get(main)
        if not bucket:
            classification_buckets[main] = {'count': 0, 'total_sec': 0}
            bucket = classification_buckets[main]
        bucket['count'] += 1
        bucket['total_sec'] += sec

        # Subtype by leave_type
        sub_name = leave_type or 'General'
        subs = classification_sub_buckets.get(main) or {}
        entry = subs.get(sub_name)
        if not entry:
            entry = {'count': 0, 'total_sec': 0}
            subs[sub_name] = entry
            classification_sub_buckets[main] = subs
        entry['count'] += 1
        entry['total_sec'] += sec

    classification_processing = []
    for key in ['Communications', 'Payroll', 'Request', 'Others', 'Leave']:
        c = classification_buckets[key]['count']
        tot = classification_buckets[key]['total_sec']
        avg_sec = int(tot / c) if c > 0 else 0
        if c > 0:
            try:
                avg_formatted = format_timedelta(timedelta(seconds=avg_sec))
            except Exception:
                avg_formatted = str(timedelta(seconds=avg_sec))
        else:
            avg_formatted = "No document processed yet"
        classification_processing.append({
            'classification': key,
            'count': c,
            'avg_sec': avg_sec,
            'avg_formatted': avg_formatted
        })

    # Build output structure for template/TXT
    classification_sub_processing = []
    for key in ['Communications', 'Payroll', 'Request', 'Others', 'Leave']:
        submap = classification_sub_buckets.get(key, {})
        rows = []
        if submap:
            for sub_name in sorted(submap.keys()):
                sc = submap[sub_name]['count']
                tot_sec = submap[sub_name]['total_sec']
                avg_sec = int(tot_sec / sc) if sc > 0 else 0
                avg_formatted = format_timedelta(timedelta(seconds=avg_sec)) if sc > 0 else "No document processed yet"
                rows.append({
                    'sub': sub_name,
                    'count': sc,
                    'avg_sec': avg_sec,
                    'avg_formatted': avg_formatted
                })
        else:
            # No documents released for this main classification
            rows.append({
                'sub': '—',
                'count': 0,
                'avg_sec': 0,
                'avg_formatted': "No document processed yet"
            })
        classification_sub_processing.append({
            'classification': key,
            'rows': rows
        })

    # 3) Rankings (monthly and overall)
    from app.models import ProcessingLog

    # Helper to get ranking (best and worst) given a base query
    def get_rankings(base_filters):
        avg_expr = db.func.avg(
            db.func.time_to_sec(
                db.func.timediff(ProcessingLog.forwarded_timestamp, ProcessingLog.accepted_timestamp)
            )
        ).label('avg_sec')

        q = (
            db.session.query(
                User.username.label('username'),
                avg_expr,
                db.func.count(ProcessingLog.id).label('count')
            )
            .join(User, User.id == ProcessingLog.user_id)
            .filter(ProcessingLog.forwarded_timestamp != None)
        )

        if base_filters:
            q = q.filter(*base_filters)

        q = q.group_by(User.username).having(db.func.count(ProcessingLog.id) > 0)

        best = q.order_by(db.asc(db.text('avg_sec'))).first()
        worst = q.order_by(db.desc(db.text('avg_sec'))).first()

        def norm(row):
            if not row or row.avg_sec is None:
                return None
            try:
                sec = int(row.avg_sec) if row.avg_sec is not None else 0
            except Exception:
                sec = 0
            return {
                'username': row.username,
                'avg_sec': sec,
                'avg_formatted': format_timedelta(timedelta(seconds=sec)),
                'count': int(row.count) if getattr(row, 'count', None) is not None else 0
            }

        return norm(best), norm(worst)

    # Monthly rankings (based on forwarded in selected month)
    monthly_best, monthly_worst = get_rankings([
        ProcessingLog.forwarded_timestamp >= start_dt,
        ProcessingLog.forwarded_timestamp < end_dt
    ])

    # Overall rankings (no date filter)
    overall_best, overall_worst = get_rankings([])

    # User Performance (This Month)
    user_performance = []
    leave_user_metrics_period = []
    try:
        # Collect handled per user from ProcessingLog within month and compute avg in Python
        plogs = (
            ProcessingLog.query
            .filter(
                ProcessingLog.forwarded_timestamp != None,
                ProcessingLog.accepted_timestamp != None,
                ProcessingLog.forwarded_timestamp >= start_dt,
                ProcessingLog.forwarded_timestamp < end_dt
            ).all()
        )
        handled_map = {}
        for pl in plogs:
            uid = pl.user_id
            if not uid:
                continue
            delta = 0
            try:
                if pl.forwarded_timestamp and pl.accepted_timestamp:
                    delta = int((pl.forwarded_timestamp - pl.accepted_timestamp).total_seconds())
            except Exception:
                delta = 0
            if delta < 0:
                delta = 0
            entry = handled_map.setdefault(uid, {'handled': 0, 'total_sec': 0})
            entry['handled'] += 1
            entry['total_sec'] += delta

        # Collect created per user from Document within month
        creators = Document.query.with_entities(Document.creator_id).filter(
            Document.timestamp >= start_dt,
            Document.timestamp < end_dt
        ).all()
        created_map = {}
        for (cid,) in creators:
            if cid:
                created_map[cid] = created_map.get(cid, 0) + 1

        # Merge and build list
        all_uids = set(created_map.keys()) | set(handled_map.keys())
        if all_uids:
            users_rows = db.session.query(User.id, User.username).filter(User.id.in_(all_uids)).all()
            usernames = {uid: uname for uid, uname in users_rows}
            for uid in all_uids:
                created = int(created_map.get(uid, 0))
                handled_data = handled_map.get(uid, {'handled': 0, 'total_sec': 0})
                handled = int(handled_data['handled'])
                if created > 0 or handled > 0:
                    avg_sec = int(handled_data['total_sec'] / handled) if handled > 0 else 0
                    user_performance.append({
                        'username': usernames.get(uid, f'User {uid}'),
                        'documents_created': created,
                        'documents_handled': handled,
                        'avg_sec': avg_sec,
                        'avg_formatted': format_timedelta(timedelta(seconds=avg_sec))
                    })
            user_performance.sort(key=lambda x: x['username'].lower() if isinstance(x['username'], str) else str(x['username']).lower())

        # Leave user performance for selected period (created -> released)
        try:
            leave_rows = (
                LeaveRequest.query
                .with_entities(
                    LeaveRequest.created_by_user_id,
                    LeaveRequest.created_timestamp,
                    LeaveRequest.released_timestamp
                )
                .filter(
                    LeaveRequest.created_by_user_id != None,
                    LeaveRequest.released_timestamp != None,
                    LeaveRequest.released_timestamp >= start_dt,
                    LeaveRequest.released_timestamp < end_dt
                ).all()
            )
        except Exception:
            leave_rows = []

        agg = {}
        for uid, cts, rts in leave_rows:
            if not uid or not cts or not rts:
                continue
            try:
                delta_td = calculate_business_hours(cts, rts)
            except Exception:
                delta_td = (rts - cts)
            try:
                sec = int(delta_td.total_seconds()) if delta_td else 0
            except Exception:
                sec = 0
            if sec < 0:
                sec = 0
            e = agg.setdefault(uid, {'count': 0, 'total_sec': 0})
            e['count'] += 1
            e['total_sec'] += sec

        if agg:
            users_rows2 = db.session.query(User.id, User.username).filter(User.id.in_(list(agg.keys()))).all()
            uname_map = {uid: uname for uid, uname in users_rows2}
            for uid, data in agg.items():
                cnt = int(data['count'])
                avg_sec = int(data['total_sec'] / cnt) if cnt > 0 else 0
                leave_user_metrics_period.append({
                    'username': uname_map.get(uid, f'User {uid}'),
                    'leaves_released': cnt,
                    'avg_sec': avg_sec,
                    'avg_formatted': format_timedelta(timedelta(seconds=avg_sec))
                })
            leave_user_metrics_period.sort(key=lambda x: x['username'].lower() if isinstance(x['username'], str) else str(x['username']).lower())
        else:
            leave_user_metrics_period = []
    except Exception as _e:
        user_performance = []
        leave_user_metrics_period = []

    # 4) Document list (optional, capped)
    documents_list = []
    truncated = False
    cap = 200
    if include_details:
        docs_q = (
            documents_month_q
            .options(joinedload(Document.creator), joinedload(Document.recipient))
            .order_by(Document.timestamp.desc())
        )
        total = docs_q.count()
        if total > cap:
            truncated = True
        docs = docs_q.limit(cap).all()
        for d in docs:
            documents_list.append({
                'title': d.title,
                'office': d.office,
                'classification': d.classification,
                'creator': d.creator.username if d.creator else 'Unknown',
                'created_at': to_local_time(d.timestamp) if d.timestamp else None,
                'status': d.status,
                'barcode': d.barcode or ''
            })

    # Plain text format
    if fmt == 'txt':
        # Build a plain text representation
        lines = []
        # Build a human-friendly period label (MMMM DD, YYYY)
        try:
            start_fmt_txt = to_local_time(start_dt).strftime('%B %d, %Y') if start_dt else ''
        except Exception:
            start_fmt_txt = start_dt.strftime('%B %d, %Y') if start_dt else ''
        try:
            end_inclusive_txt = (end_dt - timedelta(days=1)) if end_dt else None
            end_fmt_txt = to_local_time(end_inclusive_txt).strftime('%B %d, %Y') if end_inclusive_txt else ''
        except Exception:
            end_fmt_txt = end_inclusive_txt.strftime('%B %d, %Y') if end_inclusive_txt else ''
        if date_from_str and date_to_str:
            if date_from_str == date_to_str:
                period_label = start_fmt_txt
            else:
                period_label = f'{start_fmt_txt} to {end_fmt_txt}'
        else:
            period_label = to_local_time(start_dt).strftime('%B %Y') if start_dt else 'Selected Period'

        generated_ts = to_local_time(datetime.utcnow()).strftime('%Y-%m-%d %H:%M:%S')
        lines.append(f'System Activity Report — {period_label}')
        lines.append(f'Generated: {generated_ts}')
        lines.append('')
        lines.append('Summary')
        lines.append('-------')
        lines.append(f'Documents created in period: {documents_created_this_month}')
        lines.append('Per-Classification counts (selected period):')
        for k, v in per_classification_counts.items():
            lines.append(f'  - {k}: {v}')
        lines.append('')
        lines.append(f'Processing Time by Classification and Sub-types ({period_label})')
        lines.append('------------------------------------------------------')
        for grp in classification_sub_processing:
            lines.append(f'  {grp["classification"]}:')
            for row in grp["rows"]:
                lines.append(f'    - {row["sub"]}: count {row["count"]}, avg {row["avg_formatted"]}')
        lines.append('')
        lines.append('Rankings (Selected Period)')
        lines.append('--------------------------')
        if monthly_best:
            lines.append(f'  Top performer: {monthly_best["username"]} — {monthly_best["avg_formatted"]} (avg, {monthly_best["count"]} handled)')
        else:
            lines.append('  Top performer: N/A')
        if monthly_worst:
            lines.append(f'  Longest processing: {monthly_worst["username"]} — {monthly_worst["avg_formatted"]} (avg, {monthly_worst["count"]} handled)')
        else:
            lines.append('  Longest processing: N/A')
        lines.append('')
        lines.append('Rankings (Overall)')
        lines.append('------------------')
        if overall_best:
            lines.append(f'  Top performer: {overall_best["username"]} — {overall_best["avg_formatted"]} (avg, {overall_best["count"]} handled)')
        else:
            lines.append('  Top performer: N/A')
        if overall_worst:
            lines.append(f'  Longest processing: {overall_worst["username"]} — {overall_worst["avg_formatted"]} (avg, {overall_worst["count"]} handled)')
        else:
            lines.append('  Longest processing: N/A')
        lines.append('')
        lines.append('User Performance (Selected Period)')
        lines.append('----------------------------------')
        if user_performance:
            for u in user_performance:
                lines.append(f'  - {u["username"]}: created {u["documents_created"]}, handled {u["documents_handled"]}, avg {u["avg_formatted"]}')
        else:
            lines.append('  No user activity found.')
        lines.append('')
        lines.append('Leave User Performance (Selected Period)')
        lines.append('---------------------------------------')
        if leave_user_metrics_period:
            for row in leave_user_metrics_period:
                lines.append(f'  - {row["username"]}: released {row["leaves_released"]}, avg {row["avg_formatted"]}')
        else:
            lines.append('  No leave processing data found.')
        lines.append('')
        if include_details:
            lines.append('Documents Created This Month')
            lines.append('----------------------------')
            if not documents_list:
                lines.append('  No documents found.')
            else:
                for d in documents_list:
                    created_str = d['created_at'].strftime('%Y-%m-%d %H:%M') if d['created_at'] else 'N/A'
                    lines.append(f'  • {d["title"]} | {d["office"]} | {d["classification"]} | by {d["creator"]} | {created_str} | {d["status"]} | {d["barcode"]}')
                if truncated:
                    lines.append('')
                    lines.append(f'  Note: List truncated to {cap} items. Use include_details=1 and filter by month/year or export via database for full list.')
        text = '\n'.join(lines)
        resp = make_response(text, 200)
        resp.mimetype = 'text/plain; charset=utf-8'
        return resp

    # HTML format (render template)
    # Build human-friendly formatted dates and period label
    from_fmt = ''
    to_fmt = ''
    if start_dt:
        try:
            from_fmt = to_local_time(start_dt).strftime('%B %d, %Y')
        except Exception:
            from_fmt = start_dt.strftime('%B %d, %Y')
    if end_dt:
        try:
            end_inclusive = end_dt - timedelta(days=1)
            to_fmt = to_local_time(end_inclusive).strftime('%B %d, %Y')
        except Exception:
            to_fmt = (end_dt - timedelta(days=1)).strftime('%B %d, %Y')
    else:
        to_fmt = from_fmt

    if date_from_str and date_to_str:
        if date_from_str == date_to_str:
            period_label = from_fmt
        else:
            period_label = f'{from_fmt} to {to_fmt}'
    else:
        period_label = to_local_time(start_dt).strftime('%B %Y') if start_dt else 'Selected Period'

    return render_template(
        'report_text.html',
        title='System Activity Report',
        selected_from=date_from_str,
        selected_to=date_to_str,
        selected_from_fmt=from_fmt,
        selected_to_fmt=to_fmt,
        period_label=period_label,
        autoprint=bool(autoprint),
        include_details=bool(include_details),
        documents_created_this_month=documents_created_this_month,
        per_classification_counts=per_classification_counts,
        monthly_best=monthly_best,
        monthly_worst=monthly_worst,
        overall_best=overall_best,
        overall_worst=overall_worst,
        documents_list=documents_list,
        truncated=truncated,
        cap=cap,
        generated_at=to_local_time(datetime.utcnow()),
        user_performance=user_performance,
        leave_user_metrics_period=leave_user_metrics_period,
        classification_processing=classification_processing,
        classification_sub_processing=classification_sub_processing
    )

# Batch Document Action Routes
@main.route('/batch_accept_documents', methods=['POST'])
@login_required
def batch_accept_documents():
    """Accept multiple documents at once"""
    page = request.args.get('page', 1, type=int)
    view = request.args.get('view', 'received')
    
    document_ids = request.form.getlist('document_ids')
    if not document_ids:
        flash('No documents selected for batch accept.', 'warning')
        return redirect(url_for('main.dashboard', view=view, page=page))
    
    try:
        document_ids = [int(doc_id) for doc_id in document_ids]
    except ValueError:
        flash('Invalid document selection.', 'danger')
        return redirect(url_for('main.dashboard', view=view, page=page))
    
    success_count = 0
    error_count = 0
    
    for doc_id in document_ids:
        try:
            document = Document.query.get(doc_id)
            if not document:
                error_count += 1
                continue
                
            # Check authorization and status
            if document.recipient != current_user:
                error_count += 1
                continue
                
            if document.status not in ['Pending', 'Forwarded']:
                error_count += 1
                continue
            
            # Accept the document
            document.status = 'Accepted'
            document.accepted_timestamp = datetime.utcnow()
            
            # Create notification for document creator
            notification = Notification(
                user=document.creator,
                message=f"Your document '{document.title}' has been accepted by {current_user.username}"
            )
            db.session.add(notification)
            
            # Log the acceptance action
            activity_log = ActivityLog(
                user=current_user,
                document_id=document.id,
                action="Batch Accepted",
                remarks="Document accepted via batch operation"
            )
            db.session.add(activity_log)
            
            # Insert ProcessingLog record
            from app.models import ProcessingLog
            processing_log = ProcessingLog(
                user_id=current_user.id,
                document_id=document.id,
                accepted_timestamp=datetime.utcnow()
            )
            db.session.add(processing_log)
            
            success_count += 1
            
        except Exception as e:
            error_count += 1
            current_app.logger.error(f"Error in batch accept for document {doc_id}: {str(e)}")
    
    try:
        db.session.commit()
        if success_count > 0:
            flash(f'Successfully accepted {success_count} document(s).', 'success')
        if error_count > 0:
            flash(f'Failed to accept {error_count} document(s).', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing batch accept: {str(e)}', 'danger')
    
    return redirect(url_for('main.dashboard', view='received', page=page))

@main.route('/batch_decline_documents', methods=['POST'])
@login_required
def batch_decline_documents():
    """Decline multiple documents at once"""
    page = request.args.get('page', 1, type=int)
    view = request.args.get('view', 'received')
    
    form = BatchDeclineDocumentForm()
    
    if not form.validate_on_submit():
        flash('Please provide a reason for declining the documents.', 'danger')
        return redirect(url_for('main.dashboard', view=view, page=page))
    
    document_ids = request.form.getlist('document_ids')
    if not document_ids:
        flash('No documents selected for batch decline.', 'warning')
        return redirect(url_for('main.dashboard', view=view, page=page))
    
    try:
        document_ids = [int(doc_id) for doc_id in document_ids]
    except ValueError:
        flash('Invalid document selection.', 'danger')
        return redirect(url_for('main.dashboard', view=view, page=page))
    
    success_count = 0
    error_count = 0
    reason = form.reason.data
    
    for doc_id in document_ids:
        try:
            document = Document.query.get(doc_id)
            if not document:
                error_count += 1
                continue
                
            # Check authorization
            if document.recipient != current_user:
                error_count += 1
                continue
            
            # Decline the document
            document.status = 'Declined'
            document.remarks = reason
            
            # Create notification for document creator
            notification = Notification(
                user=document.creator,
                message=f"Your document '{document.title}' has been declined. Reason: {reason}"
            )
            db.session.add(notification)
            
            # Log the decline action
            activity_log = ActivityLog(
                user=current_user,
                document_id=document.id,
                action="Batch Declined",
                remarks=reason
            )
            db.session.add(activity_log)
            
            success_count += 1
            
        except Exception as e:
            error_count += 1
            current_app.logger.error(f"Error in batch decline for document {doc_id}: {str(e)}")
    
    try:
        db.session.commit()
        if success_count > 0:
            flash(f'Successfully declined {success_count} document(s).', 'success')
        if error_count > 0:
            flash(f'Failed to decline {error_count} document(s).', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing batch decline: {str(e)}', 'danger')
    
    return redirect(url_for('main.dashboard', view='received', page=page))

@main.route('/batch_forward_documents', methods=['POST'])
@login_required
def batch_forward_documents():
    """Forward multiple documents at once"""
    page = request.args.get('page', 1, type=int)
    view = request.args.get('view', 'received')
    
    form = BatchForwardDocumentForm()
    form.recipient.choices = get_recipient_choices()
    
    if not form.validate_on_submit():
        flash('Please provide valid recipient and action for forwarding the documents.', 'danger')
        return redirect(url_for('main.dashboard', view=view, page=page))
    
    document_ids = request.form.getlist('document_ids')
    if not document_ids:
        flash('No documents selected for batch forward.', 'warning')
        return redirect(url_for('main.dashboard', view=view, page=page))
    
    try:
        document_ids = [int(doc_id) for doc_id in document_ids]
    except ValueError:
        flash('Invalid document selection.', 'danger')
        return redirect(url_for('main.dashboard', view=view, page=page))
    
    success_count = 0
    error_count = 0
    new_recipient_id = form.recipient.data
    action_taken = form.action_taken.data
    remarks = form.remarks.data
    
    # Get new recipient user
    new_recipient_user = User.query.get(new_recipient_id)
    if not new_recipient_user:
        flash('Invalid recipient selected.', 'danger')
        return redirect(url_for('main.dashboard', view=view, page=page))
    
    for doc_id in document_ids:
        try:
            document = Document.query.get(doc_id)
            if not document:
                error_count += 1
                continue
                
            # Check authorization and status
            if document.recipient != current_user:
                error_count += 1
                continue
                
            if document.status not in ['Accepted', 'Forwarded']:
                error_count += 1
                continue
            
            # Forward the document
            document.recipient_id = new_recipient_id
            document.status = 'Pending'
            document.action_taken = action_taken
            document.remarks = remarks
            document.forwarded_timestamp = datetime.utcnow()
            
            # Create notification for new recipient
            notification = Notification(
                user=new_recipient_user,
                message=f"Document '{document.title}' has been forwarded to you by {current_user.username}"
            )
            db.session.add(notification)
            
            # Log the forwarding action
            activity_log = ActivityLog(
                user=current_user,
                document_id=document.id,
                action="Batch Forwarded",
                remarks=f"Forwarded to {new_recipient_user.username}"
            )
            db.session.add(activity_log)
            
            # Update ProcessingLog
            from app.models import ProcessingLog
            processing_log = (ProcessingLog.query
                              .filter_by(document_id=document.id, forwarded_timestamp=None)
                              .order_by(ProcessingLog.accepted_timestamp.desc())
                              .first())
            if processing_log:
                processing_log.forwarded_timestamp = datetime.utcnow()
            else:
                processing_log = ProcessingLog(
                    user_id=current_user.id,
                    document_id=document.id,
                    accepted_timestamp=datetime.utcnow(),
                    forwarded_timestamp=datetime.utcnow()
                )
                db.session.add(processing_log)
            
            success_count += 1
            
        except Exception as e:
            error_count += 1
            current_app.logger.error(f"Error in batch forward for document {doc_id}: {str(e)}")
    
    try:
        db.session.commit()
        if success_count > 0:
            flash(f'Successfully forwarded {success_count} document(s) to {new_recipient_user.username}.', 'success')
        if error_count > 0:
            flash(f'Failed to forward {error_count} document(s).', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing batch forward: {str(e)}', 'danger')
    
    return redirect(url_for('main.dashboard', view='received', page=page))

@main.route('/batch_release_documents', methods=['POST'])
@login_required
def batch_release_documents():
    """Release multiple documents at once"""
    page = request.args.get('page', 1, type=int)
    view = request.args.get('view', 'received')
    
    document_ids = request.form.getlist('document_ids')
    if not document_ids:
        flash('No documents selected for batch release.', 'warning')
        return redirect(url_for('main.dashboard', view=view, page=page))
    
    try:
        document_ids = [int(doc_id) for doc_id in document_ids]
    except ValueError:
        flash('Invalid document selection.', 'danger')
        return redirect(url_for('main.dashboard', view=view, page=page))
    
    success_count = 0
    error_count = 0
    
    for doc_id in document_ids:
        try:
            document = Document.query.get(doc_id)
            if not document:
                error_count += 1
                continue
                
            # Check authorization
            if document.recipient != current_user:
                error_count += 1
                continue
            
            # Release the document
            document.status = 'Released'
            document.released_timestamp = datetime.utcnow()
            
            # Create notification for document creator
            notification = Notification(
                user=document.creator,
                message=f"Your document '{document.title}' has been released."
            )
            db.session.add(notification)
            
            # Log the release action
            activity_log = ActivityLog(
                user=current_user,
                document_id=document.id,
                action="Batch Released",
                remarks="Document released via batch operation"
            )
            db.session.add(activity_log)
            
            success_count += 1
            
        except Exception as e:
            error_count += 1
            current_app.logger.error(f"Error in batch release for document {doc_id}: {str(e)}")
    
    try:
        db.session.commit()
        if success_count > 0:
            flash(f'Successfully released {success_count} document(s).', 'success')
        if error_count > 0:
            flash(f'Failed to release {error_count} document(s).', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing batch release: {str(e)}', 'danger')
    
    return redirect(url_for('main.dashboard', view='received', page=page))

# Serve favicon.ico
@main.route('/favicon.ico')
def favicon():
    try:
        favicon_path = os.path.join(current_app.root_path, 'static', 'favicon.ico')
        if not os.path.exists(favicon_path):
            # Return a default favicon from static folder
            default_favicon = os.path.join(current_app.root_path, 'static', 'default_favicon.ico')
            return send_file(default_favicon, mimetype='image/x-icon')
        return send_file(favicon_path, mimetype='image/x-icon')
    except Exception as e:
        current_app.logger.error(f"Error serving favicon: {str(e)}")
        abort(404)  # Return 404 instead of 500 for missing favicon
