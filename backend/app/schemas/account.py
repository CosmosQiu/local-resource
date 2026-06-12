"""
Pydantic schemas for AI Account — create, update, response, secret view.
"""
from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------
class AIAccountCreate(BaseModel):
    platform: str = Field(..., min_length=1, max_length=32, examples=["openai"])
    account_name: str = Field(..., min_length=1, max_length=128, examples=["公司 OpenAI 主账号"])
    username: str | None = Field(None, max_length=512)
    password: str | None = Field(None, max_length=512)
    api_key: str | None = Field(None, max_length=512)
    cookie_data: str | None = Field(None, description="JSON string of cookies for expiry checks")
    expiration_date: datetime | None = None
    notes: str | None = None


class AIAccountUpdate(BaseModel):
    platform: str | None = Field(None, min_length=1, max_length=32)
    account_name: str | None = Field(None, min_length=1, max_length=128)
    username: str | None = Field(None, max_length=512)
    password: str | None = Field(None, max_length=512)
    api_key: str | None = Field(None, max_length=512)
    cookie_data: str | None = None
    status: str | None = Field(None, pattern=r"^(active|expired|error|suspended)$")
    expiration_date: datetime | None = None
    notes: str | None = None


# ---------------------------------------------------------------------------
# Response schemas — public (no secrets)
# ---------------------------------------------------------------------------
class AIAccountResponse(BaseModel):
    id: int
    platform: str
    account_name: str
    status: str
    expiration_date: datetime | None
    last_verified_at: datetime | None
    verification_error: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AIAccountListResponse(BaseModel):
    total: int
    items: list[AIAccountResponse]


# ---------------------------------------------------------------------------
# Response schema — secret view (requires accounts.read_secret permission)
# ---------------------------------------------------------------------------
class AIAccountSecretResponse(AIAccountResponse):
    """Includes decrypted credentials — only visible with accounts.read_secret."""
    username: str | None
    password: str | None
    api_key: str | None
    cookie_data: str | None
