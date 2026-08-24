import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('FLASK_ENV', 'development')

import app as app_package  # noqa: E402
from app import create_app  # noqa: E402
from app import theme_state  # noqa: E402


class ThemeStateTestConfig:
    SECRET_KEY = 'test-secret'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = True
    WTF_CSRF_ENABLED = False
    UPLOAD_FOLDER = tempfile.mkdtemp(prefix='theme-state-uploads-')
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
    TIMEZONE = 'Asia/Manila'
    HOST = '127.0.0.1'
    PORT = 5001


class ThemeStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._original_init_scheduler = app_package.init_scheduler
        app_package.init_scheduler = lambda flask_app: None
        cls.app = create_app(ThemeStateTestConfig)
        cls.instance_path = tempfile.mkdtemp(prefix='theme-state-instance-')
        cls.app.instance_path = cls.instance_path

    @classmethod
    def tearDownClass(cls):
        app_package.init_scheduler = cls._original_init_scheduler
        shutil.rmtree(ThemeStateTestConfig.UPLOAD_FOLDER, ignore_errors=True)
        shutil.rmtree(cls.instance_path, ignore_errors=True)

    def setUp(self):
        state_file = os.path.join(self.instance_path, theme_state.STATE_FILENAME)
        if os.path.exists(state_file):
            os.remove(state_file)

    def test_manual_theme_resolves_to_itself(self):
        state = theme_state.write_theme_state(self.app, 'rainy')

        self.assertEqual(state['theme'], 'rainy')
        self.assertEqual(state['effective_theme'], 'rainy')

        resolved = theme_state.resolve_theme_state(self.app)
        self.assertEqual(resolved['theme'], 'rainy')
        self.assertEqual(resolved['effective_theme'], 'rainy')

    @patch('app.theme_state._fetch_weather_snapshot')
    @patch('app.theme_state._geocode_location')
    def test_enable_weather_theme_persists_location_and_effective_theme(self, mock_geocode, mock_weather):
        mock_geocode.return_value = {
            'location_query': 'Tacloban City',
            'location_name': 'Tacloban City, Eastern Visayas, Philippines',
            'latitude': 11.2449,
            'longitude': 125.0,
            'timezone': 'Asia/Manila',
        }
        mock_weather.return_value = {
            'weather_code': 61,
            'cloud_cover': 88,
            'wind_speed_10m': 18,
            'wind_gusts_10m': 24,
            'is_day': 1,
        }

        state = theme_state.enable_weather_theme(self.app, 'Tacloban City')

        self.assertEqual(state['theme'], theme_state.WEATHER_AUTO_THEME)
        self.assertEqual(state['effective_theme'], 'rainy')
        self.assertEqual(state['location_name'], 'Tacloban City, Eastern Visayas, Philippines')
        self.assertEqual(state['weather_label'], 'Rain')

    @patch('app.theme_state._fetch_weather_snapshot')
    def test_stale_weather_theme_refreshes_and_persists(self, mock_weather):
        old_timestamp = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        theme_state.write_theme_state(
            self.app,
            theme_state.WEATHER_AUTO_THEME,
            metadata={
                'location_query': 'Tacloban City',
                'location_name': 'Tacloban City, Eastern Visayas, Philippines',
                'latitude': 11.2449,
                'longitude': 125.0,
                'effective_theme': 'rainy',
                'weather_label': 'Rain',
                'weather_updated_at': old_timestamp,
            },
        )
        mock_weather.return_value = {
            'weather_code': 95,
            'cloud_cover': 100,
            'wind_speed_10m': 22,
            'wind_gusts_10m': 31,
            'is_day': 0,
        }

        resolved = theme_state.resolve_theme_state(self.app)

        self.assertEqual(resolved['theme'], theme_state.WEATHER_AUTO_THEME)
        self.assertEqual(resolved['effective_theme'], 'thunderstorm')
        self.assertEqual(resolved['weather_label'], 'Thunderstorm')

        persisted = theme_state.read_theme_state(self.app)
        self.assertEqual(persisted['effective_theme'], 'thunderstorm')


if __name__ == '__main__':
    unittest.main()
