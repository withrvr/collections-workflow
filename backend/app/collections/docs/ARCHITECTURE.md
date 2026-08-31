# Architecture

Owns: components, data flow, why each decision was made, trade-offs, what
breaks at scale. Does not own: how to run anything (see `DEVELOPMENT.md`),
endpoint payloads (see `API.md`).

Status: **Phase 4 complete.** Populated phase by phase as components land.

## Components

- `contracts.py` (Phase 1): `Decimal`/`date`-typed canonical records.
- `ingest/` (Phase 1): workbook -> `CanonicalDataset`, exact-match column
  resolution, `SheetMissingError`/`ColumnResolutionError`.
- `validate/` (Phase 2): the 14-rule exception catalogue (`docs/RULES.md`).
- `calculate/` (Phase 1): outstanding, overdue, region, ageing.
- `errors.py` (Phase 3): `PipelineError`, the single error contract every
  user-facing run failure maps to.
- `models.py` (Phase 3): `Run`, `RunEvent`, `RunException`,
  `RunInvoicePosition` — see "Data flow" and "The error contract" below.
- `observability/events.py` (Phase 3): writes `run_events`, the user-facing
  timeline. `observability/logging.py` is the separate developer-facing
  channel (stdlib `logging` for now; Phase 12 upgrades it to structlog
  JSON once there's a real consumer for it).
- `service.py` (Phase 3): `execute_run`, the orchestrator.
- `api/` (Phase 4): six routers (`runs`, `overdue`, `exceptions`,
  `regions`, `summary`, `run-log`) mounted under `/collections`, plus
  `schemas.py` (Pydantic response models, separate from `models.py`'s
  SQLModel tables) and `deps.py` (`get_run_or_404`). No auth — this is
  an internal ops tool, not a multi-tenant product, and MASTER_PLAN.md
  never asks for one.
- `control/`, `ai/`, `export/` (Phase 5+): not yet populated.

## Why `validate/schemas.py` is not Pandera

MASTER_PLAN.md section 9 names Pandera for Phase 2's "structural schemas."
We deliberately did not add it, and the reasoning belongs here rather than
silently deviating from the plan.

Pandera validates DataFrame-shaped data (`DataFrameSchema`/
`DataFrameModel`). This codebase has no DataFrame anywhere: `ingest/loader.py`
reads typed openpyxl cells straight into frozen dataclasses (`contracts.py`)
specifically to avoid a second, looser numeric-parsing path — the same
reasoning the anydoc boundary above uses (a DataFrame-inferred dtype for a
money column carries exactly the same "lost precision and type" risk as a
parsed Markdown cell).

By the time any `validate/rules.py` function receives a `CanonicalDataset`,
there is no dtype-mismatch state left for Pandera to catch:

- Required-sheet/required-column presence is already enforced by
  `ingest/resolver.py`'s `ColumnResolutionError`.
- Per-cell type coercion (string -> `Decimal`, string -> `date`) already
  happens in `ingest/loader.py`'s `_decimal`/`_date`/etc. helpers, which
  raise immediately on a bad cell — arguably stricter than a post-hoc
  DataFrame dtype check, since it operates on the real openpyxl typed
  value rather than an inferred column dtype.
- Empty sheet / corrupt file / missing sheet are pipeline **failures**
  (`PipelineError`, see "The error contract" below), not per-row
  exceptions — out of scope for a structural-schema layer regardless of
  which library implements it.

Adding `pandas`/Pandera here would mean building a throwaway DataFrame
just to re-check a guarantee the type system already gives, plus a new
runtime dependency and a second numeric-parsing code path for money.
Instead, `validate/schemas.py` holds `SheetSchema` constants — a
declarative, dependency-free single source of truth re-exporting
`ingest/resolver.py`'s existing header dicts — plus `sheet_row_counts()`.
If ingestion ever moves to a DataFrame-based pipeline, Pandera would be
the natural upgrade at that point.

## Data flow

`service.execute_run` is a plain function calling each stage in a fixed
order — deliberately not an autonomous agent (see QA_PREP.md question 16).
`models.EventStage` names all seven stages the design settles on —
`load`, `map`, `validate`, `calculate`, `control`, `summarise`, `persist`
— so the catalogue's shape does not change again as later phases fill it
in, but Phase 3 only implements four of them:

```
load -> validate -> calculate -> persist
```

`map` (Phase 10, multi-workbook column mapping) and `control`/`summarise`
(Phase 5-6, the exception-rate gate and the deterministic/LLM summary)
are named but not called yet — every Phase 3 run either completes after
`calculate` or fails at whichever of the four stages raised.

Every stage writes a `run_events` row before/after its work
(`observability/events.py`). A `Run` is always a real, queryable row --
`POST /run` (Phase 4) never has to catch an exception out of the
orchestrator, because `execute_run` never raises; it returns a `Run`
whose `status` is `COMPLETED` or `FAILED`.

## The error contract

Every failure a user's uploaded file can cause is a `PipelineError`
(`errors.py`): `code` (stable, machine-readable — `SHEET_MISSING`,
`SHEET_COLUMN_MISSING`, `FILE_CORRUPT`, `ROW_DATA_INVALID`), `stage`
(which of the four stages raised it), `user_message` (written for a
finance person, never containing a raw Python exception's text), and
`detail` (structured context for the event's expandable detail, not a
substitute for `user_message`).

`service._load_dataset` is the only place that translates a raw
exception into a `PipelineError` — `SheetMissingError` /
`ColumnResolutionError` (both `ingest/resolver.py`, distinct so a wholly
absent sheet reads differently from a present sheet missing columns),
`BadZipFile`/`InvalidFileException` (not a real xlsx file), and a bare
`ValueError` (a cell `loader.py`'s own `_decimal`/`_date` helpers could
not parse — e.g. text in a money column). Anything else — a genuine bug
in this code, not a bad input file — is caught by `execute_run`'s final
`except Exception`, logged with a full traceback via
`observability/logging.py` (the developer channel), and surfaces to the
user as a single generic `UNEXPECTED_ERROR` event, never the traceback
itself.

## Why run status and run_events are plain strings, not enums

`models.Run.status` and `RunEvent.stage`/`level` are indexed `str`
columns, not Postgres native `ENUM` types or a SQLAlchemy `CHECK`
constraint. A later phase (Phase 5 adds `PASSED`/`BLOCKED` alongside
`COMPLETED`) growing this catalogue would need `ALTER TYPE ... ADD
VALUE` for a native enum — awkward mid-transaction on some Postgres
versions — or a migration to widen a `CHECK` constraint. A plain string
column, kept in sync with the `RunStatus`/`EventStage`/`EventLevel`
`Literal` aliases in `models.py`, never needs a migration just because
the catalogue grew.

## Persistence: SQL crosscheck, not just Python round-trip

`RunInvoicePosition` persists every eligible invoice position (Phase 1's
`compute_positions`, not just the overdue subset), and
`tests/persistence/test_sql_crosscheck.py` aggregates it back out with a
SQL `SUM`/`GROUP BY` — a genuinely independent code path from the
in-memory `calculate/` functions `scripts/reference_summary.py` uses.
Agreement between the two (15 overdue invoices, ₹12,02,000, West
heaviest) is real evidence the persistence layer is not silently
dropping or double-counting a row, not the same arithmetic checked twice.

## The anydoc boundary

A hard rule, stated here explicitly because it is the kind of distinction
that reads as senior in review: anydoc converts workbooks to Markdown for
LLM context ONLY. Numbers for calculation always come from `openpyxl`
reading typed cells into `Decimal`, never from parsing a Markdown table
cell, which is a formatted string that has already lost precision and
type.

```
ALLOWED   workbook -> anydoc -> markdown -> LLM context
BANNED    workbook -> anydoc -> markdown -> parse -> financial calculation
```

## Trade-offs and what breaks at scale

_Filled in as decisions are made; see QA_PREP.md question 20 for the
production-hardening answer this section will expand on._
