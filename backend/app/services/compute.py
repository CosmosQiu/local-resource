"""
ComputeService — CRUD for compute resources with Grafana monitoring init.
"""
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import encrypt_secret
from app.core.config import settings
from app.models.compute import ComputeResource, ComputeResourceGPU


PROMETHEUS_SCRAPE_PORT = 9100  # node_exporter default port


def _generate_init_command(host_ip: str, node_exporter_version: str = "1.8.2") -> str:
    """Generate a one-liner to install node_exporter on the target host."""
    return (
        f"# === Node Exporter 安装命令 ===\n"
        f"# 在目标主机 ({host_ip}) 上以 root 执行：\n"
        f"curl -sSL https://github.com/prometheus/node_exporter/releases/download/"
        f"v{node_exporter_version}/node_exporter-{node_exporter_version}.linux-amd64.tar.gz \\\n"
        f"  | sudo tar xz -C /usr/local/bin/ --strip-components=1 && \\\n"
        f"sudo tee /etc/systemd/system/node_exporter.service > /dev/null <<'EOF'\n"
        f"[Unit]\n"
        f"Description=Node Exporter\n"
        f"After=network.target\n\n"
        f"[Service]\n"
        f"ExecStart=/usr/local/bin/node_exporter\n"
        f"Restart=always\n\n"
        f"[Install]\n"
        f"WantedBy=multi-user.target\n"
        f"EOF\n"
        f"sudo systemctl daemon-reload && sudo systemctl enable --now node_exporter && \\\n"
        f"echo 'Node Exporter installed. Prometheus will scrape {host_ip}:{PROMETHEUS_SCRAPE_PORT}'"
    )


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
        ssh_password = data.pop("ssh_password", None)

        resource = ComputeResource(
            name=data["name"],
            resource_type=data["resource_type"],
            host_ip=data.get("host_ip"),
            ssh_username=data.get("ssh_username"),
            management_port=data.get("management_port", 22),
            total_cpu_cores=data.get("total_cpu_cores", 0),
            total_memory_gb=data.get("total_memory_gb", 0.0),
            total_disk_gb=data.get("total_disk_gb", 0.0),
            available_cpu_cores=data.get("total_cpu_cores", 0),
            available_memory_gb=data.get("total_memory_gb", 0.0),
            available_disk_gb=data.get("total_disk_gb", 0.0),
            ansible_group=data.get("ansible_group"),
            ansible_vars=data.get("ansible_vars"),
            notes=data.get("notes"),
        )

        # Encrypt SSH password if provided
        if ssh_password:
            resource.ssh_password = encrypt_secret(ssh_password)

        # Generate init command for node_exporter
        if resource.host_ip:
            resource.init_command = _generate_init_command(resource.host_ip)
            resource.init_status = "pending"
            resource.grafana_url = (
                f"{settings.GRAFANA_URL}/d/node-exporter/"
                f"?var-instance={resource.host_ip}:{PROMETHEUS_SCRAPE_PORT}"
                if settings.GRAFANA_URL else None
            )

        self.db.add(resource)
        await self.db.flush()
        return resource

    async def update_resource(self, resource: ComputeResource, data: dict) -> ComputeResource:
        updatable = [
            "name", "host_ip", "management_port",
            "total_cpu_cores", "total_memory_gb", "total_disk_gb",
            "available_cpu_cores", "available_memory_gb", "available_disk_gb",
            "status", "ansible_group", "ansible_vars", "notes",
            "ssh_username",
        ]
        for f in updatable:
            if f in data and data[f] is not None:
                setattr(resource, f, data[f])

        # Re-encrypt SSH password if provided
        if "ssh_password" in data and data["ssh_password"] is not None:
            resource.ssh_password = encrypt_secret(data["ssh_password"])

        # Regenerate init command if host_ip changed
        if "host_ip" in data and data["host_ip"] is not None:
            resource.init_command = _generate_init_command(data["host_ip"])
            resource.init_status = "pending"
            if settings.GRAFANA_URL:
                resource.grafana_url = (
                    f"{settings.GRAFANA_URL}/d/node-exporter/"
                    f"?var-instance={data['host_ip']}:{PROMETHEUS_SCRAPE_PORT}"
                )

        resource.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return resource

    async def delete_resource(self, resource: ComputeResource) -> None:
        await self.db.delete(resource)
        await self.db.flush()

    async def get_init_command(self, resource_id: int) -> dict | None:
        """Return the init command and status for a resource."""
        result = await self.db.execute(
            select(ComputeResource).where(ComputeResource.id == resource_id)
        )
        resource = result.scalar_one_or_none()
        if not resource:
            return None
        return {
            "resource_id": resource.id,
            "resource_name": resource.name,
            "host_ip": resource.host_ip,
            "init_command": resource.init_command,
            "init_status": resource.init_status,
            "grafana_url": resource.grafana_url,
        }

    async def sync_gpu_metrics(self, resource_id: int, gpu_data: list[dict]) -> list[ComputeResourceGPU]:
        """Replace GPU snapshot for a resource (kept for backward compat)."""
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
