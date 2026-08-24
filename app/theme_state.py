import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import requests

DEFAULT_THEME = "classic"
WEATHER_AUTO_THEME = "weather_auto"
MANUAL_THEMES = [
    "classic",
    "valentines",
    "womensmonth",
    "amihan",
    "winter",
    "hallochristmas",
    "chinesenewyear",
    "gov",
    "festive",
    "rainy",
]
ALLOWED_THEMES = set(MANUAL_THEMES + [WEATHER_AUTO_THEME])
THEME_SEQUENCE = MANUAL_THEMES + [WEATHER_AUTO_THEME]
STATE_FILENAME = "season_theme.json"
WEATHER_REFRESH_INTERVAL = timedelta(minutes=30)
WEATHER_EFFECTIVE_THEMES = {"sunny", "cloudy", "windy", "rainy", "thunderstorm", "winter"}

GEOCODING_ENDPOINT = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_ENDPOINT = "https://api.open-meteo.com/v1/forecast"


def _state_path(app) -> str:
    instance_path = getattr(app, "instance_path", None) or "."
    return os.path.join(instance_path, STATE_FILENAME)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _normalize_effective_theme(theme: Optional[str]) -> str:
    if theme and theme in WEATHER_EFFECTIVE_THEMES.union(MANUAL_THEMES):
        return theme
    return DEFAULT_THEME


def _friendly_location_name(result: Dict[str, Any]) -> str:
    parts = [result.get("name"), result.get("admin1"), result.get("country")]
    return ", ".join(part for part in parts if part)


def _weather_label_from_code(code: int) -> str:
    if code == 0:
        return "Clear"
    if code in (1, 2):
        return "Partly cloudy"
    if code == 3:
        return "Overcast"
    if code in (45, 48):
        return "Fog"
    if code in (51, 53, 55, 56, 57):
        return "Drizzle"
    if code in (61, 63, 65, 66, 67):
        return "Rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "Snow"
    if code in (80, 81, 82):
        return "Rain showers"
    if code in (95, 96, 99):
        return "Thunderstorm"
    return "Current weather"


def _classify_weather_theme(current: Dict[str, Any]) -> Dict[str, Any]:
    weather_code = int(current.get("weather_code") or 0)
    cloud_cover = float(current.get("cloud_cover") or 0)
    wind_speed = float(current.get("wind_speed_10m") or 0)
    wind_gusts = float(current.get("wind_gusts_10m") or 0)
    strongest_wind = max(wind_speed, wind_gusts)

    if weather_code in {95, 96, 99}:
        effective_theme = "thunderstorm"
    elif weather_code in {71, 73, 75, 77, 85, 86}:
        effective_theme = "winter"
    elif weather_code in {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}:
        effective_theme = "rainy"
    elif strongest_wind >= 35:
        effective_theme = "windy"
    elif weather_code in {1, 2, 3, 45, 48} or cloud_cover >= 60:
        effective_theme = "cloudy"
    else:
        effective_theme = "sunny"

    weather_label = _weather_label_from_code(weather_code)
    if effective_theme == "windy" and weather_label in {"Clear", "Partly cloudy", "Overcast"}:
        weather_label = "Windy"

    return {
        "effective_theme": effective_theme,
        "weather_code": weather_code,
        "weather_label": weather_label,
        "weather_updated_at": _now_iso(),
        "cloud_cover": cloud_cover,
        "wind_speed_10m": wind_speed,
        "wind_gusts_10m": wind_gusts,
        "is_day": int(current.get("is_day") or 0),
    }


def _persist_state(app, state: Dict[str, Any]) -> Dict[str, Any]:
    path = _state_path(app)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)
    os.replace(tmp_path, path)
    return state


def _normalize_state(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    state = dict(data or {})
    theme = state.get("theme")
    if theme not in ALLOWED_THEMES:
        theme = DEFAULT_THEME
    state["theme"] = theme

    if theme == WEATHER_AUTO_THEME:
        state["effective_theme"] = _normalize_effective_theme(state.get("effective_theme"))
    else:
        state["effective_theme"] = theme

    return state


def _geocode_location(location_query: str) -> Dict[str, Any]:
    response = requests.get(
        GEOCODING_ENDPOINT,
        params={
            "name": location_query,
            "count": 1,
            "language": "en",
            "format": "json",
        },
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    results = payload.get("results") or []
    if not results:
        raise ValueError("Location not found. Enter a city or municipality.")
    result = results[0]
    return {
        "location_query": location_query,
        "location_name": _friendly_location_name(result),
        "latitude": result.get("latitude"),
        "longitude": result.get("longitude"),
        "timezone": result.get("timezone"),
    }


def _fetch_weather_snapshot(latitude: float, longitude: float) -> Dict[str, Any]:
    response = requests.get(
        FORECAST_ENDPOINT,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "weather_code,cloud_cover,wind_speed_10m,wind_gusts_10m,is_day",
            "timezone": "auto",
            "forecast_days": 1,
        },
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    current = payload.get("current")
    if not isinstance(current, dict):
        raise ValueError("Weather data is unavailable for the selected location.")
    return current


def _weather_refresh_due(state: Dict[str, Any]) -> bool:
    last_updated = _parse_datetime(state.get("weather_updated_at"))
    if not last_updated:
        return True
    return datetime.now(timezone.utc) - last_updated >= WEATHER_REFRESH_INTERVAL


def read_theme_state(app) -> Dict[str, Any]:
    """Return the stored theme state, falling back to defaults."""
    path = _state_path(app)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
            if isinstance(data, dict):
                return _normalize_state(data)
    except FileNotFoundError:
        pass
    except Exception as exc:  # pragma: no cover - defensive logging
        logger = getattr(app, "logger", None)
        if logger:
            logger.warning("Failed to read season theme state: %s", exc)
    return {"theme": DEFAULT_THEME, "effective_theme": DEFAULT_THEME}


def write_theme_state(
    app,
    theme: str,
    user: Optional[Any] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Persist the global theme selection to disk."""
    if theme not in ALLOWED_THEMES:
        raise ValueError(f"Unsupported theme '{theme}'")

    state: Dict[str, Any] = {
        "theme": theme,
        "effective_theme": theme if theme != WEATHER_AUTO_THEME else DEFAULT_THEME,
        "updated_at": _now_iso(),
    }
    if metadata:
        state.update(metadata)
    if user is not None:
        state["updated_by"] = getattr(user, "username", None)
        state["updated_by_id"] = getattr(user, "id", None)

    return _persist_state(app, _normalize_state(state))


def enable_weather_theme(app, location_query: str, user: Optional[Any] = None) -> Dict[str, Any]:
    """Persist weather-sync mode using the selected location."""
    query = (location_query or "").strip()
    if len(query) < 2:
        raise ValueError("Enter a city or municipality for Weather Sync.")

    location = _geocode_location(query)
    current = _fetch_weather_snapshot(location["latitude"], location["longitude"])
    weather_state = _classify_weather_theme(current)

    metadata = {
        "location_query": query,
        "location_name": location["location_name"],
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "timezone": location.get("timezone"),
    }
    metadata.update(weather_state)
    return write_theme_state(app, WEATHER_AUTO_THEME, user=user, metadata=metadata)


def refresh_weather_theme_state(app, force: bool = False) -> Dict[str, Any]:
    """Refresh the weather-driven effective theme when weather sync is active."""
    state = read_theme_state(app)
    if state.get("theme") != WEATHER_AUTO_THEME:
        return state

    if not force and not _weather_refresh_due(state):
        return state

    latitude = state.get("latitude")
    longitude = state.get("longitude")
    if latitude is None or longitude is None:
        location_query = (state.get("location_query") or state.get("location_name") or "").strip()
        if not location_query:
            return state
        location = _geocode_location(location_query)
        state.update(location)
        latitude = location.get("latitude")
        longitude = location.get("longitude")

    current = _fetch_weather_snapshot(float(latitude), float(longitude))
    state.update(_classify_weather_theme(current))
    return _persist_state(app, _normalize_state(state))


def resolve_theme_state(app, force_refresh: bool = False) -> Dict[str, Any]:
    """Return a state object with a concrete effective theme ready for templates."""
    state = read_theme_state(app)
    if state.get("theme") != WEATHER_AUTO_THEME:
        return state

    if force_refresh or _weather_refresh_due(state):
        try:
            return refresh_weather_theme_state(app, force=True)
        except Exception as exc:  # pragma: no cover - network resilience
            logger = getattr(app, "logger", None)
            if logger:
                logger.warning("Failed to refresh weather theme state: %s", exc)
    return state
