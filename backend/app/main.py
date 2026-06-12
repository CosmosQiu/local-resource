"""
FastAPI application factory.
"""
import logging
import secrets
import string
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

logger = logging.getLogger("uvicorn")


# ---------------------------------------------------------------------------
# Default admin bootstrap
# ---------------------------------------------------------------------------
def _generate_admin_password(length: int = 16) -> str:
    """Generate a secure random password for the default admin account."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def _bootstrap_admin() -> None:
    """Create a default admin user (username=admin) if one does not exist.

    The password is randomly generated and written to the application log.
    The admin role (with all permissions) is assigned automatically.
    """
    from sqlalchemy import select

    from app.core.database import async_session
    from app.core.security import hash_password
    from app.models.user import Role, User

    async with async_session() as db:
        result = await db.execute(select(User).where(User.username == "admin"))
        if result.scalar_one_or_none() is not None:
            return  # already exists — nothing to do

        password = _generate_admin_password()

        admin_user = User(
            username="admin",
            email="admin@localhost",
            hashed_password=hash_password(password),
            display_name="System Admin",
            is_superuser=True,
            is_active=True,
        )

        # Assign the seeded "admin" role
        role_result = await db.execute(select(Role).where(Role.name == "admin"))
        admin_role = role_result.scalar_one_or_none()
        if admin_role:
            admin_user.roles.append(admin_role)

        db.add(admin_user)
        await db.commit()

        logger.warning("=" * 60)
        logger.warning("  DEFAULT ADMIN ACCOUNT CREATED")
        logger.warning("  Username : admin")
        logger.warning("  Password : %s", password)
        logger.warning("  ⚠  CHANGE THIS PASSWORD IMMEDIATELY!")
        logger.warning("=" * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    # Startup
    # TODO: init Redis pool, start background scheduler
    await _bootstrap_admin()
    yield
    # Shutdown
    # TODO: close Redis pool, stop scheduler


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — allow frontend dev server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------
    @app.get("/api/health", tags=["System"])
    async def health_check():
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "env": settings.APP_ENV,
        }

    # ------------------------------------------------------------------
    # Routers
    # ------------------------------------------------------------------
    from app.api.auth.router import router as auth_router
    from app.api.accounts.router import router as accounts_router
    from app.api.dashboard.router import router as dashboard_router
    from app.api.compute.router import router as compute_router
    from app.api.compute.requests import router as requests_router
    from app.api.admin.router import router as admin_router

    app.include_router(auth_router, prefix="/api/auth")
    app.include_router(accounts_router, prefix="/api/accounts")
    app.include_router(dashboard_router, prefix="/api/dashboard")
    app.include_router(compute_router, prefix="/api/compute")
    app.include_router(requests_router, prefix="/api/compute")
    app.include_router(admin_router, prefix="/api/admin")

    return app


app = create_app()
