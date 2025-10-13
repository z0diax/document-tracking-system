import os

"""
Configuration example for the Document Tracking System.

Usage:
1) Copy this file to 'config.py' (which is ignored by git):
   cp config.example.py config.py

2) Set the required environment variables in your shell or a .env file
   (note: .env is ignored by git):
   - SECRET_KEY
   - DATABASE_URL
   - Optional:
       FLASK_DEBUG (0/1)
       TIMEZONE (default: Asia/Manila)
       HOST (default: 0.0.0.0)
       PORT (default: 5000)

3) Do NOT commit config.py; commit only this example file.
"""

class Config:
    # Required: enforce via environment to avoid leaking secrets
    SECRET_KEY = os.environ["SECRET_KEY"]

    # Database: use env-provided URL; example for MySQL:
    #   mysql+pymysql://USER:PASSWORD@HOST/DATABASE
    # or for SQLite (development):
    #   sqlite:///instance/site.db
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "mysql+pymysql://USER:PASSWORD@HOST/DATABASE")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flags
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
    TESTING = False

    # Paths
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

    # App specifics
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
    TIMEZONE = os.environ.get("TIMEZONE", "Asia/Manila")
    SLA_RULES = {
        "Document": {
            "Pending": {
                "warn_after_hours": float(os.environ.get("SLA_DOC_PENDING_WARN_HOURS", "8")),
                "escalate_after_hours": float(os.environ.get("SLA_DOC_PENDING_ESCALATE_HOURS", "16")),
                "use_business_hours": True,
                "notify_creator": True,
                "notify_recipient": True,
                "escalate_to_admins": True,
                "dedupe_hours": float(os.environ.get("SLA_DOC_PENDING_DEDUPE_HOURS", "6")),
                "escalation_dedupe_hours": float(os.environ.get("SLA_DOC_PENDING_ESC_DEDUPE_HOURS", "12")),
            }
        },
        "LeaveRequest": {
            "Pending": {
                "warn_after_hours": float(os.environ.get("SLA_LEAVE_PENDING_WARN_HOURS", "24")),
                "escalate_after_hours": float(os.environ.get("SLA_LEAVE_PENDING_ESCALATE_HOURS", "48")),
                "use_business_hours": False,
                "notify_creator": True,
                "escalate_to_admins": True,
                "dedupe_hours": float(os.environ.get("SLA_LEAVE_PENDING_DEDUPE_HOURS", "12")),
                "escalation_dedupe_hours": float(os.environ.get("SLA_LEAVE_PENDING_ESC_DEDUPE_HOURS", "24")),
            },
            "For Computation": {
                "warn_after_hours": float(os.environ.get("SLA_LEAVE_FORCOMP_WARN_HOURS", "24")),
                "escalate_after_hours": float(os.environ.get("SLA_LEAVE_FORCOMP_ESCALATE_HOURS", "48")),
                "use_business_hours": False,
                "notify_creator": True,
                "escalate_to_admins": True,
                "dedupe_hours": float(os.environ.get("SLA_LEAVE_FORCOMP_DEDUPE_HOURS", "12")),
                "escalation_dedupe_hours": float(os.environ.get("SLA_LEAVE_FORCOMP_ESC_DEDUPE_HOURS", "24")),
            },
            "For Signature": {
                "warn_after_hours": float(os.environ.get("SLA_LEAVE_FORSIG_WARN_HOURS", "16")),
                "escalate_after_hours": float(os.environ.get("SLA_LEAVE_FORSIG_ESCALATE_HOURS", "32")),
                "use_business_hours": False,
                "notify_creator": True,
                "escalate_to_admins": True,
                "dedupe_hours": float(os.environ.get("SLA_LEAVE_FORSIG_DEDUPE_HOURS", "12")),
                "escalation_dedupe_hours": float(os.environ.get("SLA_LEAVE_FORSIG_ESC_DEDUPE_HOURS", "24")),
            },
        },
        "EWPRecord": {
            "Pending": {
                "warn_after_hours": float(os.environ.get("SLA_EWP_PENDING_WARN_HOURS", "24")),
                "escalate_after_hours": float(os.environ.get("SLA_EWP_PENDING_ESCALATE_HOURS", "48")),
                "use_business_hours": False,
                "notify_creator": True,
                "escalate_to_admins": True,
                "dedupe_hours": float(os.environ.get("SLA_EWP_PENDING_DEDUPE_HOURS", "12")),
                "escalation_dedupe_hours": float(os.environ.get("SLA_EWP_PENDING_ESC_DEDUPE_HOURS", "24")),
            },
            "For Computation": {
                "warn_after_hours": float(os.environ.get("SLA_EWP_FORCOMP_WARN_HOURS", "16")),
                "escalate_after_hours": float(os.environ.get("SLA_EWP_FORCOMP_ESCALATE_HOURS", "36")),
                "use_business_hours": False,
                "notify_creator": True,
                "escalate_to_admins": True,
                "dedupe_hours": float(os.environ.get("SLA_EWP_FORCOMP_DEDUPE_HOURS", "12")),
                "escalation_dedupe_hours": float(os.environ.get("SLA_EWP_FORCOMP_ESC_DEDUPE_HOURS", "24")),
            },
        },
    }

    # Host/Port
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", "5000"))

class ProductionConfig:
    DEBUG = False
    TESTING = False

    LOG_LEVEL = "WARNING"

    SEND_FILE_MAX_AGE_DEFAULT = 86400

    COMPRESS_LEVEL = 6

# MIME type mapping
MIME_TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
}

# Upload folder configuration
UPLOAD_FOLDER = "uploads"
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
