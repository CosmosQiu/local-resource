"""
AIAccount model — stores third-party AI platform credentials.

All sensitive fields (password, api_key, cookie_data) are encrypted at rest
via AES-256-GCM (see app.core.security).
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AIAccount(Base):
    __tablename__ = "ai_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Platform identifier: openai, claude, deepseek, gemini, etc.
    platform: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    # Human-readable label for this account
    account_name: Mapped[str] = mapped_column(String(128), nullable=False)

    # Login credentials — encrypted at rest
    username: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Encrypted username")
    password: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Encrypted password")
    api_key: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Encrypted API key")

    # Cookie data (JSON string) for cookie-based session checks — encrypted at rest
    cookie_data: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Encrypted cookie JSON for expiry checks"
    )

    # Account status
    status: Mapped[str] = mapped_column(
        String(16), default="active", nullable=False,
        comment="active, expired, error, suspended"
    )
    expiration_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Account/subscription expiry date"
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Last cookie/credential verification time"
    )
    verification_error: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Error message from last verification attempt"
    )

    # Metadata
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AIAccount(id={self.id}, platform={self.platform!r}, name={self.account_name!r})>"
