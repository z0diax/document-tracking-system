import os
import re
import shutil
import sys
import tempfile
import unittest
from datetime import date


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('FLASK_ENV', 'development')

import app as app_package  # noqa: E402
from app import create_app, db  # noqa: E402
from app.models import LeaveRequest, User  # noqa: E402


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
