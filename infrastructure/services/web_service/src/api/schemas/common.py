from pydantic import BaseModel


class MessageResponse(BaseModel):
    """Standard response for update operations."""
    message: str
    id: int
