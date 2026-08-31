# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2026-08-31

### Added

- `api/schemas.py`: Pydantic response models (`RunOut`, `RunEventOut`,
  `ExceptionOut`, `InvoicePositionOut`, `RegionBreakdownOut`,
  `SummaryOut`), separate from `models.py`'s SQLModel tables.
- `api/deps.py`: `get_run_or_404`, shared by every report endpoint.
- `api/runs.py`: `POST /collections/runs/` (upload a workbook, run the
  pipeline synchronously, always `200` with a `Run` — never `500` on a
  bad file), `GET /collections/runs/` (list), `GET /collections/runs/{id}`.
- `api/overdue.py`: `GET /collections/overdue/?run_id=`.
- `api/exceptions.py`: `GET /collections/exceptions/?run_id=&rule_code=&severity=`.
- `api/regions.py`: `GET /collections/regions/?run_id=`, and
  `region_breakdown()` shared with `api/summary.py`.
- `api/summary.py`: `GET /collections/summary/?run_id=` — numeric
  summary plus region breakdown; Phase 5 adds the control gate on top.
- `api/runlog.py`: `GET /collections/run-log/{run_id}/events`.
- 10 new tests (122 -> 132): `tests/api/test_api.py`, the full flow a
  reviewer would drive from `/docs`, against dataset A, plus a broken
  upload asserting `200`/`FAILED` rather than `500`.

## [0.4.0] - 2026-08-31

### Added

- `errors.py`: `PipelineError`, the typed error contract every
  user-facing run failure maps to (`code`, `stage`, `user_message`,
  `detail`) — never a raw traceback.
- `models.py`: SQLModel tables `Run`, `RunEvent`, `RunException`,
  `RunInvoicePosition` (prefixed `collections_*`). `status`/`stage`/
  `level` are plain indexed strings, not native Postgres enums, so a
  later phase can add a value without a migration.
- `observability/events.py`: `emit()`, writing the `run_events` timeline;
  `to_json_detail()` converts `Decimal`/`date` values for the JSON
  column. `observability/logging.py`: the separate developer-facing
  channel (stdlib `logging` for now, Phase 12 upgrades to structlog).
- `service.py`: `execute_run`, the orchestrator — load, validate,
  calculate, persist, each stage emitting `run_events`. Always returns a
  `Run`, `COMPLETED` or `FAILED`, never raises.
- `ingest/resolver.py`: `SheetMissingError`, distinct from
  `ColumnResolutionError` so a wholly absent sheet reads differently
  from a present sheet missing columns.
- Alembic migration `3c6653dbe726` (baseline `fe56fa70289e` applied
  first): the four `collections_*` tables and their indexes.
  `compose.override.yml`'s dev `backend` command now runs
  `alembic upgrade head` before `fastapi dev`.
- Test suite additions (15 new tests, 122 total):
  `tests/persistence/test_service.py` (run lifecycle, five deliberately
  broken workbooks each asserted to a specific `error_code` and a
  traceback-free `error_message`), `tests/persistence/test_sql_crosscheck.py`
  (the independently-derived SQL recompute MASTER_PLAN.md section 10
  asks for — a SQL `SUM`/`GROUP BY` over persisted `RunInvoicePosition`
  rows checked against the same reference numbers), `tests/test_errors.py`,
  and a `SheetMissingError` test in `tests/ingest/test_loader.py`.
  `tests/ingest/workbook_builder.py`: minimal in-memory workbook builder
  for the failure-path tests. `tests/persistence/conftest.py`: in-memory
  SQLite `session` fixture — fast, no docker compose needed to run
  `pytest`; the real Postgres schema is exercised via
  `alembic upgrade head` and guarded against drift by `alembic check`.

### Fixed

- `frontend/src/routeTree.gen.ts` was stale (the `collections/*.tsx`
  route files existed but the generated route tree was never refreshed),
  breaking the backend's Docker build (the frontend builds into the
  backend image as a build stage). Regenerated.

## [0.3.0] - 2026-08-31

### Added

- `contracts.py`: `ExceptionRow` (rule code, category, plain-English
  message, severity, natural keys, native-typed detail dict).
- `validate/schemas.py`: declarative `SheetSchema` structural constants
  and `sheet_row_counts()` — deliberately not Pandera; reasoning in
  `docs/ARCHITECTURE.md`.
- `validate/engine.py`: registry-driven rule runner (`RULE_REGISTRY`,
  `run_all_rules`, `exceptions_by_rule`).
- `validate/rules.py`: all 14 exception rules (E001-E014) — missing due
  date, unknown customer/invoice references, non-positive invoice/payment
  amounts, invalid/missing GSTIN, payment-to-invoice customer mismatch,
  payment after report date, payment before invoice date, Cancelled/Credit
  Note status, duplicate source system reference, and overpayment (E014,
  added beyond the assessment's required list).
- `docs/RULES.md`: complete 14-rule catalogue, one entry per code, with
  condition, dataset A trigger, exclusion behavior, and rationale.
- Test suite additions under `backend/app/collections/tests/` (65 new
  tests, 107 total): one file per rule with a dataset-A positive case
  plus hand-built negative/boundary cases; `tests/validate/factories.py`
  shared record builders; `tests/validate/test_coverage.py` (every rule
  fires on dataset A, registry covers exactly E001-E014); two
  reconciliation identities in `tests/test_reconcile.py` proving no
  invoice or payment rupee is lost.

### Fixed

- `QA_PREP.md` Q20's answer, which claimed Pandera was already in use for
  structural checks — corrected to match the actual Phase 2 design
  decision.

## [0.2.0] - 2026-08-31

### Added

- `backend/app/collections/fixtures/dataset_a_original.xlsx`: the given
  assessment workbook, committed as a reproducible fixture.
- `openpyxl` runtime dependency for reading xlsx workbooks with typed cells.
- `contracts.py`: Decimal/date-typed canonical dataclasses (`CanonicalCustomer`,
  `CanonicalInvoice`, `CanonicalPayment`, `RegionMap`, `CanonicalDataset`).
- `ingest/resolver.py`: tier-1 exact-match column resolution.
- `ingest/loader.py`: workbook -> `CanonicalDataset` via openpyxl, no pandas.
- `calculate/outstanding.py`, `calculate/overdue.py`, `calculate/regions.py`,
  `calculate/ageing.py`: pure calculation functions for outstanding,
  overdue, region breakdown, and ageing buckets.
- `scripts/reference_summary.py`: prints the reference numbers (15 overdue
  invoices, ₹12,02,000 total outstanding, West heaviest) against dataset A.
- Test suite under `backend/app/collections/tests/` (42 tests): loader,
  resolver, calculator boundary tests, and a reference-number regression
  test.

## [0.1.0] - 2026-08-31

### Added

- Repo bootstrapped from `fastapi/full-stack-fastapi-template` (unmodified
  base commit).
- `backend/app/collections/` package skeleton: `ingest/`, `validate/`,
  `calculate/`, `control/`, `ai/roles/`, `export/`, `observability/`,
  `api/`, `docs/`, `fixtures/`, `tests/`, plus `contracts.py`,
  `config.py` (with `REPORT_DATE` as config, never `datetime.now()`),
  `models.py`, `service.py`, `scheduler.py`.
- Collections API router wired into `backend/app/api/main.py` under
  `/api/v1/collections` (stub sub-routers: runs, overdue, exceptions,
  regions, summary, run-log, mappings).
- `frontend/src/routes/collections/` route stubs: runs, run-detail,
  exceptions, summary, upload, mapping.
- Documentation skeleton: service `README.md` and `docs/ARCHITECTURE.md`,
  `docs/API.md`, `docs/RULES.md`, `docs/DEVELOPMENT.md`, `docs/DEMO.md`.
- `AGENTS.md` standing build instructions and
  `.github/pull_request_template.md` at the repo root.
