from typing import List

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class NotificationBroadcastRequest(BaseModel):
    """Request body for sending a bulk bot notification."""
    model_config = ConfigDict(extra="forbid")

    role_ids: List[int] = Field(default_factory=list)
    user_ids: List[int] = Field(default_factory=list)
    title: str = Field(min_length=1, max_length=160)
    message: str = Field(min_length=1, max_length=4000)
    attachment_urls: List[str] = Field(default_factory=list, max_length=15)
    image_urls: List[str] = Field(default_factory=list, max_length=10)

    @field_validator("title", "message", mode="before")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        return str(value or "").strip()

    @field_validator("attachment_urls", "image_urls", mode="before")
    @classmethod
    def _normalize_attachments(cls, value):
        if value is None:
            return []
        return value

    @model_validator(mode="after")
    def _validate_recipients(self):
        if not self.role_ids and not self.user_ids:
            raise ValueError("Нужно выбрать хотя бы одну роль или одного пользователя.")
        if not self.attachment_urls and self.image_urls:
            self.attachment_urls = list(self.image_urls)
        return self


class NotificationBroadcastResponse(BaseModel):
    """Response body for bulk notification delivery."""

    resolved_recipient_count: int
    sent_count: int
    failed_count: int
    failed_user_ids: List[int] = Field(default_factory=list)
