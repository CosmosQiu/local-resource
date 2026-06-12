"""
Celery task — provision a container on a remote host via Pi + Ansible.
Triggered when an operator approves a resource request.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.database import async_session
from app.core.security import decrypt_secret
from app.models.compute import ComputeResource
from app.models.container import ContainerRequest
from app.services.pi_agent import execute_provision

logger = logging.getLogger("uvicorn")


@celery_app.task(name="app.tasks.provision.provision_container")
def provision_container(request_id: int) -> dict:
    """
    Provision a Docker container on the target compute resource.

    Called synchronously in dev mode (task_always_eager=True);
    asynchronously via Celery worker in staging/production.
    """
    import asyncio
    return asyncio.run(_provision_container_async(request_id))


async def _provision_container_async(request_id: int) -> dict:
    """Async implementation of container provisioning."""
    async with async_session() as db:
        # Load request
        result = await db.execute(
            select(ContainerRequest).where(ContainerRequest.id == request_id)
        )
        req = result.scalar_one_or_none()
        if not req:
            return {"status": "error", "error": f"Request {request_id} not found"}

        # Load target compute resource
        if not req.compute_resource_id:
            return {"status": "error", "error": "No compute resource assigned"}

        result = await db.execute(
            select(ComputeResource).where(ComputeResource.id == req.compute_resource_id)
        )
        resource = result.scalar_one_or_none()
        if not resource:
            return {"status": "error", "error": "Compute resource not found"}

        # Decrypt SSH password
        ssh_password = None
        if resource.ssh_password:
            try:
                ssh_password = decrypt_secret(resource.ssh_password)
            except Exception:
                return {"status": "error", "error": "Failed to decrypt SSH password"}

        if not resource.host_ip or not resource.ssh_username:
            return {"status": "error", "error": "Missing host IP or SSH username on compute resource"}

        # Build provision parameters
        ports_json = req.exposed_ports or {}
        container_name = f"arh-{req.request_type}-{req.id}"

        params = {
            "host_ip": resource.host_ip,
            "ssh_username": resource.ssh_username,
            "ssh_password": ssh_password,
            "container_name": container_name,
            "image_name": req.image_name or "ubuntu:22.04",
            "cpu_cores": req.cpu_cores,
            "memory_gb": req.memory_gb,
            "disk_gb": req.disk_gb,
            "gpu_count": req.gpu_count,
            "ports": json.dumps(ports_json),
            "exposed_ports": req.exposed_ports,
        }

        logger.info(
            "Provisioning container for request %d on host %s (%s)",
            request_id, resource.host_ip, req.image_name
        )

        # Execute provisioning
        result_data = execute_provision(params)

        if result_data.get("status") == "success":
            # Update request with connection info
            req.status = "running"
            req.container_id = result_data.get("container_id", "")
            req.access_url = result_data.get(
                "access_url",
                f"{resource.host_ip}:{result_data.get('ssh_port', 22)}"
            )

            # Encrypt credential
            credential = result_data.get("access_credential", "")
            if credential:
                from app.core.security import encrypt_secret
                req.access_credential = encrypt_secret(credential)

            logger.info(
                "Container provisioned: request=%d container=%s url=%s",
                request_id, req.container_id, req.access_url
            )
        else:
            # Provisioning failed — keep status as approved, record error
            error_msg = result_data.get("error", "Unknown provisioning error")
            logger.error("Provisioning failed for request %d: %s", request_id, error_msg)
            req.status = "approved"
            req.notes = f"Provisioning failed: {error_msg}"

        await db.commit()
        return result_data
