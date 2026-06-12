"""
ComputeService — CRUD for compute resources + GPU metrics syncing.
"""
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.compute import ComputeResource, ComputeResourceGPU


class ComputeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_resources(
        self, resource_type: str | None = None, status: str | None = None,
        skip: int = 0, limit: int = 50,
    ) -> tuple[list[ComputeResource], int]:
        q = select(ComputeResource).options(selectinload(ComputeResource.gpus))
        count_q = select(func.count(ComputeResource.id))

        if resource_type:
            q = q.where(ComputeResource.resource_type == resource_type)
            count_q = count_q.where(ComputeResource.resource_type == resource_type)
        if status:
            q = q.where(ComputeResource.status == status)
            count_q = count_q.where(ComputeResource.status == status)

        q = q.order_by(ComputeResource.name).offset(skip).limit(limit)
        result = await self.db.execute(q)
        items = list(result.scalars().all())
        total = (await self.db.execute(count_q)).scalar_one()
        return items, total

    async def get_resource(self, resource_id: int) -> ComputeResource | None:
        result = await self.db.execute(
            select(ComputeResource)
            .where(ComputeResource.id == resource_id)
            .options(selectinload(ComputeResource.gpus))
        )
        return result.scalar_one_or_none()

    async def create_resource(self, data: dict) -> ComputeResource:
        gpu_data = data.pop("gpus", [])

        resource = ComputeResource(
            name=data["name"],
            resource_type=data["resource_type"],
            host_ip=data.get("host_ip"),
            management_port=data.get("management_port", 22),
            total_cpu_cores=data.get("total_cpu_cores", 0),
            total_memory_gb=data.get("total_memory_gb", 0.0),
            total_disk_gb=data.get("total_disk_gb", 0.0),
            available_cpu_cores=data.get("total_cpu_cores", 0),
            available_memory_gb=data.get("total_memory_gb", 0.0),
            available_disk_gb=data.get("total_disk_gb", 0.0),
            ansible_group=data.get("ansible_group"),
            ansible_vars=data.get("ansible_vars"),
            gpustack_worker_id=data.get("gpustack_worker_id"),
            notes=data.get("notes"),
        )
        self.db.add(resource)
        await self.db.flush()

        for g in gpu_data:
            gpu = ComputeResourceGPU(
                resource_id=resource.id,
                gpu_index=g["gpu_index"],
                gpu_name=g.get("gpu_name"),
                gpu_uuid=g.get("gpu_uuid"),
                total_memory_mb=g.get("total_memory_mb", 0),
                used_memory_mb=g.get("used_memory_mb", 0),
                utilization_pct=g.get("utilization_pct", 0.0),
                temperature_c=g.get("temperature_c"),
                power_draw_w=g.get("power_draw_w"),
            )
            self.db.add(gpu)

        await self.db.flush()
        return resource

    async def update_resource(self, resource: ComputeResource, data: dict) -> ComputeResource:
        updatable = [
            "name", "host_ip", "management_port",
            "total_cpu_cores", "total_memory_gb", "total_disk_gb",
            "available_cpu_cores", "available_memory_gb", "available_disk_gb",
            "status", "ansible_group", "ansible_vars", "gpustack_worker_id", "notes",
        ]
        for f in updatable:
            if f in data and data[f] is not None:
                setattr(resource, f, data[f])

        resource.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return resource

    async def delete_resource(self, resource: ComputeResource) -> None:
        await self.db.delete(resource)
        await self.db.flush()

    async def sync_gpu_metrics(self, resource_id: int, gpu_data: list[dict]) -> list[ComputeResourceGPU]:
        """Replace GPU snapshot for a resource."""
        # Remove old records (simplified — in production, keep history)
        await self.db.execute(
            __import__("sqlalchemy").delete(ComputeResourceGPU).where(
                ComputeResourceGPU.resource_id == resource_id
            )
        )

        gpus = []
        for g in gpu_data:
            gpu = ComputeResourceGPU(
                resource_id=resource_id,
                gpu_index=g["gpu_index"],
                gpu_name=g.get("gpu_name"),
                gpu_uuid=g.get("gpu_uuid"),
                total_memory_mb=g.get("total_memory_mb", 0),
                used_memory_mb=g.get("used_memory_mb", 0),
                utilization_pct=g.get("utilization_pct", 0.0),
                temperature_c=g.get("temperature_c"),
                power_draw_w=g.get("power_draw_w"),
            )
            self.db.add(gpu)
            gpus.append(gpu)

        await self.db.flush()
        return gpus
