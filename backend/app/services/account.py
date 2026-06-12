"""
AccountService — CRUD for AI accounts with field-level encryption.
"""
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_secret, encrypt_secret
from app.models.account import AIAccount


class AccountService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    async def list_accounts(
        self, platform: str | None = None, status: str | None = None,
        skip: int = 0, limit: int = 50,
    ) -> tuple[list[AIAccount], int]:
        """Return (items, total_count)."""
        q = select(AIAccount)
        count_q = select(func.count(AIAccount.id))

        if platform:
            q = q.where(AIAccount.platform == platform)
            count_q = count_q.where(AIAccount.platform == platform)
        if status:
            q = q.where(AIAccount.status == status)
            count_q = count_q.where(AIAccount.status == status)

        q = q.order_by(AIAccount.updated_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(q)
        items = list(result.scalars().all())

        total_result = await self.db.execute(count_q)
        total = total_result.scalar_one()

        return items, total

    async def get_account(self, account_id: int) -> AIAccount | None:
        result = await self.db.execute(select(AIAccount).where(AIAccount.id == account_id))
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------
    async def create_account(self, data: dict) -> AIAccount:
        """Create an account, encrypting sensitive fields before storage."""
        account = AIAccount(
            platform=data["platform"],
            account_name=data["account_name"],
            status="active",
            notes=data.get("notes"),
            expiration_date=data.get("expiration_date"),
        )
        # Encrypt sensitive fields
        if data.get("username"):
            account.username = encrypt_secret(data["username"])
        if data.get("password"):
            account.password = encrypt_secret(data["password"])
        if data.get("api_key"):
            account.api_key = encrypt_secret(data["api_key"])
        if data.get("cookie_data"):
            account.cookie_data = encrypt_secret(data["cookie_data"])

        self.db.add(account)
        await self.db.flush()
        return account

    async def update_account(self, account: AIAccount, data: dict) -> AIAccount:
        """Update an account with optional field-level encryption."""
        for field in ("platform", "account_name", "notes", "expiration_date", "status"):
            if field in data and data[field] is not None:
                setattr(account, field, data[field])

        # Encrypt sensitive fields if provided
        for field in ("username", "password", "api_key", "cookie_data"):
            if field in data:
                val = data[field]
                if val is not None:
                    setattr(account, field, encrypt_secret(val))

        account.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return account

    async def delete_account(self, account: AIAccount) -> None:
        await self.db.delete(account)
        await self.db.flush()

    async def verify_account(self, account: AIAccount, success: bool, error: str | None = None) -> AIAccount:
        """Update verification status after cookie check."""
        account.last_verified_at = datetime.now(timezone.utc)
        if success:
            account.verification_error = None
        else:
            account.verification_error = error
            if account.status == "active":
                account.status = "error"
        await self.db.flush()
        return account

    # ------------------------------------------------------------------
    # Secret decryption
    # ------------------------------------------------------------------
    @staticmethod
    def decrypt_secrets(account: AIAccount) -> dict[str, str | None]:
        """Decrypt sensitive fields for authorized viewing."""
        return {
            "username": decrypt_secret(account.username) if account.username else None,
            "password": decrypt_secret(account.password) if account.password else None,
            "api_key": decrypt_secret(account.api_key) if account.api_key else None,
            "cookie_data": decrypt_secret(account.cookie_data) if account.cookie_data else None,
        }
