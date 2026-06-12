"""
Pydantic schemas for compute resources.
"""
from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# GPU
# ---------------------------------------------------------------------------
class GPUCreate(BaseModel):
    gpu_index: int
    gpu_name: str | None = None
    gpu_uuid: str | None = None
    total_memory_mb: int = 0
    used_memory_mb: int = 0
    utilization_pct: float = 0.0
    temperature_c: float | None = None
    power_draw_w: float | None = None


class GPUResponse(BaseModel):
    id: int
    resource_id: int
    gpu_index: int
    gpu_name: str | None
    gpu_uuid: str | None
    total_memory_mb: int
    used_memory_mb: int
    utilization_pct: float
    temperature_c: float | None
    power_draw_w: float | None
    recorded_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Compute Resource
# ---------------------------------------------------------------------------
class ComputeResourceCreate(BaseModel):
    name: str = Field(..., max_length=128)
    resource_type: str = Field(..., pattern=r"^(bare_metal|k8s_cluster|linux_host|windows_host)$")
    host_ip: str | None = None
    ssh_username: str | None = None
    ssh_password: str | None = None
    management_port: int = 22
    total_cpu_cores: int = 0
    total_memory_gb: float = 0.0
    total_disk_gb: float = 0.0
    ansible_group: str | None = None
    ansible_vars: dict | None = None
    notes: str | None = None


class ComputeResourceUpdate(BaseModel):
    name: str | None = None
    host_ip: str | None = None
    ssh_username: str | None = None
    ssh_password: str | None = None
    management_port: int | None = None
    total_cpu_cores: int | None = None
    total_memory_gb: float | None = None
    total_disk_gb: float | None = None
    available_cpu_cores: float | None = None
    available_memory_gb: float | None = None
    available_disk_gb: float | None = None
    status: str | None = Field(None, pattern=r"^(online|offline|maintenance)$")
    ansible_group: str | None = None
    ansible_vars: dict | None = None
    notes: str | None = None


class ComputeResourceResponse(BaseModel):
    id: int
    name: str
    resource_type: str
    host_ip: str | None
    management_port: int
    ssh_username: str | None = None
    total_cpu_cores: int
    total_memory_gb: float
    total_disk_gb: float
    available_cpu_cores: float
    available_memory_gb: float
    available_disk_gb: float
    status: str
    ansible_group: str | None
    init_command: str | None = None
    init_status: str = "pending"
    grafana_url: str | None = None
    last_heartbeat: datetime | None
    notes: str | None
    gpus: list[GPUResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ComputeResourceListResponse(BaseModel):
    total: int
    items: list[ComputeResourceResponse]
