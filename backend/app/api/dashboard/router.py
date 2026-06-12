"""
Dashboard API router — aggregate stats for the big screen.

Queries Prometheus for real-time host metrics (CPU / memory / disk)
for each managed compute resource.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import PermissionChecker, get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.account import AIAccount
from app.models.compute import ComputeResource
from app.models.container import ContainerRequest
from app.models.user import User
from app.schemas.dashboard import DashboardSummary, HostMetrics

logger = logging.getLogger("uvicorn")
router = APIRouter(tags=["Dashboard"])

NODE_EXPORTER_PORT = 9100


async def _query_prometheus(query: str) -> float | None:
    """Run an instant query against Prometheus and return the first value."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.PROMETHEUS_URL}/api/v1/query",
                params={"query": query},
            )
            data = resp.json()
            if data.get("status") != "success":
                return None
            results = data.get("data", {}).get("result", [])
            if not results:
                return None
            val = results[0].get("value", [None, None])[1]
            return float(val) if val is not None else None
    except Exception as exc:
        logger.warning("Prometheus query failed: %s", exc)
        return None


async def _fetch_host_metrics(host_ip: str) -> dict:
    """Query Prometheus for CPU, memory, and disk usage of a single host."""
    instance = f"{host_ip}:{NODE_EXPORTER_PORT}"

    cpu_q = (
        f'100 - (avg by (instance) (rate(node_cpu_seconds_total{{instance="{instance}",mode="idle"}}[1m])) * 100)'
    )
    mem_q = (
        f'100 - ((node_memory_MemAvailable_bytes{{instance="{instance}"}} '
        f'or node_memory_MemFree_bytes{{instance="{instance}"}}) '
        f'/ node_memory_MemTotal_bytes{{instance="{instance}"}} * 100)'
    )
    disk_q = (
        f'max by (instance) '
        f'((node_filesystem_size_bytes{{instance="{instance}",fstype!~"tmpfs|overlay|squashfs"}} '
        f'- node_filesystem_avail_bytes{{instance="{instance}",fstype!~"tmpfs|overlay|squashfs"}}) '
        f'/ node_filesystem_size_bytes{{instance="{instance}",fstype!~"tmpfs|overlay|squashfs"}} * 100)'
    )

    cpu = await _query_prometheus(cpu_q)
    mem = await _query_prometheus(mem_q)
    disk = await _query_prometheus(disk_q)

    return {
        "cpu_percent": round(cpu, 1) if cpu is not None else 0.0,
        "memory_percent": round(mem, 1) if mem is not None else 0.0,
        "disk_percent": round(disk, 1) if disk is not None else 0.0,
    }


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

    # --- Host metrics from Prometheus ---
    host_result = await db.execute(
        select(ComputeResource).where(ComputeResource.host_ip.isnot(None))
    )
    compute_hosts = list(host_result.scalars().all())
    total_hosts = len(compute_hosts)

    hosts: list[HostMetrics] = []
    for host in compute_hosts:
        if host.host_ip:
            metrics = await _fetch_host_metrics(host.host_ip)
            hosts.append(HostMetrics(
                host_id=host.id,
                host_name=host.name,
                host_ip=host.host_ip,
                cpu_percent=metrics["cpu_percent"],
                memory_percent=metrics["memory_percent"],
                disk_percent=metrics["disk_percent"],
                status=host.status or "offline",
            ))

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
        total_hosts=total_hosts,
        hosts=hosts,
        recent_requests=recent_requests,
    )
