import os
import re
import shutil
import sys
import tempfile
import unittest
from io import BytesIO
from datetime import date, datetime, timedelta

from werkzeug.datastructures import FileStorage


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('FLASK_ENV', 'development')

import app as app_package  # noqa: E402
from app import create_app, db  # noqa: E402
from app.models import ActivityLog, Document, LeaveRequest, ReleaseBatch, ReleaseBatchDocument, User  # noqa: E402
from app.route_modules.document_actions import _save_document_attachment  # noqa: E402


class AuthAccessTestConfig:
    SECRET_KEY = 'test-secret'
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(tempfile.mkdtemp(prefix='auth-access-db-'), 'test.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = True
    WTF_CSRF_ENABLED = False
    UPLOAD_FOLDER = tempfile.mkdtemp(prefix='auth-access-uploads-')
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
    TIMEZONE = 'Asia/Manila'
    HOST = '127.0.0.1'
    PORT = 5001


class AuthAccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._original_init_scheduler = app_package.init_scheduler
        app_package.init_scheduler = lambda flask_app: None
        cls.app = create_app(AuthAccessTestConfig)

    @classmethod
    def tearDownClass(cls):
        app_package.init_scheduler = cls._original_init_scheduler
        shutil.rmtree(AuthAccessTestConfig.UPLOAD_FOLDER, ignore_errors=True)
        db_path = AuthAccessTestConfig.SQLALCHEMY_DATABASE_URI.removeprefix('sqlite:///')
        shutil.rmtree(os.path.dirname(db_path), ignore_errors=True)

    def setUp(self):
        self.client = self.app.test_client()
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.create_all()

    def _create_user(self, username, email, password='password123', is_admin=False, status='Active'):
        with self.app.app_context():
            user = User(
                username=username,
                email=email,
                is_admin=is_admin,
                status=status,
            )
            user.password = password
            db.session.add(user)
            db.session.commit()
            return user.id

    def _update_user_status(self, user_id, status):
        with self.app.app_context():
            user = db.session.get(User, user_id)
            user.status = status
            db.session.commit()

    def _login(self, username, password='password123', follow_redirects=False):
        return self.client.post(
            '/hrdoctrack/login',
            data={
                'username': username,
                'password': password,
                'remember': 'y',
            },
            follow_redirects=follow_redirects,
        )

    def _logout(self):
        return self.client.get('/hrdoctrack/logout', follow_redirects=False)

    def _create_document(self, *, creator_id, recipient_id, title, timestamp, status='Pending'):
        with self.app.app_context():
            document = Document(
                title=title,
                office='HRMDO',
                classification='Communications',
                status=status,
                action_taken='Noted',
                remarks='Test document',
                timestamp=timestamp,
                creator_id=creator_id,
                recipient_id=recipient_id,
            )
            db.session.add(document)
            db.session.commit()
            return document.id

    def _create_release_batch(self, *, created_by_id, name, document_ids, release_at=None):
        with self.app.app_context():
            batch = ReleaseBatch(
                name=name,
                created_by_id=created_by_id,
                release_at=release_at or datetime.utcnow(),
            )
            db.session.add(batch)
            db.session.flush()
            for document_id in document_ids:
                db.session.add(ReleaseBatchDocument(
                    release_batch_id=batch.id,
                    document_id=document_id,
                ))
            db.session.commit()
            return batch.id

    def test_unauthenticated_admin_route_redirects_to_login(self):
        response = self.client.get('/hrdoctrack/admin', follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/hrdoctrack/login', response.location)

    def test_active_admin_login_redirects_to_admin_dashboard(self):
        self._create_user('admin', 'admin@example.com', is_admin=True, status='Active')

        response = self._login('admin')

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith('/hrdoctrack/admin'))

    def test_active_standard_user_login_redirects_to_overview(self):
        self._create_user('staff', 'staff@example.com', status='Active')

        response = self._login('staff')

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith('/hrdoctrack/overview'))

    def test_pending_user_cannot_log_in(self):
        self._create_user('pending_user', 'pending@example.com', status='Pending')

        response = self._login('pending_user', follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'pending for approval', response.data)

    def test_non_admin_user_is_redirected_away_from_admin_dashboard(self):
        self._create_user('staff', 'staff@example.com', status='Active')
        self._login('staff')

        response = self.client.get('/hrdoctrack/admin', follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith('/hrdoctrack/dashboard'))

    def test_admin_user_can_load_admin_dashboard(self):
        self._create_user('admin', 'admin@example.com', is_admin=True, status='Active')
        self._login('admin')

        response = self.client.get('/hrdoctrack/admin', follow_redirects=False)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Admin Dashboard', response.data)

    def test_admin_can_manually_archive_last_month_documents_from_admin_dashboard(self):
        admin_id = self._create_user('admin', 'admin@example.com', is_admin=True, status='Active')
        with self.app.app_context():
            now = datetime.utcnow()
            first_day_of_current_month = datetime(now.year, now.month, 1)
            previous_month_timestamp = first_day_of_current_month - timedelta(days=1)
            current_month_timestamp = first_day_of_current_month + timedelta(days=1)

        old_document_id = self._create_document(
            creator_id=admin_id,
            recipient_id=admin_id,
            title='Needs manual archive',
            timestamp=previous_month_timestamp,
        )
        current_document_id = self._create_document(
            creator_id=admin_id,
            recipient_id=admin_id,
            title='Should stay active',
            timestamp=current_month_timestamp,
        )

        self._login('admin')
        response = self.client.post('/hrdoctrack/admin/archive-last-month-documents', follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/hrdoctrack/admin', response.location)

        with self.app.app_context():
            old_document = db.session.get(Document, old_document_id)
            current_document = db.session.get(Document, current_document_id)
            auto_archive_logs = ActivityLog.query.filter_by(
                document_id=old_document_id,
                action='Auto Archived',
            ).count()

            self.assertEqual(old_document.status, 'Archived')
            self.assertEqual(current_document.status, 'Pending')
            self.assertEqual(auto_archive_logs, 1)

    def test_non_admin_cannot_trigger_manual_archive_from_admin_dashboard(self):
        staff_id = self._create_user('staff', 'staff@example.com', status='Active')
        with self.app.app_context():
            now = datetime.utcnow()
            first_day_of_current_month = datetime(now.year, now.month, 1)
            previous_month_timestamp = first_day_of_current_month - timedelta(days=1)

        document_id = self._create_document(
            creator_id=staff_id,
            recipient_id=staff_id,
            title='Should not be archived by non-admin',
            timestamp=previous_month_timestamp,
        )

        self._login('staff')
        response = self.client.post('/hrdoctrack/admin/archive-last-month-documents', follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith('/hrdoctrack/dashboard'))

        with self.app.app_context():
            document = db.session.get(Document, document_id)
            auto_archive_logs = ActivityLog.query.filter_by(
                document_id=document_id,
                action='Auto Archived',
            ).count()

            self.assertEqual(document.status, 'Pending')
            self.assertEqual(auto_archive_logs, 0)

    def test_attachment_storage_uses_unique_names_for_same_filename(self):
        with self.app.app_context():
            first_name = _save_document_attachment(FileStorage(
                stream=BytesIO(b'first file'),
                filename='shared.pdf',
                content_type='application/pdf',
            ))
            second_name = _save_document_attachment(FileStorage(
                stream=BytesIO(b'second file'),
                filename='shared.pdf',
                content_type='application/pdf',
            ))

        self.assertNotEqual(first_name, second_name)

        first_path = os.path.join(AuthAccessTestConfig.UPLOAD_FOLDER, first_name)
        second_path = os.path.join(AuthAccessTestConfig.UPLOAD_FOLDER, second_name)
        self.assertTrue(os.path.exists(first_path))
        self.assertTrue(os.path.exists(second_path))

        with open(first_path, 'rb') as handle:
            self.assertEqual(handle.read(), b'first file')
        with open(second_path, 'rb') as handle:
            self.assertEqual(handle.read(), b'second file')

    def test_document_attachment_download_requires_document_access(self):
        owner_id = self._create_user('owner', 'owner@example.com', status='Active')
        other_id = self._create_user('other', 'other@example.com', status='Active')
        document_id = self._create_document(
            creator_id=owner_id,
            recipient_id=owner_id,
            title='Secret Attachment',
            timestamp=datetime.utcnow(),
        )

        attachment_name = 'secret.pdf'
        with self.app.app_context():
            document = db.session.get(Document, document_id)
            document.attachment = attachment_name
            db.session.commit()

        attachment_path = os.path.join(AuthAccessTestConfig.UPLOAD_FOLDER, attachment_name)
        with open(attachment_path, 'wb') as handle:
            handle.write(b'secret bytes')

        self._login('other')
        denied_response = self.client.get(f'/hrdoctrack/documents/{document_id}/attachment', follow_redirects=False)
        legacy_response = self.client.get(f'/hrdoctrack/uploads/{attachment_name}', follow_redirects=False)
        self.assertEqual(denied_response.status_code, 403)
        self.assertEqual(legacy_response.status_code, 404)

        self._logout()
        self._login('owner')
        allowed_response = self.client.get(f'/hrdoctrack/documents/{document_id}/attachment', follow_redirects=False)
        self.assertEqual(allowed_response.status_code, 200)
        self.assertEqual(allowed_response.data, b'secret bytes')

    def test_document_search_only_returns_user_accessible_documents(self):
        owner_id = self._create_user('creator', 'creator@example.com', status='Active')
        viewer_id = self._create_user('viewer', 'viewer@example.com', status='Active')
        outsider_id = self._create_user('outsider', 'outsider@example.com', status='Active')

        self._create_document(
            creator_id=owner_id,
            recipient_id=viewer_id,
            title='Secret Payroll',
            timestamp=datetime.utcnow(),
        )

        self._login('viewer')
        visible_response = self.client.get('/hrdoctrack/api/documents/search?q=Secret', follow_redirects=False)
        self.assertEqual(visible_response.status_code, 200)
        self.assertEqual(len(visible_response.get_json()['results']), 1)

        self._logout()
        self._login('outsider')
        hidden_response = self.client.get('/hrdoctrack/api/documents/search?q=Secret', follow_redirects=False)
        self.assertEqual(hidden_response.status_code, 200)
        self.assertEqual(hidden_response.get_json()['results'], [])

    def test_check_barcode_no_longer_exposes_document_metadata(self):
        owner_id = self._create_user('barcode_owner', 'barcode_owner@example.com', status='Active')
        viewer_id = self._create_user('barcode_viewer', 'barcode_viewer@example.com', status='Active')
        document_id = self._create_document(
            creator_id=owner_id,
            recipient_id=owner_id,
            title='Hidden Barcode Doc',
            timestamp=datetime.utcnow(),
        )

        with self.app.app_context():
            document = db.session.get(Document, document_id)
            document.barcode = 'ABC123'
            db.session.commit()

        self._login('barcode_viewer')
        response = self.client.post('/hrdoctrack/check_barcode', data={'barcode': 'ABC123'}, follow_redirects=False)
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertFalse(payload['valid'])
        self.assertNotIn('document', payload)

    def test_release_batch_list_only_shows_visible_documents_and_blocks_edits_for_non_manager(self):
        manager_id = self._create_user('manager', 'manager@example.com', status='Active')
        viewer_id = self._create_user('batch_viewer', 'batch_viewer@example.com', status='Active')
        other_id = self._create_user('batch_other', 'batch_other@example.com', status='Active')

        visible_doc_id = self._create_document(
            creator_id=manager_id,
            recipient_id=viewer_id,
            title='Visible in Batch',
            timestamp=datetime.utcnow(),
            status='Released',
        )
        hidden_doc_id = self._create_document(
            creator_id=manager_id,
            recipient_id=other_id,
            title='Hidden in Batch',
            timestamp=datetime.utcnow(),
            status='Released',
        )
        batch_id = self._create_release_batch(
            created_by_id=manager_id,
            name='Shared Batch',
            document_ids=[visible_doc_id, hidden_doc_id],
        )

        self._login('batch_viewer')
        list_response = self.client.get('/hrdoctrack/api/release_batches', follow_redirects=False)
        self.assertEqual(list_response.status_code, 200)
        payload = list_response.get_json()['results']
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]['id'], batch_id)
        self.assertFalse(payload[0]['can_edit'])
        self.assertEqual(len(payload[0]['documents']), 1)
        self.assertEqual(payload[0]['documents'][0]['id'], visible_doc_id)

        delete_response = self.client.post(f'/hrdoctrack/release_batches/{batch_id}/delete', follow_redirects=False)
        remove_response = self.client.post(
            f'/hrdoctrack/release_batches/{batch_id}/documents/remove',
            data={'document_id': visible_doc_id},
            follow_redirects=False,
        )
        self.assertEqual(delete_response.status_code, 403)
        self.assertEqual(remove_response.status_code, 403)

    def test_release_batch_list_hides_unrelated_batches(self):
        manager_id = self._create_user('batch_owner', 'batch_owner@example.com', status='Active')
        outsider_id = self._create_user('batch_outsider', 'batch_outsider@example.com', status='Active')
        document_id = self._create_document(
            creator_id=manager_id,
            recipient_id=manager_id,
            title='Private Batch Doc',
            timestamp=datetime.utcnow(),
            status='Released',
        )
        self._create_release_batch(
            created_by_id=manager_id,
            name='Private Batch',
            document_ids=[document_id],
        )

        self._login('batch_outsider')
        response = self.client.get('/hrdoctrack/api/release_batches', follow_redirects=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['results'], [])

    def test_account_status_endpoint_does_not_reveal_user_state(self):
        self._create_user('pending_user', 'pending_user@example.com', status='Pending')

        existing = self.client.post('/hrdoctrack/check_account_status', data={'username': 'pending_user'}, follow_redirects=False)
        missing = self.client.post('/hrdoctrack/check_account_status', data={'username': 'missing_user'}, follow_redirects=False)

        self.assertEqual(existing.status_code, 200)
        self.assertEqual(missing.status_code, 200)
        self.assertEqual(existing.get_json(), missing.get_json())
        self.assertNotIn('status', existing.get_json())

    def test_admin_dashboard_shows_employee_leave_type_analytics(self):
        admin_id = self._create_user('admin', 'admin@example.com', is_admin=True, status='Active')
        with self.app.app_context():
            db.session.add_all([
                LeaveRequest(
                    employee_name='Alice Reyes',
                    office='HRMDO',
                    leave_type='Vacation Leave',
                    start_date=date(2026, 3, 1),
                    end_date=date(2026, 3, 2),
                    status='Released',
                    created_by_user_id=admin_id,
                ),
                LeaveRequest(
                    employee_name='Alice Reyes',
                    office='HRMDO',
                    leave_type='Vacation Leave',
                    start_date=date(2026, 3, 10),
                    end_date=date(2026, 3, 11),
                    status='Released',
                    created_by_user_id=admin_id,
                ),
                LeaveRequest(
                    employee_name='Ben Cruz',
                    office='CMO',
                    leave_type='Vacation Leave',
                    start_date=date(2026, 3, 5),
                    end_date=date(2026, 3, 6),
                    status='Pending',
                    created_by_user_id=admin_id,
                ),
            ])
            db.session.commit()

        self._login('admin')

        response = self.client.get('/hrdoctrack/admin', follow_redirects=False)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Employees by Leave Type', response.data)
        self.assertIn(b'Vacation Leave', response.data)
        self.assertIn(b'Alice Reyes', response.data)
        self.assertIn(b'Ben Cruz', response.data)
        self.assertIn(b'Date Range', response.data)
        self.assertIn(b'value="year"', response.data)
        self.assertIn(b'leaveTypeEmployeeYearSelect', response.data)
        self.assertIn(b'leaveAnalyticsByRange', response.data)

    def test_admin_dashboard_leave_type_employee_analytics_paginate_first_ten_rows(self):
        admin_id = self._create_user('admin', 'admin@example.com', is_admin=True, status='Active')
        with self.app.app_context():
            for index in range(1, 13):
                db.session.add(
                    LeaveRequest(
                        employee_name=f'Employee {index:02d}',
                        office='HRMDO',
                        leave_type='Vacation Leave',
                        start_date=date(2026, 3, index),
                        end_date=date(2026, 3, index),
                        status='Released',
                        created_by_user_id=admin_id,
                    )
                )
            db.session.commit()

        self._login('admin')

        response = self.client.get('/hrdoctrack/admin', follow_redirects=False)

        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        match = re.search(
            r'<tbody id="leaveTypeEmployeesTableBody">(.*?)</tbody>',
            html,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        tbody_html = match.group(1)

        self.assertIn('Employee 01', tbody_html)
        self.assertIn('Employee 10', tbody_html)
        self.assertNotIn('Employee 11', tbody_html)
        self.assertNotIn('Employee 12', tbody_html)
        self.assertIn('Page 1 of 2', html)

    def test_admin_leave_analytics_drilldown_endpoint_returns_matching_records(self):
        admin_id = self._create_user('admin', 'admin@example.com', is_admin=True, status='Active')
        with self.app.app_context():
            db.session.add_all([
                LeaveRequest(
                    employee_name='Alice Reyes',
                    office='HRMDO',
                    leave_type='Vacation Leave',
                    start_date=date(2026, 3, 1),
                    end_date=date(2026, 3, 2),
                    status='Released',
                    created_by_user_id=admin_id,
                ),
                LeaveRequest(
                    employee_name='Ben Cruz',
                    office='CMO',
                    leave_type='Sick Leave',
                    start_date=date(2026, 3, 3),
                    end_date=date(2026, 3, 4),
                    status='Pending',
                    created_by_user_id=admin_id,
                ),
            ])
            db.session.commit()

        self._login('admin')

        response = self.client.get(
            '/hrdoctrack/admin/leave-analytics/drilldown?metric=status&value=Released',
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload['success'])
        self.assertEqual(payload['total'], 1)
        self.assertEqual(payload['records'][0]['employee_name'], 'Alice Reyes')
        self.assertEqual(payload['records'][0]['status'], 'Released')
        self.assertEqual(payload['range_label'], 'All Time')

    def test_disabled_user_is_logged_out_on_next_request(self):
        user_id = self._create_user('revoked', 'revoked@example.com', status='Active')
        self._login('revoked')
        self._update_user_status(user_id, 'Disabled')

        response = self.client.get('/hrdoctrack/overview', follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith('/hrdoctrack/login'))


if __name__ == '__main__':
    unittest.main()
