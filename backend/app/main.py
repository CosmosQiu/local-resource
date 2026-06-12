"""
FastAPI application factory.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    # Startup
    # TODO: init Redis pool, start background scheduler
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
