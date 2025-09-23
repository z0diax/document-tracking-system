import os
import sys
from datetime import datetime

# Ensure project root is on sys.path so 'app' package is importable
PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Configure environment before importing app
os.environ["FLASK_ENV"] = "development"

from app import create_app, db  # noqa: E402
from app.models import User, Document, ActivityLog, Notification  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402


class TestConfig:
    SECRET_KEY = "test-secret"
    # Use a file-based sqlite to survive across app contexts in a single run
    SQLALCHEMY_DATABASE_URI = "sqlite:///test_batch_actions.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = True
    WTF_CSRF_ENABLED = False
    BASE_DIR = os.path.abspath(os.getcwd())
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads_test")
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
    TIMEZONE = "Asia/Manila"
    HOST = "127.0.0.1"
    PORT = 5001


def print_header(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def create_user(username: str, email: str, is_admin: bool = False) -> User:
    u = User(
        username=username,
        email=email,
        is_admin=is_admin,
        status="Active",
    )
    # Set password directly
    u.password_hash = generate_password_hash("password123")
    db.session.add(u)
    db.session.commit()
    return u


def client_login(client, username: str, password: str = "password123"):
    return client.post(
        "/hrdoctrack/login",
        data={
            "username": username,
            "password": password,
            "remember": "y",
        },
        follow_redirects=True,
    )


def client_logout(client):
    return client.get("/hrdoctrack/logout", follow_redirects=True)


def create_document_via_post(client, title: str, creator: User, recipient: User):
    # Must be logged in as creator in client session
    payload = {
        "title": title,
        "office": "HRMDO",
        "classification": "Communications",
        "full_classification": "Communications",  # combined value accepted by route
        "status": "Pending",
        "action_taken": "Noted",
        "remarks": "Test doc",
        "recipient": recipient.id,
    }
    resp = client.post("/hrdoctrack/create_document", data=payload, follow_redirects=True)
    return resp


def get_docs_for(user: User):
    return Document.query.filter(
        Document.recipient_id == user.id,
        Document.status != "Archived",
    ).order_by(Document.timestamp.asc()).all()


def run():
    app = create_app(TestConfig)

    # Ensure uploads dir exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    with app.app_context():
        # Fresh DB schema for tests
        try:
            db.drop_all()
        except Exception:
            pass
        db.create_all()

        # Create users
        print_header("Creating test users")
        alice = create_user("alice", "alice@example.com", is_admin=False)
        bob = create_user("bob", "bob@example.com", is_admin=False)
        charlie = create_user("charlie", "charlie@example.com", is_admin=False)  # used as alternate recipient

        print(f"Users created: alice={alice.id}, bob={bob.id}, charlie={charlie.id}")

        with app.test_client() as client:
            # Login as Alice (creator)
            print_header("Login as alice (creator)")
            r = client_login(client, "alice")
            print("Login response status:", r.status_code)

            # Create documents assigned to Bob
            print_header("Create documents for Bob (as alice)")
            titles = ["Doc-A1", "Doc-A2", "Doc-F1", "Doc-D1"]
            for t in titles:
                resp = create_document_via_post(client, t, alice, bob)
                print(f"Created {t}: HTTP {resp.status_code}")
            # Verify created
            all_docs = Document.query.all()
            print(f"Total documents in DB after creation: {len(all_docs)}")

            # Logout alice; login as bob (recipient)
            print_header("Switch to bob (recipient)")
            client_logout(client)
            r = client_login(client, "bob")
            print("Login as bob status:", r.status_code)

            docs_for_bob = get_docs_for(bob)
            print(f"Bob initially has {len(docs_for_bob)} docs (non-archived).",
                  [f"{d.id}:{d.title}({d.status})" for d in docs_for_bob])

            # Batch Accept: Accept first two docs for bob
            print_header("Batch Accept two documents (as bob)")
            to_accept = [d.id for d in docs_for_bob if d.title in ("Doc-A1", "Doc-A2")]
            resp = client.post(
                "/hrdoctrack/batch_accept_documents",
                data={"document_ids": [str(i) for i in to_accept]},
                follow_redirects=True,
            )
            print("Batch Accept response:", resp.status_code)
            # Verify status
            acc_docs = Document.query.filter(Document.id.in_(to_accept)).all()
            print("Accepted docs statuses:", [(d.title, d.status, d.accepted_timestamp is not None) for d in acc_docs])

            # Batch Decline: Decline D1
            print_header("Batch Decline one document (as bob)")
            to_decline = [d.id for d in docs_for_bob if d.title == "Doc-D1"]
            resp = client.post(
                "/hrdoctrack/batch_decline_documents",
                data={"document_ids": [str(i) for i in to_decline], "reason": "Not applicable"},
                follow_redirects=True,
            )
            print("Batch Decline response:", resp.status_code)
            dec_docs = Document.query.filter(Document.id.in_(to_decline)).all()
            print("Declined docs statuses:", [(d.title, d.status, d.remarks) for d in dec_docs])

            # Batch Forward: forward Doc-F1 (must be Accepted or Forwarded)
            print_header("Batch Forward one accepted doc to charlie (as bob)")
            # Accept Doc-F1 first if still pending
            f1 = Document.query.filter_by(title="Doc-F1").first()
            if f1 and f1.status not in ("Accepted", "Forwarded"):
                resp = client.post(
                    "/hrdoctrack/batch_accept_documents",
                    data={"document_ids": [str(f1.id)]},
                    follow_redirects=True,
                )
                print("Pre-accept Doc-F1 status code:", resp.status_code)
            # Forward F1 to charlie
            resp = client.post(
                "/hrdoctrack/batch_forward_documents",
                data={
                    "document_ids": [str(f1.id)],
                    "recipient": str(charlie.id),
                    "action_taken": "Endorsed",
                    "remarks": "Batch forward to charlie",
                },
                follow_redirects=True,
            )
            print("Batch Forward response:", resp.status_code)
            f1_refreshed = Document.query.get(f1.id)
            print("Doc-F1 after forward:", f1_refreshed.title, f1_refreshed.status, f1_refreshed.recipient_id == charlie.id)

            # Batch Release: release the accepted docs still with bob (Doc-A1, Doc-A2)
            print_header("Batch Release accepted docs (as bob)")
            rel_ids = [d.id for d in Document.query.filter(Document.title.in_(("Doc-A1", "Doc-A2"))).all()]
            resp = client.post(
                "/hrdoctrack/batch_release_documents",
                data={"document_ids": [str(i) for i in rel_ids]},
                follow_redirects=True,
            )
            print("Batch Release response:", resp.status_code)
            rel_docs = Document.query.filter(Document.id.in_(rel_ids)).all()
            print("Released docs:", [(d.title, d.status, d.released_timestamp is not None) for d in rel_docs])

            # Verify notifications and activity logs count (basic sanity)
            print_header("Validate ActivityLog & Notification")
            acts = ActivityLog.query.order_by(ActivityLog.timestamp.asc()).all()
            notifs = Notification.query.order_by(Notification.timestamp.asc()).all()
            print(f"ActivityLog count: {len(acts)}")
            for a in acts:
                print(f" - {a.id}: doc={a.document_id} action={a.action} by={getattr(a.user, 'username', 'NA')}")
            print(f"Notification count: {len(notifs)}")
            for n in notifs:
                print(f" - {n.id}: to_user={n.user_id} msg={n.message}")

            # Verify forward flow completion: login as charlie and release forwarded Doc-F1
            print_header("Release forwarded doc as new recipient (charlie)")
            client_logout(client)
            client_login(client, "charlie")
            resp = client.post(
                "/hrdoctrack/batch_release_documents",
                data={"document_ids": [str(f1.id)]},
                follow_redirects=True,
            )
            print("Release Doc-F1 by charlie resp:", resp.status_code)
            f1_done = Document.query.get(f1.id)
            print("Doc-F1 final status:", f1_done.title, f1_done.status, f1_done.released_timestamp is not None)

        print_header("TEST COMPLETED")
        # Summarize final document statuses
        docs = Document.query.order_by(Document.id.asc()).all()
        for d in docs:
            print(f"Doc {d.id} '{d.title}': status={d.status}, creator={d.creator.username if d.creator else None}, recipient={d.recipient.username if d.recipient else None}, acc_ts={d.accepted_timestamp}, fwd_ts={getattr(d, 'forwarded_timestamp', None)}, rel_ts={d.released_timestamp}")


if __name__ == "__main__":
    run()
