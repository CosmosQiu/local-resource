"""
Dashboard summary schema.
"""
from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_accounts: int
    expiring_accounts: int  # accounts expiring within 7 days
    total_gpu_cards: int
    avg_gpu_utilization: float  # 0-100

    # Recent activities
    recent_requests: list[dict]
