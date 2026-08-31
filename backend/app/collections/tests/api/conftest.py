"""TestClient with the app's DB session overridden to in-memory SQLite --
same rationale as tests/persistence/conftest.py: fast, no docker compose
needed to run pytest."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import app.collections.models  # noqa: F401 -- registers collections_* tables
from app.api.deps import get_db
from app.main import app as fastapi_app


@pytest.fixture()
def client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def get_db_override() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = get_db_override
    yield TestClient(fastapi_app)
    fastapi_app.dependency_overrides.clear()
