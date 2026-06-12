"""
Auth router — login, register, refresh, me, change-password.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserInfo,
)
from app.services.auth import AuthService

router = APIRouter(tags=["Authentication"])


def _user_to_info(user: User) -> UserInfo:
    roles = [r.name for r in user.roles]
    perms = list({p.codename for r in user.roles for p in r.permissions})
    return UserInfo(
        id=user.id,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        department=user.department,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        roles=roles,
        permissions=sorted(perms),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    service = AuthService(db)
    tokens = await service.authenticate(body.username, body.password)
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    return TokenResponse(access_token=tokens[0], refresh_token=tokens[1])


@router.post("/register", response_model=UserInfo, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    service = AuthService(db)
    user = await service.register(
        username=body.username,
        email=body.email,
        password=body.password,
        display_name=body.display_name,
        department=body.department,
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        )
    return _user_to_info(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    service = AuthService(db)
    tokens = await service.refresh_tokens(body.refresh_token)
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    return TokenResponse(access_token=tokens[0], refresh_token=tokens[1])


@router.get("/me", response_model=UserInfo)
async def me(current_user: Annotated[User, Depends(get_current_user)]):
    return _user_to_info(current_user)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    body: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = AuthService(db)
    ok = await service.change_password(current_user.id, body.old_password, body.new_password)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old password is incorrect",
        )
    return MessageResponse(message="Password changed successfully")
