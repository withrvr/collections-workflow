"""SQLModel tables for runs, run events, exceptions and invoice positions.

Built in Phase 3 (MASTER_PLAN.md). Table names are prefixed `collections_`
so they read unambiguously next to the template's own `user`/`item`
tables in the same database and in Adminer's table list.

`status` and `run_event.stage`/`level` are plain indexed strings, not
Postgres native ENUM columns. A native enum needs `ALTER TYPE ... ADD
VALUE` (which cannot run inside the same transaction as other DDL on
some Postgres versions) every time a later phase adds a value -- Phase 5
adds `PASSED`/`BLOCKED` run statuses, Phase 10 may add stages. A CHECK
constraint would fight autogenerate the same way. Plain strings, kept
in sync with the `RunStatus`/`EventStage`/`EventLevel` Literal aliases
below, are the boring choice that does not require a migration every
time this catalogue grows -- see docs/ARCHITECTURE.md.

`detail_json` columns hold `ExceptionRow.detail`/`PipelineError.detail`,
which carry native Decimal/date values (see contracts.py) -- never
JSON-serializable as-is. `observability/events.py` and `service.py`
convert through `to_json_detail()` before assigning here; nothing in
this module performs that conversion itself.
"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Literal

from sqlalchemy import JSON, Column, DateTime, Numeric
from sqlmodel import Field, Relationship, SQLModel

RunStatus = Literal["PENDING", "RUNNING", "COMPLETED", "FAILED"]
EventStage = Literal["load", "validate", "calculate", "control", "summarise", "persist"]
EventLevel = Literal["info", "warning", "error"]

MONEY = Numeric(18, 2)


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


class Run(SQLModel, table=True):
    """One execution of the pipeline against one uploaded workbook."""

    __tablename__ = "collections_run"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    status: str = Field(default="PENDING", index=True, max_length=16)
    source_filename: str = Field(max_length=255)
    report_date: date
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )
    completed_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )

    # Set only when status == "FAILED".
    error_code: str | None = Field(default=None, max_length=64)
    error_message: str | None = None

    # Set only when status == "COMPLETED". Denormalized run-level totals so
    # the runs list (Phase 4) never has to aggregate the child tables.
    customer_count: int | None = None
    invoice_count: int | None = None
    payment_count: int | None = None
    overdue_count: int | None = None
    total_outstanding: Decimal | None = Field(default=None, sa_type=MONEY)  # type: ignore[call-overload]
    exception_count: int | None = None

    events: list[RunEvent] = Relationship(back_populates="run", cascade_delete=True)
    exceptions: list[RunException] = Relationship(
        back_populates="run", cascade_delete=True
    )
    invoice_positions: list[RunInvoicePosition] = Relationship(
        back_populates="run", cascade_delete=True
    )


class RunEvent(SQLModel, table=True):
    """The user-visible run timeline (docs/RULES.md's sibling for run
    lifecycle rather than data quality). See observability/events.py."""

    __tablename__ = "collections_run_event"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    run_id: uuid.UUID = Field(
        foreign_key="collections_run.id", nullable=False, ondelete="CASCADE", index=True
    )
    ts: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )
    stage: str = Field(max_length=16, index=True)
    level: str = Field(max_length=8, index=True)
    code: str = Field(max_length=64)
    message: str
    detail_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))

    run: Run | None = Relationship(back_populates="events")


class RunException(SQLModel, table=True):
    """One persisted `contracts.ExceptionRow`, tied to the run that found it."""

    __tablename__ = "collections_run_exception"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    run_id: uuid.UUID = Field(
        foreign_key="collections_run.id", nullable=False, ondelete="CASCADE", index=True
    )
    rule_code: str = Field(max_length=8, index=True)
    category: str = Field(max_length=64)
    message: str
    severity: str = Field(max_length=16)
    invoice_id: str | None = Field(default=None, max_length=64, index=True)
    payment_id: str | None = Field(default=None, max_length=64, index=True)
    customer_id: str | None = Field(default=None, max_length=64, index=True)
    detail_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))

    run: Run | None = Relationship(back_populates="exceptions")


class RunInvoicePosition(SQLModel, table=True):
    """One persisted `calculate.overdue.InvoicePosition`, tied to its run.

    Covers every eligible invoice (overdue and current alike, matching
    `compute_positions`), not only overdue ones, so a future ageing/regions
    read can filter in SQL instead of recomputing in Python.
    """

    __tablename__ = "collections_run_invoice_position"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    run_id: uuid.UUID = Field(
        foreign_key="collections_run.id", nullable=False, ondelete="CASCADE", index=True
    )
    invoice_id: str = Field(max_length=64, index=True)
    customer_id: str = Field(max_length=64, index=True)
    region: str | None = Field(default=None, max_length=64, index=True)
    due_date: date | None = None
    outstanding: Decimal = Field(sa_type=MONEY)  # type: ignore[call-overload]
    is_overdue: bool = Field(index=True)
    days_overdue: int
    ageing_bucket: str | None = Field(default=None, max_length=8)

    run: Run | None = Relationship(back_populates="invoice_positions")
