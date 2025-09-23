import os
os.environ['DATABASE_URL'] = 'sqlite:///test_auto_archive.db'

from datetime import datetime, timedelta

from app import create_app, db
from app.models import User, Document, ActivityLog
from app.auto_archive import archive_old_documents


def main():
    app = create_app()
    with app.app_context():
        db.create_all()
        # Ensure a test user exists
        username = "auto_archive_tester"
        email = "auto_archive_tester@example.com"
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username, email=email, is_admin=False, status='Active')
            user.password = "TempPass123!"
            db.session.add(user)
            db.session.commit()

        now = datetime.utcnow()
        first_day_current = datetime(now.year, now.month, 1)
        last_month_day = first_day_current - timedelta(days=1)
        two_months_ago_day = first_day_current - timedelta(days=40)
        current_month_date = first_day_current + timedelta(days=1) if now.day == 1 else now

        def create_doc(title: str, ts: datetime) -> Document:
            d = Document(
                title=title,
                office="QA",
                classification="Test",
                status="Pending",
                action_taken="None",
                attachment=None,
                remarks="Test document for auto-archive",
                barcode=None,
                timestamp=ts,
                accepted_timestamp=None,
                released_timestamp=None,
                forwarded_timestamp=None,
                creator_id=user.id,
                recipient_id=user.id,
            )
            db.session.add(d)
            db.session.commit()
            return d

        # Create sample documents
        d1 = create_doc(
            "AutoArchive Test - Last Month",
            datetime(last_month_day.year, last_month_day.month, last_month_day.day, 12, 0, 0),
        )
        d2 = create_doc(
            "AutoArchive Test - Current Month",
            datetime(current_month_date.year, current_month_date.month, current_month_date.day, 12, 0, 0),
        )
        d3 = create_doc(
            "AutoArchive Test - Two Months Ago",
            datetime(two_months_ago_day.year, two_months_ago_day.month, two_months_ago_day.day, 12, 0, 0),
        )

        # Run the archive job once
        result = archive_old_documents()

        # Reload from DB
        d1 = Document.query.get(d1.id)
        d2 = Document.query.get(d2.id)
        d3 = Document.query.get(d3.id)

        def auto_log_count(doc_id: int) -> int:
            return ActivityLog.query.filter_by(document_id=doc_id, action="Auto Archived").count()

        print("Job result:", result)
        print("Statuses after job run:")
        print(f"  Last Month       (d1): status={d1.status}, auto_logs={auto_log_count(d1.id)}")
        print(f"  Current Month    (d2): status={d2.status}, auto_logs={auto_log_count(d2.id)}")
        print(f"  Two Months Ago   (d3): status={d3.status}, auto_logs={auto_log_count(d3.id)}")

        # Cleanup created test data
        try:
            for doc in [d1, d2, d3]:
                db.session.delete(doc)
            db.session.commit()
            print("Cleanup: deleted test documents.")
        except Exception as e:
            db.session.rollback()
            print("Cleanup failed:", e)


if __name__ == "__main__":
    main()
