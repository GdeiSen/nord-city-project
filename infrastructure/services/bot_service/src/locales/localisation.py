"""
Загрузка локализации из JSON. Единственный источник текстов — localisation_ru.json.
"""
from copy import deepcopy
import json
from pathlib import Path
from threading import Lock
from typing import Any, Dict

_LOCALES_DIR = Path(__file__).resolve().parent
_JSON_PATH = _LOCALES_DIR / "localisation_ru.json"
_DATA_LOCK = Lock()


def _validate_base_shape(data: Dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise ValueError(
            f"Неверный формат {_JSON_PATH}: ожидается JSON-объект верхнего уровня."
        )
    if "RU" not in data:
        raise ValueError(
            f"Неверный формат {_JSON_PATH}: ожидается объект с ключом 'RU'."
        )
    if not isinstance(data["RU"], dict):
        raise ValueError(
            f"Неверный формат {_JSON_PATH}: ключ 'RU' должен содержать объект."
        )


def _validate_same_structure(reference: Any, candidate: Any, path: str = "root") -> None:
    if isinstance(reference, dict):
        if not isinstance(candidate, dict):
            raise ValueError(f"Значение по пути '{path}' должно быть объектом.")
        ref_keys = set(reference.keys())
        cand_keys = set(candidate.keys())
        missing = sorted(ref_keys - cand_keys)
        extra = sorted(cand_keys - ref_keys)
        if missing or extra:
            msg_parts: list[str] = []
            if missing:
                msg_parts.append(f"отсутствуют ключи: {', '.join(missing)}")
            if extra:
                msg_parts.append(f"лишние ключи: {', '.join(extra)}")
            raise ValueError(
                f"Несовпадающая структура локализации в '{path}': {'; '.join(msg_parts)}."
            )
        for key in reference:
            next_path = f"{path}.{key}" if path else key
            _validate_same_structure(reference[key], candidate[key], next_path)
        return

    if not isinstance(candidate, str):
        raise ValueError(f"Значение по пути '{path}' должно быть строкой.")


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
    _validate_base_shape(data)
    return data


def get_localisation() -> Dict[str, dict]:
    """Возвращает копию актуальной локализации в памяти."""
    with _DATA_LOCK:
        return deepcopy(Data)


def save_localisation(data: Dict[str, Any]) -> Dict[str, dict]:
    """
    Валидирует и сохраняет локализацию.
    Разрешено менять только значения, структура и имена ключей должны совпадать.
    """
    if not isinstance(data, dict):
        raise ValueError("Локализация должна быть объектом JSON.")
    _validate_base_shape(data)

    with _DATA_LOCK:
        _validate_same_structure(Data, data, "root")

        temp_path = _JSON_PATH.with_suffix(".json.tmp")
        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")
        temp_path.replace(_JSON_PATH)

        Data.clear()
        Data.update(deepcopy(data))
        return deepcopy(Data)


# Экспорт для DictExtractor
Data: Dict[str, dict] = load_localisation()
