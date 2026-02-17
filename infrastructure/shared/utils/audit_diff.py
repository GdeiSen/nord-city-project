"""
Audit diff utilities: smart mode computes only changed fields (tree of changes).
"""

from typing import Any, Dict


def _json_safe_value(v: Any) -> Any:
    """Ensure value is JSON-serializable."""
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, (list, tuple)):
        return [_json_safe_value(x) for x in v]
    if isinstance(v, dict):
        return {k: _json_safe_value(val) for k, val in v.items()}
    if hasattr(v, "isoformat"):  # datetime
        return v.isoformat()
    return str(v)


def compute_smart_diff(old_data: dict, new_data: dict) -> Dict[str, Any] | None:
    """
    Recursively compare old_data and new_data, return only changed paths.
    Result: {"path.to.field": {"old": v1, "new": v2}, ...}
    Works through the change tree - nested objects are compared recursively.
    """
    diff: Dict[str, Any] = {}

    def _compare(path: str, old_val: Any, new_val: Any) -> None:
        if old_val == new_val:
            return
        # Both are dicts - recurse
        if isinstance(old_val, dict) and isinstance(new_val, dict):
            all_keys = set(old_val.keys()) | set(new_val.keys())
            for k in all_keys:
                p = f"{path}.{k}" if path else k
                _compare(p, old_val.get(k), new_val.get(k))
            return
        # Both are lists - treat as value (or could do element-wise, but complex)
        if isinstance(old_val, (list, tuple)) and isinstance(new_val, (list, tuple)):
            if old_val != new_val:
                diff[path or "__root__"] = {
                    "old": _json_safe_value(old_val),
                    "new": _json_safe_value(new_val),
                }
            return
        # Leaf: record change
        diff[path or "__root__"] = {
            "old": _json_safe_value(old_val),
            "new": _json_safe_value(new_val),
        }

    _compare("", old_data or {}, new_data or {})
    return diff if diff else None
