from typing import Generic, TypeVar, List, Optional

from pydantic import BaseModel

T = TypeVar("T")


def parse_sort_param(sort_str: Optional[str]) -> List[dict]:
    """Parse sort=col:asc,col2:desc into [{columnId, direction}, ...]."""
    if not sort_str:
        return []
    out = []
    for part in sort_str.split(","):
        part = part.strip()
        if ":" in part:
            col, dirn = part.split(":", 1)
            out.append({"columnId": col.strip(), "direction": dirn.strip().lower() or "asc"})
        elif part:
            out.append({"columnId": part, "direction": "asc"})
    return out


class MessageResponse(BaseModel):
    """Standard response for update operations."""
    message: str
    id: int


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response."""
    items: List[T]
    total: int
