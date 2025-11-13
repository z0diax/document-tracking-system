import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

DEFAULT_THEME = "classic"
ALLOWED_THEMES = {"classic", "winter", "hallochristmas"}
THEME_SEQUENCE = ["classic", "winter", "hallochristmas"]
STATE_FILENAME = "season_theme.json"


def _state_path(app) -> str:
    instance_path = getattr(app, "instance_path", None) or "."
    return os.path.join(instance_path, STATE_FILENAME)


def read_theme_state(app) -> Dict[str, Any]:
    """Return the stored season theme state, falling back to defaults."""
    path = _state_path(app)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
            if isinstance(data, dict):
                theme = data.get("theme")
                if theme not in ALLOWED_THEMES:
                    data["theme"] = DEFAULT_THEME
                return data
    except FileNotFoundError:
        pass
    except Exception as exc:  # pragma: no cover - defensive logging
        logger = getattr(app, "logger", None)
        if logger:
            logger.warning("Failed to read season theme state: %s", exc)
    return {"theme": DEFAULT_THEME}


def write_theme_state(app, theme: str, user: Optional[Any] = None) -> Dict[str, Any]:
    """Persist the global season theme selection to disk."""
    if theme not in ALLOWED_THEMES:
        raise ValueError(f"Unsupported theme '{theme}'")

    state = {
        "theme": theme,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if user is not None:
        state["updated_by"] = getattr(user, "username", None)
        state["updated_by_id"] = getattr(user, "id", None)

    path = _state_path(app)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)
    os.replace(tmp_path, path)
    return state
