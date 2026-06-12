"""
Container / bare-metal request API router.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import PermissionChecker, get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.container import (
    ContainerRequestApprove,
    ContainerRequestCreate,
    ContainerRequestListResponse,
    ContainerRequestResponse,
)
from app.services.container import ContainerService

router = APIRouter(tags=["Resource Requests"])


@router.get("/requests", response_model=ContainerRequestListResponse)
async def list_requests(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    status_filter: str | None = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    svc = ContainerService(db)
    # Normal users only see their own; approvers see all
    user_filter = None
    if not current_user.is_superuser and not any(
        p.codename == "compute.approve" for r in current_user.roles for p in r.permissions
    ):
        user_filter = current_user.id

    items, total = await svc.list_requests(user_id=user_filter, status=status_filter, skip=skip, limit=limit)
    return ContainerRequestListResponse(
        total=total,
        items=[_to_response(r) for r in items],
    )


@router.post("/requests", response_model=ContainerRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_request(
    body: ContainerRequestCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(PermissionChecker("compute.request"))],
):
    svc = ContainerService(db)
    req = await svc.create_request(current_user.id, body.model_dump())
    req = await svc.get_request(req.id)
    return _to_response(req)


@router.get("/requests/{request_id}", response_model=ContainerRequestResponse)
async def get_request(
    request_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    svc = ContainerService(db)
    req = await svc.get_request(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    # Only owner or approver/admin can view
    if req.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Access denied")
    return _to_response(req)


@router.post("/requests/{request_id}/approve", response_model=ContainerRequestResponse)
async def approve_request(
    request_id: int,
    body: ContainerRequestApprove,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(PermissionChecker("compute.approve"))],
):
    svc = ContainerService(db)
    req = await svc.get_request(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request is {req.status}")

    if body.approved:
        req = await svc.approve_request(req, current_user.id)
    else:
        req = await svc.reject_request(req, current_user.id)

    return _to_response(req)


@router.post("/requests/{request_id}/stop", response_model=ContainerRequestResponse)
async def stop_request(
    request_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    svc = ContainerService(db)
    req = await svc.get_request(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Access denied")
    if req.status != "running":
        raise HTTPException(status_code=400, detail=f"Request is {req.status}")

    req = await svc.stop_container(req)
    return _to_response(req)


def _to_response(req) -> ContainerRequestResponse:
    return ContainerRequestResponse(
        id=req.id,
        user_id=req.user_id,
        username=req.user.username if req.user else None,
        compute_resource_id=req.compute_resource_id,
        request_type=req.request_type,
        cpu_cores=req.cpu_cores,
        memory_gb=req.memory_gb,
        disk_gb=req.disk_gb,
        gpu_count=req.gpu_count,
        gpu_memory_mb=req.gpu_memory_mb,
        exposed_ports=req.exposed_ports,
        image_name=req.image_name,
        status=req.status,
        approved_by=req.approved_by,
        approved_at=req.approved_at,
        container_id=req.container_id,
        access_url=req.access_url,
        expires_at=req.expires_at,
        created_at=req.created_at,
        updated_at=req.updated_at,
    )
