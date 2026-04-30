"""Pytest configuration and fixtures for the backend test suite."""
import asyncio
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app

# Use SQLite for testing (in-memory, no PostgreSQL required for unit/integration tests)
TEST_DB_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop():
    """Session-scoped event loop."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database engine and tables."""
    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def test_db(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional test database session with rollback."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def async_client(test_db) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP test client with overridden DB dependency."""

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    app.dependency_overrides.clear()


# ---- Token fixtures ----

ADMIN_USER_ID = "user-admin-001"
RD_USER_ID = "user-rd-001"
QA_USER_ID = "user-qa-001"
PM_USER_ID = "user-pm-001"


@pytest.fixture
def admin_token() -> str:
    return create_access_token(
        user_id=ADMIN_USER_ID, role="Admin", partition_access=[]
    )


@pytest.fixture
def rd_token() -> str:
    return create_access_token(
        user_id=RD_USER_ID, role="RD", partition_access=["SWE", "HW"]
    )


@pytest.fixture
def qa_token() -> str:
    return create_access_token(
        user_id=QA_USER_ID,
        role="QA",
        partition_access=["SWE", "SYS", "HW", "Safety", "Security"],
    )


@pytest.fixture
def pm_token() -> str:
    return create_access_token(
        user_id=PM_USER_ID,
        role="PM",
        partition_access=["SWE", "SYS", "HW", "Safety", "Security"],
    )


# ---- Data fixtures ----

@pytest_asyncio.fixture
async def sample_project(test_db: AsyncSession):
    """Create a sample project in the test DB."""
    from app.models.project import Project

    project = Project(
        id=uuid.uuid4(),
        name=f"Test Project {uuid.uuid4().hex[:6]}",
        description="Test project description",
    )
    test_db.add(project)
    await test_db.flush()
    await test_db.refresh(project)
    return project


@pytest_asyncio.fixture
async def sample_partition(test_db: AsyncSession, sample_project):
    """Create a sample partition in the test DB."""
    from app.models.partition import Partition

    partition = Partition(
        id=uuid.uuid4(),
        project_id=sample_project.id,
        name="SWE",
        description="Software Engineering partition",
    )
    test_db.add(partition)
    await test_db.flush()
    await test_db.refresh(partition)
    return partition


@pytest_asyncio.fixture
async def sample_document(test_db: AsyncSession, sample_project, sample_partition):
    """Create a sample DRAFT document in the test DB."""
    from app.models.document import Document

    doc = Document(
        id=uuid.uuid4(),
        project_id=sample_project.id,
        partition_id=sample_partition.id,
        title="Test Document",
        content_md="# Test\n\nThis is a test document.",
        version="1.0",
        status="DRAFT",
        owner_id=RD_USER_ID,
        version_lock=1,
    )
    test_db.add(doc)
    await test_db.flush()
    await test_db.refresh(doc)
    return doc


@pytest_asyncio.fixture
async def sample_attribute_definition(test_db: AsyncSession):
    """Create a sample STRING attribute definition."""
    from app.models.attribute import AttributeDefinition

    attr = AttributeDefinition(
        id=uuid.uuid4(),
        name=f"Test_Attr_{uuid.uuid4().hex[:6]}",
        data_type="STRING",
        allowed_values=None,
        is_required=False,
    )
    test_db.add(attr)
    await test_db.flush()
    await test_db.refresh(attr)
    return attr


@pytest_asyncio.fixture
async def required_attribute_definition(test_db: AsyncSession):
    """Create a required ENUM attribute definition."""
    from app.models.attribute import AttributeDefinition

    attr = AttributeDefinition(
        id=uuid.uuid4(),
        name=f"Required_Attr_{uuid.uuid4().hex[:6]}",
        data_type="ENUM",
        allowed_values=["Option_A", "Option_B", "Option_C"],
        is_required=True,
    )
    test_db.add(attr)
    await test_db.flush()
    await test_db.refresh(attr)
    return attr
