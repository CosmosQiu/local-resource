"""
Admin API router — user management, role assignment, permission configuration.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import PermissionChecker, get_current_user
from app.core.database import get_db
from app.core.security import hash_password
from app.models.user import Permission, Role, User
from app.schemas.auth import UserInfo

router = APIRouter(tags=["Admin"])


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------
@router.get("/users", response_model=list[UserInfo])
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    _u: Annotated[User, Depends(PermissionChecker("admin.manage_users"))],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .offset(skip).limit(limit)
    )
    users = result.scalars().all()
    return [_user_to_info(u) for u in users]


@router.put("/users/{user_id}/roles", response_model=UserInfo)
async def assign_roles(
    user_id: int,
    role_ids: list[int],
    db: Annotated[AsyncSession, Depends(get_db)],
    _u: Annotated[User, Depends(PermissionChecker("admin.manage_roles"))],
):
    result = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.roles))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    role_result = await db.execute(select(Role).where(Role.id.in_(role_ids)))
    new_roles = list(role_result.scalars().all())
    user.roles = new_roles
    await db.commit()
    await db.refresh(user)

    # Re-fetch with permissions
    result = await db.execute(
        select(User).where(User.id == user_id)
        .options(selectinload(User.roles).selectinload(Role.permissions))
    )
    user = result.scalar_one()
    return _user_to_info(user)


@router.get("/roles", response_model=list[dict])
async def list_roles(
    db: Annotated[AsyncSession, Depends(get_db)],
    _u: Annotated[User, Depends(PermissionChecker("admin.manage_roles"))],
):
    result = await db.execute(
        select(Role).options(selectinload(Role.permissions))
    )
    roles = result.scalars().all()
    return [
        {
            "id": r.id, "name": r.name, "description": r.description,
            "permissions": [p.codename for p in r.permissions],
        }
        for r in roles
    ]


@router.get("/permissions", response_model=list[dict])
async def list_permissions(
    db: Annotated[AsyncSession, Depends(get_db)],
    _u: Annotated[User, Depends(PermissionChecker("admin.manage_roles"))],
):
    result = await db.execute(select(Permission))
    perms = result.scalars().all()
    return [{"id": p.id, "codename": p.codename, "description": p.description, "resource_type": p.resource_type} for p in perms]


def _user_to_info(user: User) -> UserInfo:
    roles = [r.name for r in user.roles]
    perms = list({p.codename for r in user.roles for p in r.permissions})
    return UserInfo(
        id=user.id, username=user.username, email=user.email,
        display_name=user.display_name, department=user.department,
        is_active=user.is_active, is_superuser=user.is_superuser,
        roles=roles, permissions=sorted(perms),
    )
