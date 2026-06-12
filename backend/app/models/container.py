"""
ContainerRequest model — user applications for development containers or bare-metal access.

Workflow:
  pending → approved → running → completed / expired
           ↘ rejected
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ContainerRequest(Base):
    __tablename__ = "container_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Requester
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Target compute resource
    compute_resource_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("compute_resources.id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="Can be NULL for new bare-metal requests not yet assigned"
    )

    # Request type
    request_type: Mapped[str] = mapped_column(
        String(16), nullable=False,
        comment="container, bare_metal"
    )

    # Resource specs
    cpu_cores: Mapped[int] = mapped_column(Integer, default=2)
    memory_gb: Mapped[float] = mapped_column(Float, default=4.0)
    disk_gb: Mapped[float] = mapped_column(Float, default=20.0)

    # GPU requirements
    gpu_count: Mapped[int] = mapped_column(Integer, default=0)
    gpu_memory_mb: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Minimum GPU memory per card in MB"
    )

    # Networking
    exposed_ports: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment='e.g. {"8888/tcp": 30080, "22/tcp": 30022}'
    )

    # Container image (for container type)
    image_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        comment="Docker image, e.g. nvidia/cuda:12.4.0-devel-ubuntu22.04"
    )

    # Workflow status
    status: Mapped[str] = mapped_column(
        String(16), default="pending",
        comment="pending, approved, running, rejected, completed, expired"
    )

    # Approval
    approved_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Runtime info (filled after container is created)
    container_id: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="Docker container ID")
    access_url: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="e.g. http://host:port")
    access_credential: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Encrypted access password/token"
    )

    # Expiry
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="When this resource allocation expires"
    )

    # Timestamps
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
    user: Mapped["User"] = relationship("User", back_populates="container_requests", foreign_keys=[user_id])
    compute_resource: Mapped["ComputeResource | None"] = relationship(
        "ComputeResource", back_populates="container_requests"
    )

    def __repr__(self) -> str:
        return f"<ContainerRequest(id={self.id}, type={self.request_type!r}, status={self.status!r})>"
