"""Shared test fixtures for backend tests."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Generator
import json
import enum

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.dialects.postgresql import ARRAY, ENUM, JSONB, TSVECTOR, UUID as PGUUID
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool

from app.domains.news import NewsFacade
from app.main import app as fastapi_app
from app.core.database import get_db
from app.models import Base, User
from app.api.dependencies import get_current_user
import uuid


SQLITE_TEST_URL = "sqlite+aiosqlite:///:memory:"


@compiles(PGUUID, "sqlite")
def compile_uuid(element, compiler, **kw):  # type: ignore[override]
    return "CHAR(36)"


@compiles(ENUM, "sqlite")
def compile_enum(element, compiler, **kw):  # type: ignore[override]
    # emulate enum via TEXT in SQLite
    return "VARCHAR"


@compiles(TSVECTOR, "sqlite")
def compile_tsvector(element, compiler, **kw):  # type: ignore[override]
    return "TEXT"


@compiles(ARRAY, "sqlite")
def compile_array(element, compiler, **kw):  # type: ignore[override]
    # represent PostgreSQL ARRAY columns as TEXT for SQLite tests
    return "TEXT"


@compiles(JSONB, "sqlite")
def compile_jsonb(element, compiler, **kw):  # type: ignore[override]
    return "TEXT"

_ARRAY_ORIGINAL_BIND = ARRAY.bind_processor
_ARRAY_ORIGINAL_RESULT = ARRAY.result_processor


def _coerce_array_item_for_sqlite(item_type, value):
    if value is None:
        return None
    if hasattr(item_type, "python_type"):
        try:
            python_type = item_type.python_type
        except NotImplementedError:
            python_type = None
    else:
        python_type = None

    if python_type is not None:
        import uuid

        if python_type.__name__ == "UUID" or python_type is uuid.UUID:
            return str(value)
        try:
            if issubclass(python_type, enum.Enum):  # type: ignore[arg-type]
                return value.value if hasattr(value, "value") else str(value)
        except Exception:
            pass

    if hasattr(value, "value"):
        return value.value
    if isinstance(value, enum.Enum):
        return value.value
    return value


def _restore_array_item_from_sqlite(item_type, value):
    if value is None:
        return None

    if hasattr(item_type, "python_type"):
        try:
            python_type = item_type.python_type
        except NotImplementedError:
            python_type = None
    else:
        python_type = None

    if python_type is None:
        return value

    try:
        import uuid

        if python_type.__name__ == "UUID" or python_type is uuid.UUID:
            return python_type(str(value))
        if issubclass(python_type, enum.Enum):  # type: ignore[arg-type]
            return python_type(value)
        return python_type(value)
    except Exception:
        return value


def _sqlite_array_bind(self, dialect):
    if dialect.name != "sqlite":
        return _ARRAY_ORIGINAL_BIND(self, dialect)

    item_type = getattr(self, "item_type", None)

    def process(value):
        if value is None:
            return None
        coerced = []
        for element in value:
            coerced.append(_coerce_array_item_for_sqlite(item_type, element))
        return json.dumps(coerced)

    return process


def _sqlite_array_result(self, dialect, coltype):
    if dialect.name != "sqlite":
        return _ARRAY_ORIGINAL_RESULT(self, dialect, coltype)

    item_type = getattr(self, "item_type", None)

    def process(value):
        if value is None:
            return []
        raw = value
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                raw = [raw]
        if not isinstance(raw, (list, tuple)):
            raw = [raw]
        restored = []
        for element in raw:
            restored.append(_restore_array_item_from_sqlite(item_type, element))
        return restored

    return process


ARRAY.bind_processor = _sqlite_array_bind  # type: ignore[assignment]
ARRAY.result_processor = _sqlite_array_result  # type: ignore[assignment]

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the whole test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def async_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Provide a session-scoped async engine backed by in-memory SQLite."""
    engine = create_async_engine(
        SQLITE_TEST_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def async_session_factory(
    async_engine: AsyncEngine,
) -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    """Provide an async session factory bound to the test engine."""
    factory = async_sessionmaker(
        async_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    yield factory


@pytest_asyncio.fixture
async def async_session(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Yield an AsyncSession and ensure rollback between tests."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest_asyncio.fixture
async def news_facade(async_session: AsyncSession) -> AsyncGenerator[NewsFacade, None]:
    """Shortcut fixture to interact with the news domain facade."""
    yield NewsFacade(async_session)


@pytest_asyncio.fixture
async def test_app(async_session: AsyncSession) -> AsyncGenerator[FastAPI, None]:
    """Provide FastAPI app with dependency overrides bound to test session."""

    test_user = User(
        email=f"test-{uuid.uuid4()}@example.com",
        password_hash="not-used",
        is_active=True,
    )
    async_session.add(test_user)
    await async_session.commit()
    await async_session.refresh(test_user)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield async_session

    async def override_get_current_user() -> User:
        return test_user

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_current_user] = override_get_current_user

    yield fastapi_app

    fastapi_app.dependency_overrides.pop(get_db, None)
    fastapi_app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def async_client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """HTTPX async client bound to the FastAPI app."""
    async with AsyncClient(app=test_app, base_url="http://testserver") as client:
        yield client

