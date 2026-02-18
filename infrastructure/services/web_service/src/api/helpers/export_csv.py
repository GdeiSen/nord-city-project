"""
CSV export helper. Builds CSV from items using column config.
"""
import csv
import io
from typing import Any, Callable, Dict, List, Optional


def _escape_csv_value(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    if "\n" in s or "\r" in s or '"' in s or "," in s:
        return '"' + s.replace('"', '""') + '"'
    return s


def build_csv(
    items: List[Dict[str, Any]],
    columns: List[str],
    value_getters: Dict[str, Callable[[Dict], str]],
    headers: Optional[Dict[str, str]] = None,
) -> str:
    """
    Build CSV string from items.
    columns: list of column ids in order
    value_getters: {column_id: fn(item) -> str}
    headers: {column_id: header_label} - if None, use column_id as header
    """
    out = io.StringIO(newline="")
    writer = csv.writer(out, quoting=csv.QUOTE_MINIMAL)
    header_row = [headers.get(c, c) if headers else c for c in columns]
    writer.writerow(header_row)
    for item in items:
        row = []
        for col in columns:
            getter = value_getters.get(col)
            if getter:
                row.append(_escape_csv_value(getter(item)))
            else:
                row.append(_escape_csv_value(item.get(col, "")))
        writer.writerow(row)
    return out.getvalue()
