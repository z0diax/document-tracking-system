from flask import Blueprint
from flask_login import current_user

from app.models import User

OFFICE_CHOICES = [
    ('CMO', 'CMO'), ('CMO - CARPOOL', 'CMO - CARPOOL'), ('CMO - YOUTH', 'CMO - YOUTH'),
    ('CMO - NORTH', 'CMO - NORTH'), ('CMO - SUPPLY', 'CMO - SUPPLY'), ('CADMO', 'CADMO'),
    ('VMO', 'VMO'), ('SP', 'SP'), ('CPDO', 'CPDO'), ('CLGOO', 'CLGOO'), ('CTO', 'CTO'),
    ('CAO', 'CAO'), ('CASSO', 'CASSO'), ('CBO', 'CBO'), ('HRMDO', 'HRMDO'), ('CCRO', 'CCRO'),
    ('CDO', 'CDO'), ('CHO', 'CHO'), ('TCH', 'TCH'), ('CPO', 'CPO'), ('CSWDO', 'CSWDO'),
    ('CEO', 'CEO'), ('OBO', 'OBO'), ('CGSO', 'CGSO'), ('CENRO', 'CENRO'), ('CAGRIO', 'CAGRIO'),
    ('CVO', 'CVO'), ('EED', 'EED'), ('CIAS', 'CIAS'), ('TOMECO', 'TOMECO'), ('CIO', 'CIO'),
    ('CHCDO', 'CHCDO'), ('CDRRMO', 'CDRRMO'), ('CCDLAO', 'CCDLAO'), ('CTOO', 'CTOO'),
    ('CLO', 'CLO'), ('CMISO', 'CMISO'), ('CLEP', 'CLEP'), ('SPORTS', 'SPORTS'),
    ('BPLD', 'BPLD'), ('FLET', 'FLET'), ('TACRU', 'TACRU'), ('CNO', 'CNO'), ('TNSH', 'TNSH'),
    ('PDAO', 'PDAO'), ('OSCA', 'OSCA'), ('TCPO', 'TCPO'), ('PESO', 'PESO'),
    ('TCCC', 'TCCC'), ('TNBT', 'TNBT'), ('BAC', 'BAC'), ('DILG', 'DILG'),
    ('COMELEC', 'COMELEC'), ('COA', 'COA'), ('CACO', 'CACO'),
]

CLASSIFICATION_CHOICES = [
    ('Communications', 'Communications'),
    ('Payroll', 'Payroll'),
    ('Request', 'Request'),
    ('Others', 'Others'),
]

STATUS_CHOICES = [
    ('For Checking', 'For Checking'),
    ('For Signature', 'For Signature'),
    ('Pending', 'Pending'),
    ('Declined', 'Declined'),
]

ACTION_TAKEN_CHOICES = [
    ('Noted', 'Noted'),
    ('Signed', 'Signed'),
    ('Approved', 'Approved'),
    ('Verified', 'Verified'),
    ('For Review', 'For Review'),
    ('For Revision', 'For Revision'),
    ('For Approval', 'For Approval'),
    ('Endorsed', 'Endorsed'),
]

RSP_TOTAL_PHASES = 12
RSP_PHASE_NAMES = [
    'Publication of Vacant Positions/Talent Sourcing/Notice to NIR',
    'Preliminary Evaluation',
    'Notification for Pre-Qualifying Examination',
    'Conduct of Pre-Qualifying Examination',
    'Establishment of Pre-Qualifying Examination Result',
    'Notification of Qualified Applicants for HRMPSB Deliberation',
    'Conduct of HRMPSB Deliberation',
    'Finalization and Confirmation',
    'Conduct of Background Investigation',
    'Endorsement of Assessment Results to Appointing Authority',
    'Preparation and Issuance of Appointment',
    'Posting of Notice of Appointment',
]

main = Blueprint('main', __name__)


def get_rsp_phase_name(phase_number):
    try:
        idx = int(phase_number) - 1
    except Exception:
        idx = -1
    if 0 <= idx < len(RSP_PHASE_NAMES):
        return RSP_PHASE_NAMES[idx]
    return f'Phase {phase_number}'


def get_recipient_choices():
    """Return list of recipient choices excluding current user."""
    if not current_user.is_authenticated:
        return []
    return [(user.id, user.username) for user in User.query.filter(User.id != current_user.id).all()]
