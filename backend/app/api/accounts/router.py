"""
AI Account API router — CRUD with permission-gated secret viewing.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import PermissionChecker, get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.account import (
    AIAccountCreate,
    AIAccountListResponse,
    AIAccountResponse,
    AIAccountSecretResponse,
    AIAccountUpdate,
)
from app.services.account import AccountService

router = APIRouter(tags=["AI Accounts"])


@router.get("/", response_model=AIAccountListResponse)
async def list_accounts(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(PermissionChecker("accounts.read"))],
    platform: str | None = Query(None),
    status: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    service = AccountService(db)
    items, total = await service.list_accounts(platform=platform, status=status, skip=skip, limit=limit)
    return AIAccountListResponse(
        total=total,
        items=[AIAccountResponse.model_validate(a) for a in items],
    )


@router.post("/", response_model=AIAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    body: AIAccountCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(PermissionChecker("accounts.create"))],
):
    service = AccountService(db)
    account = await service.create_account(body.model_dump(exclude_unset=True))
    return AIAccountResponse.model_validate(account)


@router.get("/{account_id}", response_model=AIAccountResponse)
async def get_account(
    account_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(PermissionChecker("accounts.read"))],
):
    service = AccountService(db)
    account = await service.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return AIAccountResponse.model_validate(account)


@router.put("/{account_id}", response_model=AIAccountResponse)
async def update_account(
    account_id: int,
    body: AIAccountUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(PermissionChecker("accounts.update"))],
):
    service = AccountService(db)
    account = await service.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    account = await service.update_account(account, body.model_dump(exclude_unset=True))
    return AIAccountResponse.model_validate(account)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(PermissionChecker("accounts.delete"))],
):
    service = AccountService(db)
    account = await service.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    await service.delete_account(account)


@router.get("/{account_id}/secret", response_model=AIAccountSecretResponse)
async def get_account_secret(
    account_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(PermissionChecker("accounts.read_secret"))],
):
    """View decrypted credentials — requires accounts.read_secret permission."""
    service = AccountService(db)
    account = await service.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    response = AIAccountSecretResponse.model_validate(account)
    secrets = service.decrypt_secrets(account)
    response.username = secrets["username"]
    response.password = secrets["password"]
    response.api_key = secrets["api_key"]
    response.cookie_data = secrets["cookie_data"]
    return response
