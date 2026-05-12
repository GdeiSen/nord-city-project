import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from shared.utils.ddid_utils import create_ddid

_CONFIG_PATH = Path(__file__).resolve().parents[1] / "assets" / "service_ticket_category_bindings.json"


@lru_cache(maxsize=1)
def _load_config() -> dict[str, Any]:
    try:
        with _CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _format_category(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, list):
        parts = [str(part).strip() for part in value if str(part).strip()]
        return " | ".join(parts) if parts else None
    return None


def resolve_service_ticket_category(raw_trace: Optional[list[Any]]) -> Optional[str]:
    """Resolve service ticket category from dynamic dialog trace.

    Supports option-level bindings and DDID-level bindings. Option bindings win because
    they identify the exact selected branch in shared terminal sequences.
    """
    config = _load_config()
    option_categories = config.get("option_categories") if isinstance(config.get("option_categories"), dict) else {}
    ddid_categories = config.get("ddid_categories") if isinstance(config.get("ddid_categories"), dict) else {}

    resolved: Optional[str] = None
    for raw_item in raw_trace or []:
        parts = str(raw_item).split(":")
        if len(parts) < 4:
            continue
        try:
            dialog_id = int(parts[1])
            sequence_id = int(parts[2])
            item_id = int(parts[3])
            option_id = int(parts[4]) if len(parts) >= 5 and str(parts[4]).isdigit() else None
        except (TypeError, ValueError):
            continue

        if option_id is not None:
            option_category = _format_category(option_categories.get(str(option_id)))
            if option_category:
                resolved = option_category
                continue

        try:
            ddid = create_ddid(dialog_id, sequence_id, item_id)
        except ValueError:
            continue
        ddid_category = _format_category(ddid_categories.get(ddid))
        if ddid_category:
            resolved = ddid_category

    return resolved
