"""
Pydantic schemas for container / bare-metal requests.
"""
from datetime import datetime

from pydantic import BaseModel, Field


class ContainerRequestCreate(BaseModel):
    request_type: str = Field(..., pattern=r"^(container|bare_metal)$")
    compute_resource_id: int | None = None
    cpu_cores: int = Field(2, ge=1, le=256)
    memory_gb: float = Field(4.0, ge=0.5, le=2048)
    disk_gb: float = Field(20.0, ge=1.0, le=10000)
    gpu_count: int = Field(0, ge=0, le=64)
    gpu_memory_mb: int | None = None
    exposed_ports: dict | None = None
    image_name: str | None = None


class ContainerRequestApprove(BaseModel):
    approved: bool


class ContainerRequestResponse(BaseModel):
    id: int
    user_id: int
    username: str | None = None        # populated from relationship
    compute_resource_id: int | None
    request_type: str
    cpu_cores: int
    memory_gb: float
    disk_gb: float
    gpu_count: int
    gpu_memory_mb: int | None
    exposed_ports: dict | None
    image_name: str | None
    status: str
    approved_by: int | None
    approved_at: datetime | None
    container_id: str | None
    access_url: str | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContainerRequestListResponse(BaseModel):
    total: int
    items: list[ContainerRequestResponse]
