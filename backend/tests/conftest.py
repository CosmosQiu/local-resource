"""
Test fixtures — each test gets a fresh SQLite in-memory database.
"""
import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

TEST_DATABASE_URL = "sqlite+aiosqlite://"

# Ensure models are registered early
import app.models  # noqa: E402, F401


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    from app.core.database import Base
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_engine):
    from app.main import app

    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    app.dependency_overrides.clear()

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    from app.core.database import get_db
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session):
    from app.core.security import hash_password
    from app.models.user import User, Role
    from sqlalchemy import select as sa_select

    role_result = await db_session.execute(sa_select(Role).where(Role.name == "user"))
    role = role_result.scalar_one_or_none()
    if not role:
        role = Role(name="user", description="Standard user")
        db_session.add(role)
        await db_session.flush()

    user = User(
        username="testuser", email="test@example.com",
        hashed_password=hash_password("password123"),
        display_name="Test User", is_active=True,
    )
    user.roles.append(role)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session):
    from app.core.security import hash_password
    from app.models.user import User, Role, Permission

    role = Role(name="admin", description="Admin role for test")
    db_session.add(role)
    await db_session.flush()

    perms_data = [
        ("accounts.read", "accounts"), ("accounts.read_secret", "accounts"),
        ("accounts.create", "accounts"), ("accounts.update", "accounts"),
        ("accounts.delete", "accounts"),
        ("compute.read", "compute"), ("compute.manage", "compute"),
        ("compute.request", "compute"), ("compute.approve", "compute"),
        ("dashboard.view", "dashboard"),
        ("admin.manage_users", "admin"), ("admin.manage_roles", "admin"),
    ]
    for codename, rtype in perms_data:
        perm = Permission(codename=codename, resource_type=rtype)
        db_session.add(perm)
        role.permissions.append(perm)

    user = User(
        username="admin", email="admin@example.com",
        hashed_password=hash_password("admin123"),
        display_name="Admin", is_active=True, is_superuser=True,
    )
    user.roles.append(role)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user
