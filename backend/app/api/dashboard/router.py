"""
Dashboard API router — aggregate stats for the big screen.
"""
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import PermissionChecker, get_current_user
from app.core.database import get_db
from app.models.account import AIAccount
from app.models.compute import ComputeResource, ComputeResourceGPU
from app.models.container import ContainerRequest
from app.models.user import User
from app.schemas.dashboard import DashboardSummary

router = APIRouter(tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(PermissionChecker("dashboard.view"))],
):
    # --- Account stats ---
    total_accounts_result = await db.execute(select(func.count(AIAccount.id)))
    total_accounts = total_accounts_result.scalar_one()

    soon = datetime.now(timezone.utc) + timedelta(days=7)
    expiring_result = await db.execute(
        select(func.count(AIAccount.id)).where(
            AIAccount.status == "active",
            AIAccount.expiration_date.isnot(None),
            AIAccount.expiration_date <= soon,
        )
    )
    expiring_accounts = expiring_result.scalar_one()

    # --- GPU stats ---
    # Count total GPU cards from latest snapshot per resource
    # (simplified: count distinct GPUs)
    gpu_count_result = await db.execute(
        select(func.count(func.distinct(ComputeResourceGPU.gpu_uuid)))
        .where(ComputeResourceGPU.gpu_uuid.isnot(None))
    )
    total_gpu_cards = gpu_count_result.scalar_one()

    # Average utilization across all GPU records in the last hour
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    avg_util_result = await db.execute(
        select(func.avg(ComputeResourceGPU.utilization_pct)).where(
            ComputeResourceGPU.recorded_at >= one_hour_ago
        )
    )
    avg_gpu = avg_util_result.scalar_one()
    avg_gpu_utilization = round(float(avg_gpu or 0), 1)

    # --- Recent requests ---
    recent_result = await db.execute(
        select(ContainerRequest)
        .options(selectinload(ContainerRequest.user))
        .order_by(ContainerRequest.created_at.desc())
        .limit(5)
    )
    recent_requests = []
    for req in recent_result.scalars().all():
        recent_requests.append({
            "time": req.created_at.isoformat() if req.created_at else "",
            "user": req.user.username if req.user else "Unknown",
            "type": req.request_type,
            "status": req.status,
            "gpu_count": req.gpu_count,
        })

    return DashboardSummary(
        total_accounts=total_accounts,
        expiring_accounts=expiring_accounts,
        total_gpu_cards=total_gpu_cards,
        avg_gpu_utilization=avg_gpu_utilization,
        recent_requests=recent_requests,
    )
