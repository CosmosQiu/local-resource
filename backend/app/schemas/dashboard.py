"""
Dashboard summary schema.
"""
from pydantic import BaseModel


class HostMetrics(BaseModel):
    """Per-host resource utilization from Prometheus."""
    host_id: int
    host_name: str
    host_ip: str
    cpu_percent: float = 0.0    # 0-100
    memory_percent: float = 0.0  # 0-100
    disk_percent: float = 0.0    # 0-100
    status: str = "offline"


class DashboardSummary(BaseModel):
    total_accounts: int
    expiring_accounts: int  # accounts expiring within 7 days
    total_hosts: int

    # Per-host real-time metrics from Prometheus
    hosts: list[HostMetrics] = []

    # Recent activities
    recent_requests: list[dict]
