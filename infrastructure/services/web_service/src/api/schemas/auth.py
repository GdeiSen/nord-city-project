from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


# ---------------------------------------------------------------------------
# OTP Authentication Schemas
# ---------------------------------------------------------------------------

class RequestOtpBody(BaseModel):
    """Request body for initiating OTP code delivery via Telegram."""
    model_config = ConfigDict(extra="forbid")

    user_id: int


class RequestOtpResponse(BaseModel):
    """Response for OTP request."""
    success: bool
    message: str


class VerifyOtpBody(BaseModel):
    """Request body for verifying an OTP code."""
    model_config = ConfigDict(extra="forbid")

    user_id: int
    code: str


class VerifyOtpResponse(BaseModel):
    """Response for OTP verification -- includes JWT token on success."""
    success: bool
    message: str
    access_token: Optional[str] = None
    user: Optional[dict] = None


class TokenValidationResponse(BaseModel):
    """Response for token validation check."""
    valid: bool
    user_id: Optional[int] = None
    role: Optional[int] = None


# ---------------------------------------------------------------------------
# Legacy CRUD schemas (kept for backward compatibility)
# ---------------------------------------------------------------------------

class UserAuthResponse(BaseModel):
    """Response schema for UserAuth entity."""
    id: Optional[int] = None
    user_id: int
    password_hash: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CreateAuthRequest(BaseModel):
    """Request body for creating an auth record."""
    model_config = ConfigDict(extra="forbid")

    user_id: int
    password_hash: str


class UpdateAuthBody(BaseModel):
    """Request body for partial auth update."""
    model_config = ConfigDict(extra="forbid")

    password_hash: Optional[str] = None
