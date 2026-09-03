# Architecture

Owns: components, data flow, why each decision was made, trade-offs, what
breaks at scale. Does not own: how to run anything (see `DEVELOPMENT.md`),
endpoint payloads (see `API.md`).

Status: **Phase 8 complete -- core scope (Phases 0-8) done.** Populated phase by phase as components land.

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
- `ai/context.py` (Phase 6): anydoc workbook-to-Markdown, for Phase 10's
  schema_mapper to consume -- still not called by anything as of Phase 7.
- `observability/metrics.py` (Phase 6, formalized in Phase 12): plain
  in-process `llm_calls_total` counter for now.
- `ai/roles/exception_explainer.py` (Phase 7): `explain_rules`, the
  batched-by-rule-code three-rung chain -- see "The LLM layer" below.
  `models.RunRuleExplanation` persists one row per `(run, rule_code)`.
- `frontend/src/routes/collections/` (Phase 8): five routes --
  `upload`, `runs`, `run-detail`, `exceptions`, `summary`. No auth,
  matching the API. Template's own shadcn/ui components throughout, no
  new UI library. See "The frontend" below.
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
expected output for the given sample file, not a bug to chase away.

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

### The Exception Explainer (Phase 7)

`ai/roles/exception_explainer.py`'s `explain_rules` is the same
three-rung chain, applied to the exception catalogue instead of the run
summary, with two deliberate differences:

- **Batched by rule code, not per row.** `docs/RULES.md` is a fixed
  14-entry catalogue -- "why did E001 fire" has one answer regardless of
  whether it fired once or five times in a given run. One
  `RuleExplanation` per distinct `rule_code` present in a run's
  exceptions is computed and persisted (`RunRuleExplanation`, one row
  per `(run, rule_code)`), then joined onto every matching `RunException`
  row at read time (`api/exceptions.py`) -- "every exception row carries
  an explanation" by lookup, not by redundant per-row storage.
- **Guards IDs, not numbers.** `ai/guard.py`'s `ids_are_contained`
  checks that every `INV-####`/`PAY-####`/`C###`-style token the model's
  output mentions is one of the actual IDs in that rule's batch for that
  run -- the failure mode here isn't a wrong number, it's the model
  citing a specific example it invented (or misremembered from a
  different rule's batch). Same rejection-and-fall-through behavior as
  the numeric guard.

The deterministic third rung, `RULE_METADATA`, is not batch-specific --
it is each rule's fixed, general cause/impact/suggested-fix/owner, in
the same words `docs/RULES.md`'s own "Why" prose already establishes,
so the fallback is never improvised text. `auto_fixable` is a hardcoded
`False` on every `RuleExplanation` regardless of rung -- the LLM is not
in the business of deciding a row is safe to auto-correct (AGENTS.md);
it explains, never fixes.

`_cached_explanation` is `functools.lru_cache`-wrapped, keyed on
`(rule_code, category, sorted affected IDs)`: re-running against the
same dataset (the overwhelmingly common case in this codebase's own
test suite and in a real demo re-run) never re-hits the LLM for a batch
it has already explained identically.

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

## The frontend (Phase 8)

Five routes under `frontend/src/routes/collections/`, deliberately
outside the template's `_layout/` tree (which requires
`isLoggedIn()`) -- collections has no auth, matching the backend API's
own no-auth design (an internal ops tool, not a multi-tenant product).
A shared `CollectionsNav` component (not a router-level layout route)
gives the five pages a consistent header without touching the
template's own routing.

Route-to-route flow mirrors the pipeline itself: `upload` -> (on
success) `run-detail?runId=` -> `exceptions?runId=` /
`summary?runId=`. `runId` is a TanStack Router search param
(`validateSearch`, `zod`), not a path param -- the route files stay
flat (`run-detail.tsx`, not `run-detail.$runId.tsx`), matching the
Phase 0 scaffold's own file names exactly.

`run-detail`'s timeline groups consecutive `run_events` by `stage`,
colors each group green/amber/red by the worst `level` inside it
(exactly MASTER_PLAN.md section 7's design: "Green through calculate,
amber at control when the gate blocks, red on failure"), and expands
per stage to the underlying events -- never a raw JSON dump.
`exceptions` joins each row's Phase 7 explanation inline, expandable to
cause/impact/suggested-fix/owner. `summary` renders the exact "blocked
payload" `api/schemas.py`'s `SummaryOut` carries, plus a badge naming
which of the three LLM rungs produced the narrative.

No new UI dependency: every component is the template's own
shadcn/ui (`frontend/src/components/ui/`). The one non-template piece
is `CollectionsService`, generated by the template's existing
`scripts/generate-client.sh` from the live OpenAPI schema -- run it
again any time `api/schemas.py` changes.

Verified in a real, unmocked headless Chromium (not just `tsc`/`vite
build` passing) against the actual Docker-served app: upload
`dataset_a_original.xlsx`, land on its `BLOCKED` run-detail page,
expand a timeline stage, click through to exceptions (cause/impact/
fix/owner render per row) and summary (block banner, narrative with
its source badge, region table), zero browser console errors captured
throughout. No Playwright spec committed for this yet -- see
`docs/DEVELOPMENT.md` for how to reproduce the check by hand; a real
test suite is a reasonable next addition, not built as of Phase 8.

## Trade-offs and what breaks at scale

This project is deliberately scoped as a fifteen-minute review, not a
platform (MASTER_PLAN.md section 1) — every trade-off below was made
consciously, not by accident, and each has a specific, named upgrade
path rather than an open-ended "would need more work."

**Scheduler: in-process → Celery Beat / a Kubernetes CronJob.**
`scheduler.py` is currently a stub for a single-process APScheduler job
(Phase 11, extended scope). APScheduler works correctly with one
worker process; the moment there is more than one (any real horizontal
scale-out), two workers can both pick up the same trigger unless
coordination is added. Celery Beat or a CronJob hitting the API is the
standard fix — same trigger, no shared in-process scheduler state to
race on.

**Structural validation: typed dataclasses → Pandera, conditionally.**
Today's structural guarantee is `ingest/loader.py`'s per-cell type
coercion plus `validate/schemas.py`'s declarative `SheetSchema`
constants (see "Why `validate/schemas.py` is not Pandera" above) — this
is deliberately Pandera-*shaped* work without the Pandera dependency,
because there is no DataFrame anywhere in the current pipeline for
Pandera to validate. If ingestion ever moves to a DataFrame-based
pipeline (e.g. to support much larger workbooks via chunked/vectorized
reads), Pandera becomes the natural fit at that point, not before —
adding it today would mean building a throwaway DataFrame solely to
re-check a guarantee the type system already gives.

**Observability: bespoke counters → a managed platform.**
`observability/metrics.py`'s `llm_calls_total` is a plain in-process
counter, and `observability/logging.py` is stdlib `logging`. Both are
sufficient for a single-instance demo where "did the LLM call succeed"
is a yes/no question read directly off the process. At real scale, a
managed observability layer (Prometheus + Grafana, or a hosted
equivalent) replaces both: multi-instance counters need to be
aggregated somewhere other than a single process's memory, and
`run_events`-style trend detection (is the exception rate climbing
across runs) is exactly the kind of query a time-series backend is
built for, not something to hand-roll against Postgres indefinitely.

**Exception explainer: advisory → a remediation queue.**
`ai/roles/exception_explainer.py` explains a rule violation and
proposes a fix; `auto_fixable` is hardcoded `False` everywhere, on
every rung, because the LLM is never allowed to decide something is
safe to auto-correct (AGENTS.md). The next real step here isn't
"let the model fix it" — it's a human-approval queue: an owner reviews
the suggested fix, approves or edits it, and *that* approved action
(not the model's raw output) is what actually touches data. This keeps
the same "code decides, humans approve, models never silently act"
posture that governs the rest of the system.

**Payment application: invoice-level → a proper cash-application
matcher.** Payments are matched to the invoice they explicitly
reference and checked against that invoice's own customer (rule E007).
Real accounts-receivable platforms instead match cash against a
customer's *ledger* — applying a payment across several open invoices,
handling partial and FIFO application, and reconciling on remittance
advice rather than a single Invoice_ID field. This is the single
hardest and most valuable upgrade on this list, and it's also exactly
where E007 (payment-to-invoice customer mismatch) comes from: a real
matcher would catch that same class of problem structurally instead of
flagging it after the fact.

**GSTIN validation: format-only, by design, not by oversight.**
`E006`/`E008` check the 15-character GSTIN pattern; there is no
checksum digit validation. This is a genuine, documented limitation
(see `docs/RULES.md`'s E006 entry) rather than a gap discovered later —
worth surfacing to a reviewer directly if asked "what's the weakest
part of this," per QA_PREP.md's own closing question.
