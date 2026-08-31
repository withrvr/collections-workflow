# Architecture

Owns: components, data flow, why each decision was made, trade-offs, what
breaks at scale. Does not own: how to run anything (see `DEVELOPMENT.md`),
endpoint payloads (see `API.md`).

Status: **Phase 6 complete.** Populated phase by phase as components land.

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
- `control/gate.py` (Phase 5): the 5% exception-rate gate. Never tuned
  to pass -- see "The control gate" below.
- `ai/fallback.py` (Phase 5): the deterministic Jinja narrative, the
  last rung of Phase 6's LLM fallback chain. Works with no network, no
  model -- every run gets a plain-English summary regardless of whether
  Ollama is even installed.
- `ai/provider.py` (Phase 6): the LiteLLM seam -- `call_ollama`/
  `call_cloud`, one HTTP call each, no fallback logic (that lives in
  each role).
- `ai/guard.py` (Phase 6): `numbers_are_contained`, the post-generation
  numeric containment check -- see "The LLM layer" below.
- `ai/roles/summary_narrator.py` (Phase 6): the three-rung fallback
  chain (Ollama -> cloud if configured -> deterministic template) for
  the run narrative, numeric-guarded at every rung.
- `ai/context.py` (Phase 6): anydoc workbook-to-Markdown, for Phase 7/10
  roles to consume -- not called by anything in Phase 6 itself.
- `observability/metrics.py` (Phase 6, formalized in Phase 12): plain
  in-process `llm_calls_total` counter for now.
- `export/` (Phase 9+): not yet populated.

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
in. As of Phase 5, six of the seven are wired up:

```
load -> validate -> calculate -> control -> summarise -> persist
```

`map` (Phase 10, multi-workbook column mapping) is still named but not
called — every current run resolves columns by exact match only.

Every stage writes a `run_events` row before/after its work
(`observability/events.py`). A `Run` is always a real, queryable row --
`POST /run` (Phase 4) never has to catch an exception out of the
orchestrator, because `execute_run` never raises; it returns a `Run`
whose `status` is `PASSED`, `BLOCKED`, or `FAILED`.

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

## The control gate

`control/gate.py`'s `evaluate_gate` is a pure function: invoice count in,
`GateResult` out. It is deliberately never tuned to pass —
`dataset_a_original.xlsx` blocks (47.2%), and that is the correct,
expected output for the given assessment file, not a bug to chase away.

QA_PREP.md Q8 flags that the brief's wording, "exception records over
invoice records," is ambiguous: one invoice can carry more than one
exception, and some exceptions (e.g. E002 on a payment, E005) never
touch an `invoice_id` at all. `evaluate_gate` resolves the ambiguity by
computing **both** rates rather than picking one silently:

- `exception_row_rate` = `exception_count / invoice_count` — drives the
  gate. The more literal reading of the brief, and it does not
  undercount a badly-behaved invoice carrying three exceptions as "one
  problem."
- `distinct_invoice_rate` = distinct invoices named by any exception
  row, over invoice count — reported alongside for transparency, never
  silently dropped even though it isn't the driving number.

Both rates, the threshold, and the raw counts are persisted on `Run` and
returned by `GET /collections/summary` — QA_PREP.md Q7's "blocked
payload reports the rate, both denominators, the threshold, and the
count," verified directly by `tests/control/test_gate.py` and
`tests/api/test_api.py`.

`ai/fallback.py`'s `render_summary` turns a `GateResult` plus the run's
numbers into one plain-English paragraph via a Jinja `Template` — no
LLM, no network, cannot fail short of a programming bug. This is
deliberately the *last* rung of Phase 6's LLM fallback chain, built
first: Phase 6 adds an LLM rung above it, but every run — Ollama
installed or not, network up or not — always gets a real summary.

## Why run status and run_events are plain strings, not enums

`models.Run.status` and `RunEvent.stage`/`level` are indexed `str`
columns, not Postgres native `ENUM` types or a SQLAlchemy `CHECK`
constraint. A later phase (Phase 10 may add `AWAITING_SCHEMA_CONFIRMATION`)
growing this catalogue would need `ALTER TYPE ... ADD VALUE` for a
native enum — awkward mid-transaction on some Postgres versions — or a
migration to widen a `CHECK` constraint. A plain string column, kept in
sync with the `RunStatus`/`EventStage`/`EventLevel` `Literal` aliases in
`models.py`, never needs a migration just because the catalogue grew —
exactly what happened in Phase 5, replacing the placeholder `COMPLETED`
status with the real `PASSED`/`BLOCKED` outcomes with no schema change.

## Persistence: SQL crosscheck, not just Python round-trip

`RunInvoicePosition` persists every eligible invoice position (Phase 1's
`compute_positions`, not just the overdue subset), and
`tests/persistence/test_sql_crosscheck.py` aggregates it back out with a
SQL `SUM`/`GROUP BY` — a genuinely independent code path from the
in-memory `calculate/` functions `scripts/reference_summary.py` uses.
Agreement between the two (15 overdue invoices, ₹12,02,000, West
heaviest) is real evidence the persistence layer is not silently
dropping or double-counting a row, not the same arithmetic checked twice.

## The LLM layer

`ai/roles/summary_narrator.py`'s `narrate()` is the three-rung chain
MASTER_PLAN.md section 9 names for Phase 6:

1. **Local Ollama** (`ai/provider.py`'s `call_ollama`), model `phi4-mini`
   via LiteLLM. The default and the only rung actually exercised without
   extra configuration.
2. **A configured cloud model** (`call_cloud`), only attempted if
   `COLLECTIONS_CLOUD_LLM_MODEL` is set -- unset by default, and this
   project never requires a cloud API key to run.
3. **The deterministic Jinja template** (`ai/fallback.py`, built in
   Phase 5). Cannot fail short of a programming bug -- there is no rung
   4, because there does not need to be one.

Every rung's raw output passes through `ai/guard.py`'s
`numbers_are_contained` before it can be accepted: every number literal
the model wrote must also appear in the prompt it was given. A rung that
invents a number is rejected outright and the chain falls through to the
next one -- the model narrates, it never computes (AGENTS.md), and this
is the check that turns that rule into something enforced rather than
merely intended. `summary_narrator.narrate()`'s prompt only ever
contains the already-computed metrics dictionary (invoice/overdue
counts, totals, the gate's rates) -- never raw sheet data, so there is
nothing in the prompt for the model to selectively misreport from in the
first place.

Which rung actually produced a run's narrative is recorded on
`Run.summary_source` (`"ollama"`/`"cloud"`/`"fallback"`) and surfaced via
`GET /collections/summary` -- a reviewer can see directly whether a given
run's summary came from the model or the safety net, never silently.

`observability/metrics.py`'s `llm_calls_total` (a plain in-process
counter for now; Phase 12 upgrades it to a real Prometheus `Counter` in
place) is Phase 6's own proof of its done-when: local Ollama calls
succeed and are counted, and since Ollama is local (no cloud round trip),
this holds with the network disconnected -- verified directly by
`tests/ai/test_summary_narrator.py` against a real, unmocked local model.

### Docker Compose and Ollama

The dev backend container is wired to reach Ollama at
`http://host.docker.internal:11434` (`compose.override.yml`, with
`extra_hosts: host-gateway` since `host.docker.internal` isn't automatic
on native Docker Engine, only Docker Desktop). This only actually
reaches Ollama if it is bound to `0.0.0.0`, not the default `127.0.0.1` --
a container's loopback is always its own, isolated from the host's,
regardless of WSL2 mirrored networking sharing host *interfaces* into
WSL (mirrored networking does not extend into a container's separate
network namespace). Set `OLLAMA_HOST=0.0.0.0` as an environment variable
on the Ollama host and restart it to fix this -- the same fix pre-22H2
WSL setups need for a different reason. Absent that, the Docker-run
backend degrades to `summary_source: "fallback"` automatically and
correctly (verified: `docker compose exec backend` reaches the API,
gets a `PASSED`/`BLOCKED` run either way, just without the LLM rung) --
this is the fallback chain working exactly as designed, not a bug.
Running `pytest`/scripts natively via `uv run` (not inside the
container) reaches Ollama directly with no such caveat, since WSL's own
loopback genuinely is shared with Windows' under mirrored networking.

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
