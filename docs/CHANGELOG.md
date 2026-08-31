# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Per-run file storage: every upload is kept on disk
  (`/tmp/collections-uploads/`) and downloadable via
  `GET /collections/runs/{id}/download`; `RunOut.has_download` and a
  download link/icon expose it in the UI (runs list, run-detail).
- `report_date` is now a user-overridable form field on
  `POST /collections/runs` (default 2026-07-31, validated ISO date,
  422 on malformed input) instead of a fixed setting -- both Postman
  and the upload page (native `<input type="date">`) can drive it.
- `POST /collections/runs/{id}/send-email`: emails a run's summary
  (status, stats, narrative) via the existing SMTP/Mailpit setup;
  503 if email isn't configured, 409 if the run hasn't finished.
- Pagination on `/collections/runs` (`GET .../runs?skip=&limit=`,
  frontend `?page=` search param, 20/page).
- Public (no-auth) root dashboard at `/`: KPI cards, an outstanding-
  by-run bar chart and a run-outcomes pie chart (Recharts), recent
  runs list, nav into upload/runs.
- `backend/app/collections/scripts/make_manual_test_files.py`: writes
  6 `.xlsx` cases (clean pass, blocked, missing sheet, missing column,
  corrupt, empty) to a local gitignored `test-files/` folder for
  manual Postman/UI testing.

### Changed

- AI summary narrative (both the Ollama prompt and the deterministic
  fallback) rewritten to be substantially longer and more analytical:
  region breakdown, ageing-bucket breakdown, top exception rules by
  count, not just a one-line total.
- `ExceptionsPanel` rebuilt from a `<table>` to a card layout -- a
  table forces every cell in a column to share one width, which is
  what caused the reported overlapping/horizontal-scroll bug on the
  exceptions page; cards let cause/impact/fix text wrap at full width
  instead. Hover `title` tooltips added throughout (severity badges,
  truncated filenames, monetary values, region cells).
- Full rebrand off the FastAPI template identity: new SVG logo, page
  title/favicon, footer, and route titles all say "Collections
  Workflow"; `FASTAPI.md`/`FASTAPI-release-notes.md` removed.
- Upload page: native HTML5 drag-and-drop added to the existing
  dropzone.

- `postman/`: a full Postman collection (13 requests) plus two
  environments (local Docker, public ngrok tunnel) -- verified against
  the live backend via Newman, 25 assertions, 0 failures. Covers the
  whole flow (upload -> timeline -> overdue/exceptions/regions/summary)
  plus the error contract (a real garbage-file fixture proving
  `FAILED`-never-`500`, an unknown-id 404). Test scripts chain
  `run_id` automatically between requests.
- `frontend`: `run-detail` is now the one-screen automated view --
  timeline, summary (block/pass banner, AI narrative, region
  breakdown), and the first 10 exceptions (cause/impact/fix/owner,
  expandable inline) all render on the same page a successful upload
  lands on, no further clicks required. `exceptions.tsx`/`summary.tsx`
  now render off shared `ExceptionsPanel`/`SummaryPanel` components
  also embedded in `run-detail` -- one implementation, not two copies.

## [0.9.0] - 2026-08-31

**Submission scope (MASTER_PLAN.md Phases 0-8) complete.**

### Added

- `frontend/src/routes/collections/`: five routes -- `upload`, `runs`,
  `run-detail`, `exceptions`, `summary`. No auth, matching the API.
  Template's own shadcn/ui components throughout, no new UI library.
- `frontend/src/components/Collections/`: `CollectionsNav` (shared
  header, not a router-level layout), `StatusBadge`
  (PASSED/BLOCKED/FAILED/RUNNING/PENDING color coding).
- `run-detail` groups `run_events` by stage into a colored timeline
  (green/amber/red by worst level in the group -- MASTER_PLAN.md
  section 7's exact design), expandable per stage to the raw events.
- `exceptions` joins each row's Phase 7 explanation inline
  (cause/impact/suggested-fix/owner), filterable by severity.
- `summary` renders the full "blocked payload" (`SummaryOut`) plus a
  badge naming which of the three LLM rungs produced the narrative.
- Frontend client regenerated (`scripts/generate-client.sh`) to include
  `CollectionsService` against the current OpenAPI schema.
- Verified end to end in a real, unmocked headless Chromium against the
  actual Docker-served app (not just a `tsc`/`vite build` pass) --
  upload, run-detail, exceptions, and summary all render correctly with
  zero console errors, for both a `BLOCKED` (dataset A) and a `PASSED`
  (dataset B) run. No automated Playwright suite committed yet.

## [0.8.0] - 2026-08-31

### Added

- `ai/guard.py`: `ids_are_contained` -- an LLM explanation naming a
  record ID outside its own batch is rejected outright.
- `ai/roles/exception_explainer.py`: `explain_rules`, batched by rule
  code (one explanation per distinct `rule_code`, not per row -- the 14
  rules are a fixed catalogue). Same three-rung fallback as
  `summary_narrator`; `RULE_METADATA` is the deterministic third rung,
  in the same words `docs/RULES.md`'s own "Why" prose already
  establishes. `auto_fixable` hardcoded `False` on every
  `RuleExplanation`, every rung, no exceptions. Cached per
  `(rule_code, category, sorted affected IDs)`.
- `models.py`: `RunRuleExplanation`, one row per `(run, rule_code)`.
- `service.py`: `validate` stage now also calls `explain_rules` and
  persists the results.
- `api/exceptions.py`, `api/schemas.py`: `ExceptionOut` gains
  `cause`/`impact`/`suggested_fix`/`owner`/`auto_fixable`/
  `explanation_source`, joined from `RunRuleExplanation` by `rule_code`.
- 8 new tests (154 -> 162): `tests/ai/test_exception_explainer.py`
  (every fired rule explained, `auto_fixable` always `False`, fallback
  reproduces `RULE_METADATA`, no invented IDs against real Ollama) and
  `ids_are_contained` cases added to `tests/ai/test_guard.py`.

## [0.7.0] - 2026-08-31

### Added

- `ai/provider.py`: `call_ollama`/`call_cloud`, the LiteLLM seam --
  local Ollama (`phi4-mini`) by default; a cloud model only if
  `COLLECTIONS_CLOUD_LLM_MODEL` is explicitly set, never required.
- `ai/guard.py`: `numbers_are_contained`, the post-generation numeric
  containment check -- an LLM output containing a number never given to
  it is rejected outright.
- `ai/roles/summary_narrator.py`: `narrate()`, the three-rung fallback
  chain (Ollama -> cloud -> deterministic template) for the run
  narrative, numeric-guarded at every rung, never raises.
- `ai/context.py`: `workbook_readme_markdown`, anydoc workbook-to-Markdown
  conversion for LLM context only -- not consumed by any Phase 6 role
  yet; ready for Phase 7/10.
- `observability/metrics.py`: `llm_calls_total`, a plain in-process
  counter -- Phase 6's done-when ("llm_calls_total shows local calls
  succeeding"), formalized to real Prometheus in Phase 12.
- `config.py`: `OLLAMA_API_BASE`/`OLLAMA_MODEL`/`CLOUD_LLM_MODEL`/
  `LLM_TIMEOUT_SECONDS`, all environment-variable driven.
- `models.py`: `Run.summary_source` (`"ollama"`/`"cloud"`/`"fallback"`).
  `api/summary.py`, `api/schemas.py`: surfaced via `GET /collections/summary`.
- `service.py`: `summarise` stage now calls `summary_narrator.narrate`
  instead of `ai/fallback.render_summary` directly.
- `compose.override.yml`: dev backend wired to reach Ollama at
  `host.docker.internal:11434` (documented limitation: only works if
  Ollama binds `0.0.0.0`, not the default loopback-only -- falls back
  to the deterministic template correctly either way, verified).
- 12 new tests (142 -> 154): `tests/ai/test_guard.py`,
  `test_provider.py`, `test_summary_narrator.py` (real, unmocked local
  Ollama calls, skipped gracefully if unreachable), `test_context.py`.
- New dependencies: `litellm`, `firecrawl-anydoc`.

## [0.6.0] - 2026-08-31

### Added

- `control/gate.py`: `evaluate_gate`, the 5% exception-rate gate.
  Reports both `exception_row_rate` (drives the gate) and
  `distinct_invoice_rate` (QA_PREP.md Q8's denominator ambiguity,
  resolved by reporting both rather than picking one silently).
- `ai/fallback.py`: `render_summary`, a deterministic Jinja narrative --
  no LLM, no network, the last rung of Phase 6's fallback chain, built
  first so every run always gets a plain-English summary.
- `models.py`: `Run` gains `gate_threshold`, `exception_row_rate`,
  `distinct_invoices_affected`, `distinct_invoice_rate`, `narrative`.
  `RunStatus` replaces the placeholder `COMPLETED` with the real
  `PASSED`/`BLOCKED` outcomes.
- `service.py`: wires the `control` and `summarise` stages into
  `execute_run` between `calculate` and `persist`.
- `api/summary.py`, `api/schemas.py`: `SummaryOut` carries the full
  "blocked payload" -- the rate, both denominators, the threshold, the
  narrative.
- `scripts/make_fixtures.py`: generates `fixtures/dataset_b_clean.xlsx`
  from dataset A by removing every row touched by any exception rule --
  passes the gate by construction. MASTER_PLAN.md section 3's dataset C
  (renamed columns) and D (corrupt file) are not built yet; nothing
  before Phase 10 needs them.
- 10 new tests (132 -> 142): `tests/control/test_gate.py` (threshold
  boundary, zero-invoice edge case, row-rate/distinct-rate divergence),
  `tests/ai/test_fallback.py`, and a direct proof of the Phase 5
  done-when in `tests/persistence/test_service.py` -- dataset A's real
  run blocks, dataset B's real run passes.

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
