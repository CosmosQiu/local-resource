"""
Authentication service — login, register, token management.
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_jwt_token,
    hash_password,
    verify_password,
)
from app.models.user import User, Role


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def authenticate(self, username: str, password: str) -> tuple[str, str] | None:
        """Return (access_token, refresh_token) if credentials are valid."""
        result = await self.db.execute(
            select(User).where(User.username == username).options(selectinload(User.roles))
        )
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None

        # Update last login
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.flush()

        sub = str(user.id)
        access = create_access_token(sub)
        refresh = create_refresh_token(sub)
        return access, refresh

    async def register(self, username: str, email: str, password: str,
                       display_name: str | None = None,
                       department: str | None = None) -> User | None:
        """Register a new user. Returns None if username/email already exists."""
        # Check uniqueness
        existing = await self.db.execute(
            select(User).where((User.username == username) | (User.email == email))
        )
        if existing.scalar_one_or_none():
            return None

        user = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            display_name=display_name,
            department=department,
        )

        # Assign default "user" role
        role_result = await self.db.execute(select(Role).where(Role.name == "user"))
        default_role = role_result.scalar_one_or_none()
        if default_role:
            user.roles.append(default_role)

        self.db.add(user)
        await self.db.flush()
        return user

    async def refresh_tokens(self, refresh_token: str) -> tuple[str, str] | None:
        """Validate refresh token and issue a new pair."""
        payload = decode_jwt_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        # Verify user still exists and is active
        result = await self.db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            return None

        new_access = create_access_token(user_id)
        new_refresh = create_refresh_token(user_id)
        return new_access, new_refresh

    async def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return False
        if not verify_password(old_password, user.hashed_password):
            return False
        user.hashed_password = hash_password(new_password)
        await self.db.flush()
        return True
