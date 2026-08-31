"""In-memory SQLite session for persistence-layer tests.

Deliberately not Postgres: this suite tests `service.py`'s orchestration
logic and `models.py`'s table shape, not any Postgres-specific SQL
feature. SQLite in-memory keeps the test suite fast and dependency-free
(no docker compose required to run `pytest`); the real Postgres schema
is exercised via `alembic upgrade head` in CI/dev, and `alembic check`
(see docs/DEVELOPMENT.md) guards drift between `models.py` and the
committed migration.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import app.collections.models  # noqa: F401 -- registers collections_* tables on SQLModel.metadata


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session
