"""
ComputeResource & ComputeResourceGPU models.

Represents heterogeneous compute resources:
- bare_metal: physical GPU servers
- k8s_cluster: Kubernetes clusters
- linux_host: Linux GPU workstations
- windows_host: Windows GPU workstations (monitored via Ansible)

GPU metrics are tracked separately in ComputeResourceGPU for time-series queries.
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ComputeResource(Base):
    __tablename__ = "compute_resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identity
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="Display name")
    resource_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True,
        comment="bare_metal, k8s_cluster, linux_host, windows_host"
    )

    # Network
    host_ip: Mapped[str] = mapped_column(String(64), nullable=True, comment="Management IP")
    management_port: Mapped[int] = mapped_column(Integer, default=22, nullable=False)

    # Total capacity (from hardware inventory)
    total_cpu_cores: Mapped[int] = mapped_column(Integer, default=0)
    total_memory_gb: Mapped[float] = mapped_column(Float, default=0.0)
    total_disk_gb: Mapped[float] = mapped_column(Float, default=0.0)

    # Available capacity (updated periodically)
    available_cpu_cores: Mapped[float] = mapped_column(Float, default=0.0)
    available_memory_gb: Mapped[float] = mapped_column(Float, default=0.0)
    available_disk_gb: Mapped[float] = mapped_column(Float, default=0.0)

    # Status
    status: Mapped[str] = mapped_column(
        String(16), default="offline",
        comment="online, offline, maintenance"
    )

    # Integration — Ansible
    ansible_group: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="Ansible inventory group"
    )
    ansible_vars: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="Extra Ansible host vars"
    )

    # Integration — GPUStack (optional, for GPUStack-managed clusters)
    gpustack_worker_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True, comment="GPUStack worker UUID"
    )

    # Health
    last_heartbeat: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    gpus: Mapped[list["ComputeResourceGPU"]] = relationship(
        "ComputeResourceGPU", back_populates="resource", lazy="selectin", cascade="all, delete-orphan"
    )
    container_requests: Mapped[list["ContainerRequest"]] = relationship(
        "ContainerRequest", back_populates="compute_resource", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<ComputeResource(id={self.id}, name={self.name!r}, type={self.resource_type!r})>"


class ComputeResourceGPU(Base):
    """Per-GPU metrics snapshot — updated on each monitoring cycle."""

    __tablename__ = "compute_resource_gpus"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("compute_resources.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # GPU identity
    gpu_index: Mapped[int] = mapped_column(Integer, nullable=False, comment="nvidia-smi index")
    gpu_name: Mapped[str] = mapped_column(String(128), nullable=True, comment="e.g. Tesla V100-SXM2-32GB")
    gpu_uuid: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Metrics
    total_memory_mb: Mapped[int] = mapped_column(Integer, default=0)
    used_memory_mb: Mapped[int] = mapped_column(Integer, default=0)
    utilization_pct: Mapped[float] = mapped_column(Float, default=0.0, comment="GPU core utilization %")
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    power_draw_w: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Timestamp of this snapshot
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        comment="When this GPU metric snapshot was taken",
    )

    # Relationships
    resource: Mapped["ComputeResource"] = relationship("ComputeResource", back_populates="gpus")

    def __repr__(self) -> str:
        return f"<GPU(id={self.id}, name={self.gpu_name!r}, idx={self.gpu_index})>"
