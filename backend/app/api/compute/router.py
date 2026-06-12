"""
Compute resource API router.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import PermissionChecker, get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.compute import (
    ComputeResourceCreate,
    ComputeResourceListResponse,
    ComputeResourceResponse,
    ComputeResourceUpdate,
)
from app.services.compute import ComputeService

router = APIRouter(tags=["Compute Resources"])


@router.get("/", response_model=ComputeResourceListResponse)
async def list_resources(
    db: Annotated[AsyncSession, Depends(get_db)],
    _u: Annotated[User, Depends(PermissionChecker("compute.read"))],
    resource_type: str | None = Query(None),
    status: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    svc = ComputeService(db)
    items, total = await svc.list_resources(resource_type, status, skip, limit)
    return ComputeResourceListResponse(
        total=total,
        items=[ComputeResourceResponse.model_validate(r) for r in items],
    )


@router.post("/", response_model=ComputeResourceResponse, status_code=status.HTTP_201_CREATED)
async def create_resource(
    body: ComputeResourceCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _u: Annotated[User, Depends(PermissionChecker("compute.manage"))],
):
    svc = ComputeService(db)
    resource = await svc.create_resource(body.model_dump())
    # Re-fetch with GPUs loaded
    resource = await svc.get_resource(resource.id)
    return ComputeResourceResponse.model_validate(resource)


@router.get("/{resource_id}", response_model=ComputeResourceResponse)
async def get_resource(
    resource_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _u: Annotated[User, Depends(PermissionChecker("compute.read"))],
):
    svc = ComputeService(db)
    r = await svc.get_resource(resource_id)
    if not r:
        raise HTTPException(status_code=404, detail="Resource not found")
    return ComputeResourceResponse.model_validate(r)


@router.put("/{resource_id}", response_model=ComputeResourceResponse)
async def update_resource(
    resource_id: int,
    body: ComputeResourceUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _u: Annotated[User, Depends(PermissionChecker("compute.manage"))],
):
    svc = ComputeService(db)
    r = await svc.get_resource(resource_id)
    if not r:
        raise HTTPException(status_code=404, detail="Resource not found")
    r = await svc.update_resource(r, body.model_dump(exclude_unset=True))
    return ComputeResourceResponse.model_validate(r)


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(
    resource_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _u: Annotated[User, Depends(PermissionChecker("compute.manage"))],
):
    svc = ComputeService(db)
    r = await svc.get_resource(resource_id)
    if not r:
        raise HTTPException(status_code=404, detail="Resource not found")
    await svc.delete_resource(r)
