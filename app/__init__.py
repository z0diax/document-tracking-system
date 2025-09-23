from flask import Flask, Blueprint, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from config import Config, ProductionConfig
import pytz
from datetime import datetime
import os
from decimal import Decimal

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'main.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Force refresh - critical for security
login_manager.needs_refresh_message = "To protect your account, please log in again to verify your identity."
login_manager.needs_refresh_message_category = "info"
login_manager.refresh_view = 'main.login'
login_manager.session_protection = "strong"  # Set to strong protection

csrf = CSRFProtect()

# Define helper functions for timezone and timedelta formatting before create_app
def to_local_time(utc_dt):
    """Convert UTC datetime to local Manila time"""
    if not utc_dt:
        return None
    manila_tz = pytz.timezone('Asia/Manila')
    if utc_dt.tzinfo is None:
        utc_dt = pytz.UTC.localize(utc_dt)
    return utc_dt.astimezone(manila_tz)

def local_time(dt, format=None):
    """Convert UTC datetime to local Manila time with optional formatting"""
    if not dt:
        return None
    manila_tz = pytz.timezone('Asia/Manila')
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    local_dt = dt.astimezone(manila_tz)
    if format:
        return local_dt.strftime(format)
    return local_dt

def format_avg_timedelta(td):
    """Format a timedelta into (days, hours, minutes)."""
    if isinstance(td, Decimal):
        td = float(td)
    if not hasattr(td, 'days'):
        from datetime import timedelta
        td = timedelta(seconds=td)
    days = td.days
    seconds = td.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{days}d {hours}h {minutes}m"

def create_app(config_class=Config): 
    app = Flask(__name__)
    # Load production config if in production
    if os.getenv('FLASK_ENV') == 'production':
        app.config.from_object(ProductionConfig)
    else:
        app.config.from_object(config_class)

    # Set timezone
    app.config['TIMEZONE'] = pytz.timezone(app.config['TIMEZONE'])

    # Initialize extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    app.jinja_env.filters['timezone'] = to_local_time
    app.jinja_env.filters['strftime'] = lambda date, format: date.strftime(format) if date else ''
    app.jinja_env.filters['local_time'] = local_time
    app.jinja_env.filters['format_avg_timedelta'] = format_avg_timedelta

    from app.routes import main
    app.register_blueprint(main, url_prefix="/hrdoctrack")

    @app.before_request
    def check_user_status():
        if current_user.is_authenticated:
            # Force logout if user status is not 'Active'
            if current_user.status != 'Active':
                from flask_login import logout_user
                print(f"SECURITY: Force logging out user {current_user.username} with status '{current_user.status}'")
                logout_user()
                flash('Only users with Active status can access the system.', 'warning')
                return redirect(url_for('main.login'))

    # Add an error handler for unauthorized access
    @login_manager.unauthorized_handler
    def unauthorized():
        flash('You must be logged in with an active account to access this page.', 'danger')
        return redirect(url_for('main.login'))

    # Add local time filter
    @app.template_filter('local_time')
    def local_time_filter(dt, format='%B %d, %Y at %I:%M %p'):
        return to_local_time(dt).strftime(format) if dt else ''

    # Add format_avg_timedelta filter for average processing time
    @app.template_filter('format_avg_timedelta')
    def format_avg_timedelta_filter(seconds):
        if not seconds:
            return 'N/A'
        
        try:
            seconds = int(seconds)
            minutes, seconds = divmod(seconds, 60)
            hours, minutes = divmod(minutes, 60)
            days, hours = divmod(hours, 24)
            
            parts = []
            if days > 0:
                parts.append(f"{days} day{'s' if days != 1 else ''}")
            if hours > 0:
                parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
            if minutes > 0:
                parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
            
            return ", ".join(parts) if parts else "less than a minute"
        except:
            return 'Error calculating time'

    # Initialize the scheduler
    init_scheduler(app)

    return app

@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))

def init_scheduler(app):
    """
    Initializes and starts the background scheduler.
    """
    from apscheduler.schedulers.background import BackgroundScheduler
    from app.auto_archive import archive_old_documents

    scheduler = BackgroundScheduler()
    scheduler.add_job(archive_old_documents, 'cron', hour=0, minute=0)  # Run daily at midnight
    scheduler.start()
