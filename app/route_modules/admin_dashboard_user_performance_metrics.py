from app import db
from app.models import LeaveRequest, ProcessingLog, User


def build_user_metrics():
    try:
        user_metrics = (
            db.session.query(
                User.username,
                db.func.count(ProcessingLog.id).label('documents_handled'),
                db.func.avg(
                    db.func.time_to_sec(
                        db.func.timediff(ProcessingLog.forwarded_timestamp, ProcessingLog.accepted_timestamp)
                    )
                ).label('avg_processing_time')
            )
            .join(ProcessingLog, ProcessingLog.user_id == User.id)
            .filter(ProcessingLog.forwarded_timestamp != None)
            .group_by(User.username)
            .all()
        )
    except Exception:
        user_metrics = []

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

    return user_metrics, leave_user_metrics
