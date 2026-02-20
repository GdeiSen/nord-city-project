"""
Загрузка локализации из JSON. Единственный источник текстов — localisation_ru.json.
"""
import json
from pathlib import Path
from typing import Dict

_LOCALES_DIR = Path(__file__).resolve().parent
_JSON_PATH = _LOCALES_DIR / "localisation_ru.json"


def load_localisation() -> Dict[str, dict]:
    """
    Загружает данные локализации из localisation_ru.json.
    Raises FileNotFoundError или json.JSONDecodeError при ошибке.
    """
    if not _JSON_PATH.exists():
        raise FileNotFoundError(
            f"Файл локализации не найден: {_JSON_PATH}. "
            "Создайте localisation_ru.json в директории locales/."
        )
    with open(_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or "RU" not in data:
        raise ValueError(
            f"Неверный формат {_JSON_PATH}: ожидается объект с ключом 'RU'."
        )
    return data


# Экспорт для DictExtractor
Data: Dict[str, dict] = load_localisation()
