import os
from flask import current_app, url_for
from werkzeug.utils import secure_filename
from datetime import time, timedelta, datetime
import pytz

def calculate_business_hours(start_dt, end_dt, holidays=None):
    """
    Calculates the total business hours (Mon-Fri, 8am-5pm) between two datetimes,
    excluding weekends and holidays.
    """
    if not start_dt or not end_dt:
        return timedelta()

    # Define business hours
    business_start = time(8, 0)
    business_end = time(17, 0)

    # Ensure datetimes are timezone-aware (assuming UTC from DB)
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=pytz.UTC)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=pytz.UTC)

    # Convert to local time for business hour logic
    local_tz = pytz.timezone('Asia/Manila')
    start_dt = start_dt.astimezone(local_tz)
    end_dt = end_dt.astimezone(local_tz)

    # Placeholder for holidays
    holidays = holidays or []

    total_business_hours = timedelta()
    current_dt = start_dt

    while current_dt < end_dt:
        # Skip weekends and holidays
        if current_dt.weekday() >= 5 or current_dt.date() in holidays:
            current_dt += timedelta(days=1)
            current_dt = current_dt.replace(hour=business_start.hour, minute=business_start.minute, second=0)
            continue

        # Clamp start time to business hours
        day_start = current_dt.replace(hour=business_start.hour, minute=business_start.minute, second=0)
        day_end = current_dt.replace(hour=business_end.hour, minute=business_end.minute, second=0)

        # Calculate time worked on the current day
        start_of_period = max(current_dt, day_start)
        end_of_period = min(end_dt, day_end)

        if end_of_period > start_of_period:
            total_business_hours += end_of_period - start_of_period

        # Move to the next day
        current_dt += timedelta(days=1)
        current_dt = current_dt.replace(hour=business_start.hour, minute=business_start.minute, second=0)

    return total_business_hours

def get_upload_path(filename):
    """Convert filename to secure relative path"""
    secure_name = secure_filename(filename)
    return os.path.join('uploads', secure_name).replace('\\', '/')

def is_allowed_file(filename):
    """Validate uploaded file extension against ALLOWED_EXTENSIONS config"""
    if not filename:
        return False
    allowed = current_app.config.get('ALLOWED_EXTENSIONS', set()) or set()
    # Normalize to extension without leading dot, lowercased
    _, ext = os.path.splitext(filename)
    ext_norm = (ext or '').lower().lstrip('.')
    allowed_norm = {str(x).lower().lstrip('.') for x in allowed}
    return ext_norm in allowed_norm

def get_file_url(filepath):
    """Convert relative file path to URL"""
    if not filepath:
        return None
    filename = os.path.basename(filepath)
    return url_for('main.serve_file', filename=filename)
