"""Add SSH credentials, init_command, and Grafana fields — remove gpustack_worker_id

Revision ID: 0002_add_ssh_and_monitoring
Revises: 0001_initial
Create Date: 2026-06-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_add_ssh_and_monitoring"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old GPUStack column
    op.drop_index("ix_compute_resources_gpustack_worker_id", table_name="compute_resources")
    op.drop_column("compute_resources", "gpustack_worker_id")

    # SSH credentials (encrypted at rest)
    op.add_column("compute_resources", sa.Column("ssh_username", sa.String(128), nullable=True))
    op.add_column("compute_resources", sa.Column("ssh_password", sa.Text(), nullable=True))

    # Init command for node_exporter installation
    op.add_column("compute_resources", sa.Column("init_command", sa.Text(), nullable=True))
    op.add_column(
        "compute_resources",
        sa.Column(
            "init_status",
            sa.String(16),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
    )

    # Grafana dashboard URL / UID for embedding
    op.add_column("compute_resources", sa.Column("grafana_url", sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column("compute_resources", "grafana_url")
    op.drop_column("compute_resources", "init_status")
    op.drop_column("compute_resources", "init_command")
    op.drop_column("compute_resources", "ssh_password")
    op.drop_column("compute_resources", "ssh_username")

    op.add_column(
        "compute_resources",
        sa.Column("gpustack_worker_id", sa.String(128), nullable=True),
    )
    op.create_index(
        "ix_compute_resources_gpustack_worker_id",
        "compute_resources",
        ["gpustack_worker_id"],
    )
