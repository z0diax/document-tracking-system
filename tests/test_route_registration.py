import os
import shutil
import sys
import tempfile
import unittest


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('FLASK_ENV', 'development')

import app as app_package  # noqa: E402
from app import create_app  # noqa: E402


class RouteTestConfig:
    SECRET_KEY = 'test-secret'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = True
    WTF_CSRF_ENABLED = False
    UPLOAD_FOLDER = tempfile.mkdtemp(prefix='route-test-uploads-')
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
    TIMEZONE = 'Asia/Manila'
    HOST = '127.0.0.1'
    PORT = 5001


class RouteRegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._original_init_scheduler = app_package.init_scheduler
        app_package.init_scheduler = lambda flask_app: None
        cls.app = create_app(RouteTestConfig)

    @classmethod
    def tearDownClass(cls):
        app_package.init_scheduler = cls._original_init_scheduler
        shutil.rmtree(RouteTestConfig.UPLOAD_FOLDER, ignore_errors=True)

    def _assert_route(self, endpoint, rule, methods=None):
        matching_rules = [
            existing_rule
            for existing_rule in self.app.url_map.iter_rules()
            if existing_rule.endpoint == endpoint and existing_rule.rule == rule
        ]
        self.assertTrue(matching_rules, f'Missing route {endpoint} -> {rule}')
        if methods:
            self.assertTrue(
                set(methods).issubset(matching_rules[0].methods),
                f'Route {endpoint} missing methods {methods}; has {sorted(matching_rules[0].methods)}',
            )

    def test_escapejs_filter_is_registered(self):
        self.assertIn('escapejs', self.app.jinja_env.filters)

    def test_main_blueprint_has_expected_route_volume(self):
        main_routes = [
            rule for rule in self.app.url_map.iter_rules()
            if rule.endpoint.startswith('main.')
        ]
        self.assertGreaterEqual(len(main_routes), 75)

    def test_core_module_routes_are_registered(self):
        self._assert_route('main.home', '/hrdoctrack/')
        self._assert_route('main.home', '/hrdoctrack/home')
        self._assert_route('main.login', '/hrdoctrack/login', methods={'GET', 'POST'})
        self._assert_route('main.dashboard', '/hrdoctrack/dashboard')
        self._assert_route('main.create_document', '/hrdoctrack/create_document', methods={'POST'})
        self._assert_route('main.batch_release_documents', '/hrdoctrack/batch_release_documents', methods={'POST'})
        self._assert_route('main.create_leave_request', '/hrdoctrack/leave_request/create', methods={'POST'})
        self._assert_route('main.create_rsp', '/hrdoctrack/rsp/create', methods={'POST'})
        self._assert_route('main.archive', '/hrdoctrack/archive')
        self._assert_route('main.print_text_report', '/hrdoctrack/admin/print_text_report')

    def test_admin_module_routes_are_registered(self):
        self._assert_route('main.admin_dashboard', '/hrdoctrack/admin')
        self._assert_route('main.admin_archive_last_month_documents', '/hrdoctrack/admin/archive-last-month-documents', methods={'POST'})
        self._assert_route('main.admin_leave_analytics_drilldown', '/hrdoctrack/admin/leave-analytics/drilldown')
        self._assert_route('main.admin_missing_offices', '/hrdoctrack/admin/missing-offices')
        self._assert_route('main.admin_missing_office_details', '/hrdoctrack/admin/missing-offices/details')
        self._assert_route('main.admin_sla_alerts', '/hrdoctrack/admin/sla-alerts', methods={'GET', 'POST'})
        self._assert_route('main.toggle_user_status', '/hrdoctrack/admin/toggle_user_status/<int:user_id>', methods={'POST'})
        self._assert_route('main.user_metrics_details', '/hrdoctrack/admin/user_metrics/<int:user_id>')

    def test_supporting_module_routes_are_registered(self):
        self._assert_route('main.employee_list', '/hrdoctrack/employees')
        self._assert_route('main.check_bio_number', '/hrdoctrack/employees/check_bio_number', methods={'POST'})
        self._assert_route('main.search_recipients', '/hrdoctrack/api/users/search')
        self._assert_route('main.create_release_batch', '/hrdoctrack/release_batches', methods={'POST'})
        self._assert_route('main.set_system_theme', '/hrdoctrack/system-theme', methods={'POST'})
        self._assert_route('main.overview', '/hrdoctrack/overview')
        self._assert_route('main.docgen_mock', '/hrdoctrack/docgen')


if __name__ == '__main__':
    unittest.main()
