"""
ContainerService — request lifecycle management.
"""
from datetime import datetime, timezone, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.container import ContainerRequest
from app.models.user import User


class ContainerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_requests(
        self, user_id: int | None = None, status: str | None = None,
        skip: int = 0, limit: int = 50,
    ) -> tuple[list[ContainerRequest], int]:
        q = select(ContainerRequest).options(selectinload(ContainerRequest.user))
        count_q = select(func.count(ContainerRequest.id))

        if user_id:
            q = q.where(ContainerRequest.user_id == user_id)
            count_q = count_q.where(ContainerRequest.user_id == user_id)
        if status:
            q = q.where(ContainerRequest.status == status)
            count_q = count_q.where(ContainerRequest.status == status)

        q = q.order_by(ContainerRequest.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        items = list(result.scalars().all())
        total = (await self.db.execute(count_q)).scalar_one()
        return items, total

    async def get_request(self, request_id: int) -> ContainerRequest | None:
        result = await self.db.execute(
            select(ContainerRequest)
            .where(ContainerRequest.id == request_id)
            .options(selectinload(ContainerRequest.user))
        )
        return result.scalar_one_or_none()

    async def create_request(self, user_id: int, data: dict) -> ContainerRequest:
        req = ContainerRequest(
            user_id=user_id,
            request_type=data["request_type"],
            compute_resource_id=data.get("compute_resource_id"),
            cpu_cores=data.get("cpu_cores", 2),
            memory_gb=data.get("memory_gb", 4.0),
            disk_gb=data.get("disk_gb", 20.0),
            gpu_count=data.get("gpu_count", 0),
            gpu_memory_mb=data.get("gpu_memory_mb"),
            exposed_ports=data.get("exposed_ports"),
            image_name=data.get("image_name"),
            status="pending",
        )
        self.db.add(req)
        await self.db.flush()
        return req

    async def approve_request(self, request: ContainerRequest, approver_id: int) -> ContainerRequest:
        request.status = "provisioning"
        request.approved_by = approver_id
        request.approved_at = datetime.now(timezone.utc)
        request.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        await self.db.flush()

        # Trigger Pi agent to provision the container asynchronously
        from app.tasks.provision import provision_container
        provision_container.delay(request.id)

        return request

    async def reject_request(self, request: ContainerRequest, approver_id: int) -> ContainerRequest:
        request.status = "rejected"
        request.approved_by = approver_id
        request.approved_at = datetime.now(timezone.utc)
        await self.db.flush()
        return request

    async def start_container(self, request: ContainerRequest, container_id: str,
                              access_url: str, access_credential: str | None = None) -> ContainerRequest:
        request.status = "running"
        request.container_id = container_id
        request.access_url = access_url
        if access_credential:
            from app.core.security import encrypt_secret
            request.access_credential = encrypt_secret(access_credential)
        await self.db.flush()
        return request

    async def stop_container(self, request: ContainerRequest) -> ContainerRequest:
        request.status = "completed"
        request.container_id = None
        request.access_url = None
        request.access_credential = None
        await self.db.flush()
        return request
