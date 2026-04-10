from copy import deepcopy
import json
from pathlib import Path
from threading import Lock
from typing import Any

from bot_features import BOT_FEATURES_BY_KEY, DEFAULT_BOT_SETTINGS

_SETTINGS_DIR = Path(__file__).resolve().parent
_JSON_PATH = _SETTINGS_DIR / "bot_settings.json"
_DATA_LOCK = Lock()


def _default_settings_copy() -> dict[str, Any]:
    return deepcopy(DEFAULT_BOT_SETTINGS)


def _normalize_settings(data: Any) -> dict[str, Any]:
    if data is None:
        return _default_settings_copy()
    if not isinstance(data, dict):
        raise ValueError("Настройки бота должны быть JSON-объектом.")

    raw_features = data.get("features")
    if raw_features is None:
        raw_features = {}
    if not isinstance(raw_features, dict):
        raise ValueError("Поле 'features' должно быть объектом.")

    normalized = _default_settings_copy()
    for feature_key in BOT_FEATURES_BY_KEY:
        raw_feature = raw_features.get(feature_key)
        if raw_feature is None:
            continue
        if not isinstance(raw_feature, dict):
            raise ValueError(f"Настройка фичи '{feature_key}' должна быть объектом.")

        enabled = raw_feature.get("enabled")
        if enabled is None:
            continue
        if not isinstance(enabled, bool):
            raise ValueError(
                f"Поле 'features.{feature_key}.enabled' должно быть булевым значением."
            )
        normalized["features"][feature_key]["enabled"] = enabled

    return normalized


def _write_settings(data: dict[str, Any]) -> None:
    _SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = _JSON_PATH.with_suffix(".json.tmp")
    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")
    temp_path.replace(_JSON_PATH)


def load_bot_settings() -> dict[str, Any]:
    if not _JSON_PATH.exists():
        data = _default_settings_copy()
        _write_settings(data)
        return data

    with open(_JSON_PATH, "r", encoding="utf-8") as file:
        data = json.load(file)

    normalized = _normalize_settings(data)
    if normalized != data:
        _write_settings(normalized)
    return normalized


def get_bot_settings() -> dict[str, Any]:
    with _DATA_LOCK:
        return deepcopy(Data)


def save_bot_settings(data: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_settings(data)
    with _DATA_LOCK:
        _write_settings(normalized)
        Data.clear()
        Data.update(deepcopy(normalized))
        return deepcopy(Data)


Data: dict[str, Any] = load_bot_settings()
