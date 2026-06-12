"""Initial schema — users, roles, permissions, ai_accounts, compute_resources, compute_resource_gpus, container_requests

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=True),
        sa.Column("department", sa.String(128), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_username", "users", ["username"])

    # ------------------------------------------------------------------
    # roles
    # ------------------------------------------------------------------
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # ------------------------------------------------------------------
    # permissions
    # ------------------------------------------------------------------
    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codename", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("resource_type", sa.String(32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codename"),
    )
    op.create_index("ix_permissions_resource_type", "permissions", ["resource_type"])

    # ------------------------------------------------------------------
    # user_role (m2m)
    # ------------------------------------------------------------------
    op.create_table(
        "user_role",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
    )

    # ------------------------------------------------------------------
    # role_permission (m2m)
    # ------------------------------------------------------------------
    op.create_table(
        "role_permission",
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )

    # ------------------------------------------------------------------
    # ai_accounts
    # ------------------------------------------------------------------
    op.create_table(
        "ai_accounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("account_name", sa.String(128), nullable=False),
        sa.Column("username", sa.Text(), nullable=True),
        sa.Column("password", sa.Text(), nullable=True),
        sa.Column("api_key", sa.Text(), nullable=True),
        sa.Column("cookie_data", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'active'")),
        sa.Column("expiration_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_error", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_accounts_platform", "ai_accounts", ["platform"])

    # ------------------------------------------------------------------
    # compute_resources
    # ------------------------------------------------------------------
    op.create_table(
        "compute_resources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("resource_type", sa.String(32), nullable=False),
        sa.Column("host_ip", sa.String(64), nullable=True),
        sa.Column("management_port", sa.Integer(), nullable=False, server_default=sa.text("22")),
        sa.Column("total_cpu_cores", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_memory_gb", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("total_disk_gb", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("available_cpu_cores", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("available_memory_gb", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("available_disk_gb", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'offline'")),
        sa.Column("ansible_group", sa.String(128), nullable=True),
        sa.Column("ansible_vars", sa.JSON(), nullable=True),
        sa.Column("gpustack_worker_id", sa.String(128), nullable=True),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_compute_resources_resource_type", "compute_resources", ["resource_type"])
    op.create_index("ix_compute_resources_gpustack_worker_id", "compute_resources", ["gpustack_worker_id"])

    # ------------------------------------------------------------------
    # compute_resource_gpus
    # ------------------------------------------------------------------
    op.create_table(
        "compute_resource_gpus",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=False),
        sa.Column("gpu_index", sa.Integer(), nullable=False),
        sa.Column("gpu_name", sa.String(128), nullable=True),
        sa.Column("gpu_uuid", sa.String(128), nullable=True),
        sa.Column("total_memory_mb", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("used_memory_mb", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("utilization_pct", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("temperature_c", sa.Float(), nullable=True),
        sa.Column("power_draw_w", sa.Float(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["resource_id"], ["compute_resources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_compute_resource_gpus_resource_id", "compute_resource_gpus", ["resource_id"])
    op.create_index("ix_compute_resource_gpus_recorded_at", "compute_resource_gpus", ["recorded_at"])

    # ------------------------------------------------------------------
    # container_requests
    # ------------------------------------------------------------------
    op.create_table(
        "container_requests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("compute_resource_id", sa.Integer(), nullable=True),
        sa.Column("request_type", sa.String(16), nullable=False),
        sa.Column("cpu_cores", sa.Integer(), nullable=False, server_default=sa.text("2")),
        sa.Column("memory_gb", sa.Float(), nullable=False, server_default=sa.text("4.0")),
        sa.Column("disk_gb", sa.Float(), nullable=False, server_default=sa.text("20.0")),
        sa.Column("gpu_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("gpu_memory_mb", sa.Integer(), nullable=True),
        sa.Column("exposed_ports", sa.JSON(), nullable=True),
        sa.Column("image_name", sa.String(255), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("container_id", sa.String(128), nullable=True),
        sa.Column("access_url", sa.String(255), nullable=True),
        sa.Column("access_credential", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["compute_resource_id"], ["compute_resources.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_container_requests_user_id", "container_requests", ["user_id"])
    op.create_index("ix_container_requests_compute_resource_id", "container_requests", ["compute_resource_id"])

    # ------------------------------------------------------------------
    # Seed default roles
    # ------------------------------------------------------------------
    op.execute("INSERT INTO roles (name, description, is_system) VALUES ('admin', 'System administrator — full access', true)")
    op.execute("INSERT INTO roles (name, description, is_system) VALUES ('operator', 'Operator — manage accounts & approve requests', true)")
    op.execute("INSERT INTO roles (name, description, is_system) VALUES ('viewer', 'Viewer — read-only dashboard access', true)")
    op.execute("INSERT INTO roles (name, description, is_system) VALUES ('user', 'Standard user — request resources, view own data', true)")

    # Seed default permissions
    perms = [
        ("accounts.read", "View AI account list", "accounts"),
        ("accounts.read_secret", "View decrypted account credentials", "accounts"),
        ("accounts.create", "Create AI accounts", "accounts"),
        ("accounts.update", "Update AI accounts", "accounts"),
        ("accounts.delete", "Delete AI accounts", "accounts"),
        ("compute.read", "View compute resources", "compute"),
        ("compute.manage", "Manage compute resources", "compute"),
        ("compute.request", "Request container/bare-metal access", "compute"),
        ("compute.approve", "Approve resource requests", "compute"),
        ("dashboard.view", "View dashboard", "dashboard"),
        ("admin.manage_users", "Manage users and roles", "admin"),
        ("admin.manage_roles", "Manage roles and permissions", "admin"),
    ]
    for codename, desc, rtype in perms:
        op.execute(
            f"INSERT INTO permissions (codename, description, resource_type) "
            f"VALUES ('{codename}', '{desc}', '{rtype}')"
        )

    # Assign all permissions to admin role
    op.execute(
        "INSERT INTO role_permission (role_id, permission_id) "
        "SELECT (SELECT id FROM roles WHERE name='admin'), id FROM permissions"
    )
    # Assign relevant permissions to operator
    op.execute(
        "INSERT INTO role_permission (role_id, permission_id) "
        "SELECT (SELECT id FROM roles WHERE name='operator'), id FROM permissions "
        "WHERE codename IN ('accounts.read', 'accounts.read_secret', 'accounts.create', 'accounts.update', "
        "'compute.read', 'compute.manage', 'compute.approve', 'dashboard.view')"
    )
    # Assign read-only permissions to viewer
    op.execute(
        "INSERT INTO role_permission (role_id, permission_id) "
        "SELECT (SELECT id FROM roles WHERE name='viewer'), id FROM permissions "
        "WHERE codename IN ('accounts.read', 'compute.read', 'dashboard.view')"
    )
    # Assign basic permissions to user
    op.execute(
        "INSERT INTO role_permission (role_id, permission_id) "
        "SELECT (SELECT id FROM roles WHERE name='user'), id FROM permissions "
        "WHERE codename IN ('compute.read', 'compute.request', 'dashboard.view')"
    )


def downgrade() -> None:
    op.drop_table("container_requests")
    op.drop_table("compute_resource_gpus")
    op.drop_table("compute_resources")
    op.drop_table("ai_accounts")
    op.drop_table("role_permission")
    op.drop_table("user_role")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("users")
