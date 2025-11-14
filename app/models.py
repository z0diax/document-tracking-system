import pytz
import json
from datetime import datetime
from flask_login import UserMixin
from app import db, login_manager
# Remove the to_local_time import as it's causing circular import
from werkzeug.security import generate_password_hash, check_password_hash

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

EDUCATION_FIELD_NAMES = (
    'school_name',
    'basic_education',
    'period_from',
    'period_to',
    'highest_level',
    'year_graduated',
    'scholarships'
)

CIVIL_SERVICE_FIELD_NAMES = (
    'career_service',
    'rating',
    'exam_date',
    'exam_place',
    'license_number',
    'license_validity'
)

WORK_EXPERIENCE_FIELD_NAMES = (
    'inclusive_from',
    'inclusive_to',
    'position_title',
    'department_agency',
    'monthly_salary',
    'salary_grade',
    'appointment_status',
    'is_gov_service'
)

VOLUNTARY_WORK_FIELD_NAMES = (
    'organization_name',
    'organization_address',
    'inclusive_from',
    'inclusive_to',
    'hours',
    'position_nature'
)

LEARNING_DEV_FIELD_NAMES = (
    'program_title',
    'inclusive_from',
    'inclusive_to',
    'hours',
    'ld_type',
    'conducted_by'
)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    # Changed column size for password_hash
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    # Per-user permission to access Leave module
    can_access_leave = db.Column(db.Boolean, default=False, nullable=False, server_default='0')
    # Per-user permission to access Employee Records module
    can_access_employee_records = db.Column(db.Boolean, default=False, nullable=False, server_default='0')
    status = db.Column(db.String(20), default='Pending', server_default='Pending', nullable=False)  # Add server_default
    documents_created = db.relationship('Document', backref='creator', lazy=True, foreign_keys='Document.creator_id')
    documents_received = db.relationship('Document', backref='recipient', lazy=True, foreign_keys='Document.recipient_id')
    
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if 'status' not in kwargs:
            self.status = 'Pending'
    
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')
    
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_pending_documents_count(self):
        """Get count of pending documents assigned to the user"""
        return Document.query.filter_by(
            recipient_id=self.id,
            status='Pending'
        ).count()

    def has_documents(self):
        """Check if user has any documents (created or received)"""
        created_count = Document.query.filter_by(creator_id=self.id).count()
        received_count = Document.query.filter_by(recipient_id=self.id).count()
        return created_count > 0 or received_count > 0

    @property
    def name(self):
        """Return username as name for compatibility"""
        return self.username
        
    @property
    def is_active(self):
        """Override UserMixin's is_active property
        
        This is used by Flask-Login to determine if a user can log in.
        We only allow users with 'Active' status.
        """
        print(f"DEBUG - Checking if user {self.username} is_active - status: '{self.status}'")
        
        # Explicit status check - anything except exactly 'Active' returns False
        if self.status != 'Active':
            print(f"User {self.username} NOT active - status is '{self.status}'")
            return False
        
        print(f"User {self.username} IS active - has 'Active' status")
        return True

# Move these timezone functions here instead of importing
def to_local_time(dt):
    """Convert datetime to Manila time"""
    if not dt:
        return None
    manila_tz = pytz.timezone('Asia/Manila')
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    return dt.astimezone(manila_tz)

def format_timestamp(timestamp):
    """Standard timestamp formatting for the application"""
    if not timestamp:
        return None
    manila_tz = pytz.timezone('Asia/Manila')
    if timestamp.tzinfo is None:
        timestamp = pytz.UTC.localize(timestamp)
    local_time = timestamp.astimezone(manila_tz)
    return local_time.strftime('%B-%d-%Y at %I:%M %p')

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    office = db.Column(db.String(100), nullable=False)
    classification = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='For Computation', server_default='For Computation')

    action_taken = db.Column(db.String(50), nullable=False)
    attachment = db.Column(db.String(200), nullable=True)
    remarks = db.Column(db.Text, nullable=True)
    barcode = db.Column(db.String(50), nullable=True)  # New barcode field
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # Creation timestamp
    no_dtas_flag = db.Column(db.Boolean, nullable=False, default=False, server_default='0')

    # Additional timestamps for status changes
    accepted_timestamp = db.Column(db.DateTime, nullable=True)  # When the document was accepted
    released_timestamp = db.Column(db.DateTime, nullable=True)  # When the document was released
    forwarded_timestamp = db.Column(db.DateTime, nullable=True)  # NEW: When the document was forwarded

    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Add this relationship
    activities = db.relationship('ActivityLog', 
                               backref='document',
                               lazy=True,
                               cascade='all, delete-orphan')

    # Update processing_logs relationship to use back_populates
    processing_logs = db.relationship('ProcessingLog', cascade='all, delete-orphan', back_populates='document')

    __table_args__ = (
        db.Index('ix_doc_recipient_status', 'recipient_id', 'status'),
        db.Index('ix_doc_creator_status', 'creator_id', 'status'),
        db.Index('ix_doc_timestamp', 'timestamp'),
        db.Index('ix_doc_barcode', 'barcode'),
        db.Index('ix_doc_classification', 'classification'),
    )

    @property
    def last_activity_details(self):
        """Return the last user who sent the document and the timestamp"""
        last_activity = ActivityLog.query.filter(
            ActivityLog.document_id == self.id,
            ActivityLog.action.in_(['Batch Forwarded', 'Forwarded', 'Resubmitted', 'Created'])
        ).order_by(ActivityLog.timestamp.desc()).first()
        
        if last_activity:
            return {'user': last_activity.user, 'timestamp': last_activity.timestamp}
        return {'user': self.creator, 'timestamp': self.timestamp}

    def restore_from_archive(self):
        """Helper method to restore document from archive"""
        self.status = 'Pending'
        return self

    def to_dict(self):
        """Convert Document instance to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'title': self.title,
            'office': self.office,
            'classification': self.classification,
            'status': self.status,
            'action_taken': self.action_taken,
            'remarks': self.remarks,
            'attachment': self.attachment,
            'barcode': self.barcode,  # Add barcode to dictionary
            'no_dtas_flag': self.no_dtas_flag,
            'creator': self.creator.username,
            'recipient': self.recipient.username,
            'timestamp': format_timestamp(self.timestamp),
            'accepted_timestamp': format_timestamp(self.accepted_timestamp),
            'released_timestamp': format_timestamp(self.released_timestamp),
            'forwarded_timestamp': format_timestamp(self.forwarded_timestamp)
        }

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    action = db.Column(db.String(50), nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id', ondelete='CASCADE'), nullable=False)
    
    # Add this relationship
    user = db.relationship('User', foreign_keys=[user_id])
    
    __table_args__ = (db.Index('idx_document_id', 'document_id'),)

    def __init__(self, user=None, document_id=None, action=None, remarks=None):
        self.user_id = user.id if user else None  # Change this line
        self.document_id = document_id
        self.action = action
        self.remarks = remarks

    def to_dict(self):
        """Convert ActivityLog instance to dictionary for JSON serialization"""
        manila_tz = pytz.timezone('Asia/Manila')
        local_time = self.timestamp.replace(tzinfo=pytz.UTC).astimezone(manila_tz)
        
        return {
            'id': self.id,
            'timestamp': local_time.strftime('%B %d, %Y at %I:%M %p'),
            'action': self.action,
            'remarks': self.remarks,
            'user': {'username': self.user.username} if self.user else None
        }

def format_timedelta(td):
    if not hasattr(td, 'days'):
        from datetime import timedelta
        td = timedelta(seconds=td)
    days = td.days
    seconds = td.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    
    # Build the string showing only non-zero values
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    
    # If all values are zero, show at least minutes
    if not parts:
        return "less than 1m"
    
    return " ".join(parts)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # User receiving the notification
    message = db.Column(db.String(200), nullable=False)  # Notification message
    is_read = db.Column(db.Boolean, default=False, nullable=False)  # Whether the notification has been read
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # Timestamp of the notification

    # Relationship
    user = db.relationship('User', backref='notifications')
    
    @property
    def formatted_timestamp(self):
        """Return properly formatted timestamp in Manila time"""
        manila_tz = pytz.timezone('Asia/Manila')
        local_time = self.timestamp.replace(tzinfo=pytz.UTC).astimezone(manila_tz)
        return local_time


class SLAAlertPreference(db.Model):
    __tablename__ = 'sla_alert_preferences'

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), unique=True, nullable=False)
    enabled = db.Column(db.Boolean, nullable=False, default=True, server_default='1')
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    DEFAULTS = {
        'documents': True,
        'leave_requests': True,
        'ewp_records': True,
    }

    @classmethod
    def ensure_defaults(cls):
        """
        Ensure default preference rows exist. Safe to call multiple times.
        """
        created = False
        for key, default in cls.DEFAULTS.items():
            if not cls.query.filter_by(category=key).first():
                db.session.add(cls(category=key, enabled=default))
                created = True
        if created:
            db.session.flush()

    @classmethod
    def get_preferences_map(cls):
        """
        Return a dictionary of category -> enabled, falling back to defaults.
        """
        cls.ensure_defaults()
        prefs = {row.category: row.enabled for row in cls.query.all()}
        for key, default in cls.DEFAULTS.items():
            prefs.setdefault(key, default)
        return prefs

    @classmethod
    def set_enabled(cls, category: str, enabled: bool):
        """
        Persist a boolean preference for a category, creating it if needed.
        """
        pref = cls.query.filter_by(category=category).first()
        if not pref:
            pref = cls(category=category)
            db.session.add(pref)
        pref.enabled = bool(enabled)


class ProcessingLog(db.Model):
    __tablename__ = 'processing_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=False)
    accepted_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    forwarded_timestamp = db.Column(db.DateTime)
    
    user = db.relationship('User', backref='processing_logs')
    # Update document relationship to use back_populates rather than backref
    document = db.relationship('Document', back_populates='processing_logs')

class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'

    id = db.Column(db.Integer, primary_key=True)
    barcode = db.Column(db.String(50), index=True, nullable=True)
    employee_name = db.Column(db.String(120), nullable=False)
    office = db.Column(db.String(100), nullable=False)
    # Map attribute leave_type to DB column name 'type' to avoid Python built-in name collision
    leave_type = db.Column('type', db.String(50), nullable=False, default='Others', server_default='Others')
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    created_timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    released_timestamp = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='For Computation', server_default='For Computation')
    remarks = db.Column(db.Text, nullable=True)
    # New: subtype and subtype_detail to capture additional Type info
    subtype = db.Column(db.String(100), nullable=True)
    subtype_detail = db.Column(db.Text, nullable=True)
    # Track who created the leave request (visibility for metrics)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True, nullable=True)
    created_by = db.relationship('User', foreign_keys=[created_by_user_id])
    # Multiple date ranges associated to this leave request
    date_ranges = db.relationship('LeaveDateRange',
                                  backref='leave_request',
                                  cascade='all, delete-orphan',
                                  order_by='LeaveDateRange.start_date')

    def to_dict(self):
        return {
            'id': self.id,
            'barcode': self.barcode,
            'employee_name': self.employee_name,
            'office': self.office,
            'type': self.leave_type,
            'subtype': self.subtype,
            'subtype_detail': self.subtype_detail,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'created_timestamp': format_timestamp(self.created_timestamp),
            'released_timestamp': format_timestamp(self.released_timestamp),
            'status': self.status,
            'remarks': self.remarks,
            'date_ranges': [
                {
                    'id': r.id,
                    'start_date': r.start_date.isoformat() if r.start_date else None,
                    'end_date': r.end_date.isoformat() if r.end_date else None
                } for r in (self.date_ranges or [])
            ]
        }

class LeaveDateRange(db.Model):
    __tablename__ = 'leave_date_ranges'

    id = db.Column(db.Integer, primary_key=True)
    leave_request_id = db.Column(db.Integer, db.ForeignKey('leave_requests.id', ondelete='CASCADE'), nullable=False, index=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    # Per-range time selection: FULL_DAY (default), AM_HALF, PM_HALF
    time_mode = db.Column(db.String(20), nullable=False, default='FULL_DAY', server_default='FULL_DAY')

    def to_dict(self):
        return {
            'id': self.id,
            'leave_request_id': self.leave_request_id,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'time_mode': self.time_mode or 'FULL_DAY'
        }

class EWPRecord(db.Model):
    __tablename__ = 'ewp_records'

    id = db.Column(db.Integer, primary_key=True)
    barcode = db.Column(db.String(50), index=True, nullable=True)
    employee_name = db.Column(db.String(120), nullable=False)
    office = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    purpose = db.Column(db.Text, nullable=True)
    remarks = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='For Computation', server_default='For Computation')
    created_timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True, nullable=True)

    created_by = db.relationship('User', foreign_keys=[created_by_user_id])

    def to_dict(self):
        return {
            'id': self.id,
            'barcode': self.barcode,
            'employee_name': self.employee_name,
            'office': self.office,
            'amount': format(self.amount, '.2f') if self.amount is not None else None,
            'purpose': self.purpose,
            'remarks': self.remarks,
            'status': self.status,
            'created_timestamp': format_timestamp(self.created_timestamp),
            'created_by_user_id': self.created_by_user_id
        }

# New Employee model for Employee Records functionality
class Employee(db.Model):
    __tablename__ = 'employees'

    id = db.Column(db.Integer, primary_key=True)
    bio_number = db.Column(db.String(50), unique=True, nullable=False)
    employee_name = db.Column(db.String(120), nullable=False)
    office = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Active', server_default='Active')  # Active/Inactive account status

    # Personal Information (Phase 1)
    surname = db.Column(db.String(120), nullable=True)
    first_name = db.Column(db.String(120), nullable=True)
    middle_name = db.Column(db.String(120), nullable=True)
    name_extension = db.Column(db.String(20), nullable=True)

    date_of_birth = db.Column(db.String(20), nullable=True)  # store as string mm/dd/yyyy for simplicity
    place_of_birth = db.Column(db.String(200), nullable=True)

    sex = db.Column(db.String(20), nullable=True)  # Male/Female/Other
    civil_status = db.Column(db.String(20), nullable=True)  # Single/Married/...

    height_m = db.Column(db.String(10), nullable=True)
    weight_kg = db.Column(db.String(10), nullable=True)
    blood_type = db.Column(db.String(10), nullable=True)

    gsis_id_no = db.Column(db.String(120), nullable=True)
    pagibig_id_no = db.Column(db.String(120), nullable=True)
    philhealth_no = db.Column(db.String(120), nullable=True)
    sss_no = db.Column(db.String(120), nullable=True)
    tin = db.Column(db.String(120), nullable=True)
    agency_employee_no = db.Column(db.String(120), nullable=True)

    citizenship = db.Column(db.String(120), nullable=True)
    citizenship_details = db.Column(db.Text, nullable=True)

    # Residential Address
    res_house_lot = db.Column(db.String(150), nullable=True)
    res_street = db.Column(db.String(150), nullable=True)
    res_subdivision = db.Column(db.String(150), nullable=True)
    res_barangay = db.Column(db.String(150), nullable=True)
    res_city_municipality = db.Column(db.String(150), nullable=True)
    res_province = db.Column(db.String(150), nullable=True)
    res_zip_code = db.Column(db.String(10), nullable=True)

    # Permanent Address
    perm_house_lot = db.Column(db.String(150), nullable=True)
    perm_street = db.Column(db.String(150), nullable=True)
    perm_subdivision = db.Column(db.String(150), nullable=True)
    perm_barangay = db.Column(db.String(150), nullable=True)
    perm_city_municipality = db.Column(db.String(150), nullable=True)
    perm_province = db.Column(db.String(150), nullable=True)
    perm_zip_code = db.Column(db.String(10), nullable=True)

    # Contact
    telephone_no = db.Column(db.String(120), nullable=True)
    mobile_no = db.Column(db.String(120), nullable=True)
    email_address = db.Column(db.String(120), nullable=True)

    # Family Background
    spouse_surname = db.Column(db.String(120), nullable=True)
    spouse_first_name = db.Column(db.String(120), nullable=True)
    spouse_middle_name = db.Column(db.String(120), nullable=True)
    spouse_occupation = db.Column(db.String(120), nullable=True)
    spouse_employer_name = db.Column(db.String(150), nullable=True)
    spouse_business_address = db.Column(db.String(255), nullable=True)
    spouse_telephone_no = db.Column(db.String(120), nullable=True)

    father_surname = db.Column(db.String(120), nullable=True)
    father_first_name = db.Column(db.String(120), nullable=True)
    father_middle_name = db.Column(db.String(120), nullable=True)
    father_extension = db.Column(db.String(20), nullable=True)

    mother_maiden_surname = db.Column(db.String(120), nullable=True)
    mother_maiden_first_name = db.Column(db.String(120), nullable=True)
    mother_maiden_middle_name = db.Column(db.String(120), nullable=True)

    children_info = db.Column(db.Text, nullable=True)

    # Educational Background - Elementary
    elem_school_name = db.Column(db.String(255), nullable=True)
    elem_basic_education = db.Column(db.String(255), nullable=True)
    elem_period_from = db.Column(db.String(20), nullable=True)
    elem_period_to = db.Column(db.String(20), nullable=True)
    elem_highest_level = db.Column(db.String(255), nullable=True)
    elem_year_graduated = db.Column(db.String(10), nullable=True)
    elem_scholarships = db.Column(db.String(255), nullable=True)

    # Educational Background - Secondary
    sec_school_name = db.Column(db.String(255), nullable=True)
    sec_basic_education = db.Column(db.String(255), nullable=True)
    sec_period_from = db.Column(db.String(20), nullable=True)
    sec_period_to = db.Column(db.String(20), nullable=True)
    sec_highest_level = db.Column(db.String(255), nullable=True)
    sec_year_graduated = db.Column(db.String(10), nullable=True)
    sec_scholarships = db.Column(db.String(255), nullable=True)

    # Educational Background - Vocational
    voc_school_name = db.Column(db.String(255), nullable=True)
    voc_basic_education = db.Column(db.String(255), nullable=True)
    voc_period_from = db.Column(db.String(20), nullable=True)
    voc_period_to = db.Column(db.String(20), nullable=True)
    voc_highest_level = db.Column(db.String(255), nullable=True)
    voc_year_graduated = db.Column(db.String(10), nullable=True)
    voc_scholarships = db.Column(db.String(255), nullable=True)

    # Educational Background - College
    college_school_name = db.Column(db.String(255), nullable=True)
    college_basic_education = db.Column(db.String(255), nullable=True)
    college_period_from = db.Column(db.String(20), nullable=True)
    college_period_to = db.Column(db.String(20), nullable=True)
    college_highest_level = db.Column(db.String(255), nullable=True)
    college_year_graduated = db.Column(db.String(10), nullable=True)
    college_scholarships = db.Column(db.String(255), nullable=True)

    # Educational Background - Graduate Studies
    grad_school_name = db.Column(db.String(255), nullable=True)
    grad_basic_education = db.Column(db.String(255), nullable=True)
    grad_period_from = db.Column(db.String(20), nullable=True)
    grad_period_to = db.Column(db.String(20), nullable=True)
    grad_highest_level = db.Column(db.String(255), nullable=True)
    grad_year_graduated = db.Column(db.String(10), nullable=True)
    grad_scholarships = db.Column(db.String(255), nullable=True)

    elem_records_json = db.Column(db.Text, nullable=True)
    sec_records_json = db.Column(db.Text, nullable=True)
    voc_records_json = db.Column(db.Text, nullable=True)
    college_records_json = db.Column(db.Text, nullable=True)
    grad_records_json = db.Column(db.Text, nullable=True)
    civil_service_records_json = db.Column(db.Text, nullable=True)
    work_experience_json = db.Column(db.Text, nullable=True)
    voluntary_work_json = db.Column(db.Text, nullable=True)
    learning_dev_json = db.Column(db.Text, nullable=True)

    def _primary_education_entry(self, prefix):
        entry = {field: (getattr(self, f"{prefix}_{field}", '') or '').strip() for field in EDUCATION_FIELD_NAMES}
        if any(entry.values()):
            return entry
        return {}

    def _education_records(self, prefix):
        records = []
        json_field = getattr(self, f"{prefix}_records_json", None)
        if json_field:
            try:
                parsed = json.loads(json_field)
                if isinstance(parsed, list):
                    for item in parsed:
                        if not isinstance(item, dict):
                            continue
                        normalized = {field: (item.get(field) or '').strip() for field in EDUCATION_FIELD_NAMES}
                        if any(normalized.values()):
                            records.append(normalized)
            except Exception:
                records = []
        if not records:
            primary = self._primary_education_entry(prefix)
            if primary:
                records.append(primary)
        return records

    @property
    def elem_records(self):
        return self._education_records('elem')

    @property
    def sec_records(self):
        return self._education_records('sec')

    @property
    def voc_records(self):
        return self._education_records('voc')

    @property
    def college_records(self):
        return self._education_records('college')

    @property
    def grad_records(self):
        return self._education_records('grad')

    def _civil_service_records_internal(self):
        records = []
        raw_json = self.civil_service_records_json
        if raw_json:
            try:
                parsed = json.loads(raw_json)
            except Exception:
                parsed = []
            if isinstance(parsed, list):
                for entry in parsed:
                    if not isinstance(entry, dict):
                        continue
                    normalized = {
                        field: (entry.get(field) or '').strip()
                        for field in CIVIL_SERVICE_FIELD_NAMES
                    }
                    if any(normalized.values()):
                        records.append(normalized)
        return records

    @property
    def civil_service_records(self):
        return self._civil_service_records_internal()

    def _work_experience_records_internal(self):
        records = []
        raw_json = self.work_experience_json
        if raw_json:
            try:
                parsed = json.loads(raw_json)
            except Exception:
                parsed = []
            if isinstance(parsed, list):
                for entry in parsed:
                    if not isinstance(entry, dict):
                        continue
                    normalized = {
                        field: (entry.get(field) or '').strip()
                        for field in WORK_EXPERIENCE_FIELD_NAMES
                    }
                    if any(normalized.values()):
                        records.append(normalized)
        return records

    @property
    def work_experience_records(self):
        return self._work_experience_records_internal()

    def _voluntary_work_records_internal(self):
        records = []
        raw_json = self.voluntary_work_json
        if raw_json:
            try:
                parsed = json.loads(raw_json)
            except Exception:
                parsed = []
            if isinstance(parsed, list):
                for entry in parsed:
                    if not isinstance(entry, dict):
                        continue
                    normalized = {
                        field: (entry.get(field) or '').strip()
                        for field in VOLUNTARY_WORK_FIELD_NAMES
                    }
                    if any(normalized.values()):
                        records.append(normalized)
        return records

    @property
    def voluntary_work_records(self):
        return self._voluntary_work_records_internal()

    def _learning_dev_records_internal(self):
        records = []
        raw_json = self.learning_dev_json
        if raw_json:
            try:
                parsed = json.loads(raw_json)
            except Exception:
                parsed = []
            if isinstance(parsed, list):
                for entry in parsed:
                    if not isinstance(entry, dict):
                        continue
                    normalized = {
                        field: (entry.get(field) or '').strip()
                        for field in LEARNING_DEV_FIELD_NAMES
                    }
                    if any(normalized.values()):
                        records.append(normalized)
        return records

    @property
    def learning_dev_records(self):
        return self._learning_dev_records_internal()

    def to_dict(self):
        return {
            'id': self.id,
            'bio_number': self.bio_number,
            'employee_name': self.employee_name,
            'office': self.office,
            'position': self.position,
            'status': self.status,
            'surname': self.surname,
            'first_name': self.first_name,
            'middle_name': self.middle_name,
            'name_extension': self.name_extension,
            'date_of_birth': self.date_of_birth,
            'place_of_birth': self.place_of_birth,
            'sex': self.sex,
            'civil_status': self.civil_status,
            'height_m': self.height_m,
            'weight_kg': self.weight_kg,
            'blood_type': self.blood_type,
            'gsis_id_no': self.gsis_id_no,
            'pagibig_id_no': self.pagibig_id_no,
            'philhealth_no': self.philhealth_no,
            'sss_no': self.sss_no,
            'tin': self.tin,
            'agency_employee_no': self.agency_employee_no,
            'citizenship': self.citizenship,
            'citizenship_details': self.citizenship_details,
            'res_house_lot': self.res_house_lot,
            'res_street': self.res_street,
            'res_subdivision': self.res_subdivision,
            'res_barangay': self.res_barangay,
            'res_city_municipality': self.res_city_municipality,
            'res_province': self.res_province,
            'res_zip_code': self.res_zip_code,
            'perm_house_lot': self.perm_house_lot,
            'perm_street': self.perm_street,
            'perm_subdivision': self.perm_subdivision,
            'perm_barangay': self.perm_barangay,
            'perm_city_municipality': self.perm_city_municipality,
            'perm_province': self.perm_province,
            'perm_zip_code': self.perm_zip_code,
            'telephone_no': self.telephone_no,
            'mobile_no': self.mobile_no,
            'email_address': self.email_address,
            'spouse_surname': self.spouse_surname,
            'spouse_first_name': self.spouse_first_name,
            'spouse_middle_name': self.spouse_middle_name,
            'spouse_occupation': self.spouse_occupation,
            'spouse_employer_name': self.spouse_employer_name,
            'spouse_business_address': self.spouse_business_address,
            'spouse_telephone_no': self.spouse_telephone_no,
            'father_surname': self.father_surname,
            'father_first_name': self.father_first_name,
            'father_middle_name': self.father_middle_name,
            'father_extension': self.father_extension,
            'mother_maiden_surname': self.mother_maiden_surname,
            'mother_maiden_first_name': self.mother_maiden_first_name,
            'mother_maiden_middle_name': self.mother_maiden_middle_name,
            'children_info': self.children_info,
            'elem_school_name': self.elem_school_name,
            'elem_basic_education': self.elem_basic_education,
            'elem_period_from': self.elem_period_from,
            'elem_period_to': self.elem_period_to,
            'elem_highest_level': self.elem_highest_level,
            'elem_year_graduated': self.elem_year_graduated,
            'elem_scholarships': self.elem_scholarships,
            'sec_school_name': self.sec_school_name,
            'sec_basic_education': self.sec_basic_education,
            'sec_period_from': self.sec_period_from,
            'sec_period_to': self.sec_period_to,
            'sec_highest_level': self.sec_highest_level,
            'sec_year_graduated': self.sec_year_graduated,
            'sec_scholarships': self.sec_scholarships,
            'voc_school_name': self.voc_school_name,
            'voc_basic_education': self.voc_basic_education,
            'voc_period_from': self.voc_period_from,
            'voc_period_to': self.voc_period_to,
            'voc_highest_level': self.voc_highest_level,
            'voc_year_graduated': self.voc_year_graduated,
            'voc_scholarships': self.voc_scholarships,
            'college_school_name': self.college_school_name,
            'college_basic_education': self.college_basic_education,
            'college_period_from': self.college_period_from,
            'college_period_to': self.college_period_to,
            'college_highest_level': self.college_highest_level,
            'college_year_graduated': self.college_year_graduated,
            'college_scholarships': self.college_scholarships,
            'grad_school_name': self.grad_school_name,
            'grad_basic_education': self.grad_basic_education,
            'grad_period_from': self.grad_period_from,
            'grad_period_to': self.grad_period_to,
            'grad_highest_level': self.grad_highest_level,
            'grad_year_graduated': self.grad_year_graduated,
            'grad_scholarships': self.grad_scholarships,
            'elem_records_json': self.elem_records_json,
            'sec_records_json': self.sec_records_json,
            'voc_records_json': self.voc_records_json,
            'college_records_json': self.college_records_json,
            'grad_records_json': self.grad_records_json,
            'civil_service_records_json': self.civil_service_records_json,
            'work_experience_json': self.work_experience_json,
            'voluntary_work_json': self.voluntary_work_json,
            'learning_dev_json': self.learning_dev_json,
            'elem_records': self.elem_records,
            'sec_records': self.sec_records,
            'voc_records': self.voc_records,
            'college_records': self.college_records,
            'grad_records': self.grad_records,
            'civil_service_records': self.civil_service_records,
            'work_experience_records': self.work_experience_records,
            'voluntary_work_records': self.voluntary_work_records,
            'learning_dev_records': self.learning_dev_records
        }
