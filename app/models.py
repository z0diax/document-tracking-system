import pytz
from datetime import datetime
from flask_login import UserMixin
from app import db, login_manager
# Remove the to_local_time import as it's causing circular import
from werkzeug.security import generate_password_hash, check_password_hash

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    # Changed column size for password_hash
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    # Per-user permission to access Leave module
    can_access_leave = db.Column(db.Boolean, default=False, nullable=False, server_default='0')
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

    def to_dict(self):
        return {
            'id': self.id,
            'bio_number': self.bio_number,
            'employee_name': self.employee_name,
            'office': self.office,
            'position': self.position,
            'status': self.status
        }
