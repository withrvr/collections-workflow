# ERP Collection Reporting Workflow

The assessment deliverable for Elevent Group: an ERP collection reporting
service built on `fastapi/full-stack-fastapi-template`. This file is the
single source of truth for what the service does and how to run it; see
`docs/` for internals (owned per file, see below).

Status: **Phase 6 (LLM layer) complete**. This README
will be filled in as each phase lands; see `../../../docs/CHANGELOG.md`
for what has shipped so far.

## What this does

Computes an overdue collections position — invoice-level and by
region/customer — from an ERP export (Customers, Invoices, Payments,
Region_Mapping sheets), as of a fixed report date, and flags every data
quality or business-rule issue it finds along the way rather than
silently dropping the affected row. Phase 1 built the pure calculation
core (loading the workbook into typed records, computing
outstanding/overdue/ageing/region figures); Phase 2 added the 14-rule
exception catalogue (`docs/RULES.md`) that explains every exclusion;
Phase 3 added a real run lifecycle — every uploaded workbook becomes a
persisted `Run`, `COMPLETED` or `FAILED`, with a `run_events` timeline a
non-technical user can read and no raw traceback ever reaching them.
Phase 4 put all of that behind a real API (`docs/API.md`) — upload a
file at `POST /collections/runs/` and drive the whole flow from
`/docs`. Phase 5 added the control gate: any run whose exception rate
exceeds 5% comes back `BLOCKED`, not silently passed off as clean, with
a deterministic plain-English narrative either way. Phase 6 puts a local
LLM (Ollama, `phi4-mini`) in front of that narrative — the model
narrates the already-computed numbers, never raw sheets, and never gets
the final word: a numeric guard rejects any output that invents a
figure it wasn't given, falling through to the same deterministic
template if the model (or the network) fails. See `docs/CHANGELOG.md`
for what each phase adds.

## How to run

```
cd backend
uv run python -m app.collections.scripts.reference_summary
uv run pytest app/collections/tests -v
```
The script loads `fixtures/dataset_a_original.xlsx` and prints the overdue
count, total outstanding, and region breakdown.

To exercise the full pipeline end to end against the real Postgres (not
the in-memory SQLite the test suite uses), bring up the Docker stack
(`docker compose watch` from the repo root — the dev backend container
runs `alembic upgrade head` automatically before starting) and open
http://localhost:8000/docs. `POST /collections/runs/` with a workbook
file, then drive `GET /collections/overdue`, `/exceptions`, `/regions`,
`/summary`, `/run-log/{id}/events` from there — see `docs/API.md`.

## Business rules

- Report date: `2026-07-31` (`app/collections/config.py`, never `datetime.now()`).
- Only `Approved` invoices are included in the overdue report; `Cancelled`
  and `Credit Note` are excluded (shown in the exception report from Phase 2 on).
- Outstanding = Invoice Amount − valid payments received on or before the
  report date. Tax is never added.
- A payment is valid only if its amount is positive, it is dated on or
  before the report date, and its customer matches the invoice's own
  customer.
- Overdue = Due Date strictly before the report date AND Outstanding > 0.
- If Customer Region is blank, Region is derived from `Region_Mapping` via
  State.
- **Control gate**: a run's exception rate is `exception_count /
  invoice_count`. If it exceeds 5%, the run is `BLOCKED`, never silently
  reported as clean; if not, it `PASSED`. Never tuned to pass —
  dataset_a_original.xlsx blocks (47.2%), and it's supposed to.

See `docs/RULES.md` for the full exception catalogue (Phase 2).

## Assumptions

- **A payment dated before its own invoice's invoice date still counts in
  full toward outstanding.** The workbook lists "payment before invoice"
  only as an exception-report item, not as a reason to exclude the
  payment from the calculation. Verified against the given dataset: the
  reference figures (15 overdue invoices, ₹12,02,000 total, West
  heaviest) only reconcile under this reading — excluding that payment
  instead would land the total at ₹12,12,000. Example: PAY-2027 (dated
  2026-06-05) still reduces INV-1004's outstanding, even though
  INV-1004's own invoice date is 2026-06-10.
- **Ageing bucket boundaries (0-30 / 31-60 / 61-90 / 90+ days) are a
  standard-practice default**, not specified anywhere in the workbook.
  Revisit if the client expects different cutoffs.
- An invoice with an unknown customer reference, a missing due date, or a
  non-positive amount is excluded from the overdue report (it cannot be
  soundly attributed to a Region/Customer or compared against a due
  date) — shown in the exception report from Phase 2 on, not silently
  dropped.
- **The control gate's "exception records over invoice records" reads as
  the exception-*row* count over the invoice count**, not distinct
  invoices affected. The wording in the brief is ambiguous (one invoice
  can carry more than one exception; some exceptions never touch an
  invoice_id at all — e.g. E002 on a payment). The row rate is the more
  literal reading and does not undercount a badly-behaved invoice with
  three exceptions as "one problem." The distinct-invoices-affected rate
  is still reported alongside it (`GET /collections/summary`) so nothing
  is hidden either way — see `docs/ARCHITECTURE.md`'s control gate
  section and `control/gate.py`'s docstring.

## AI tooling used

**Runtime (Phase 6):** local-first via [LiteLLM](https://docs.litellm.ai/)
(`ai/provider.py`) against [Ollama](https://ollama.com) running
`phi4-mini`. The LLM only ever narrates a frozen dictionary of
already-computed numbers (`ai/roles/summary_narrator.py`'s own
docstring: "never receives raw sheets") — it does not compute, choose,
or correct anything (AGENTS.md). Three-rung fallback, in order: local
Ollama, an optional configured cloud model (`ai/provider.py`, unset by
default and never required), then a deterministic Jinja template
(`ai/fallback.py`) that cannot fail short of a programming bug. Every
rung's output is numeric-guarded (`ai/guard.py`): if it contains a
number that was never given to it, it's rejected outright and the chain
falls through — never surfaced as if it were real. Which rung actually
produced a run's narrative is recorded on `Run.summary_source`
(`"ollama"`/`"cloud"`/`"fallback"`) and returned by
`GET /collections/summary`. Runs entirely without internet access —
Ollama is local, and `tests/ai/test_summary_narrator.py`'s
`test_narrate_uses_local_ollama_and_records_metric` proves it end to
end against a real (not mocked) local model.

**anydoc** (`ai/context.py`): workbook-to-Markdown conversion for LLM
context only, never a calculation source — see `docs/ARCHITECTURE.md`'s
anydoc boundary. Not yet consumed by any Phase 6 role; ready for Phase 7's
exception_explainer and Phase 10's schema_mapper.

**Agent-side build tooling**: [ponytail](https://github.com/DietrichGebert/ponytail)
(`/ponytail-review` before every MR) and [caveman](https://github.com/JuliusBrussee/caveman)
for the build conversation itself — both installed and used from Phase 3
onward, MASTER_PLAN.md section 6.

## Validation performed

- **154 tests** (`uv run pytest app/collections/tests -v`): loader/resolver
  tests, boundary tests on the calculators, a positive and a negative case
  per exception rule against hand-built records, and the tests below.
- **Rule coverage test** (`tests/validate/test_coverage.py`): asserts every
  one of the 14 rules fires at least once against `dataset_a_original.xlsx`,
  and that the registry covers exactly E001-E014 — a rule that never
  triggers is treated as a bug, not good news.
- **Reconciliation tests** (`tests/test_reconcile.py`): two identities
  proving nothing silently vanishes. Every invoice's
  `outstanding + valid_paid == invoice_amount + overpaid`, summed across
  the full 36-invoice portfolio; and every payment rupee is either applied
  to reduce some invoice's outstanding or explicitly unapplied, with every
  unapplied payment traceable to an exception row. These are
  internal-consistency checks — verifying the calculator's own arithmetic
  never creates or destroys a rupee — not an independently-derived second
  method.
- **Exact-ID assertions throughout**, not just "fires at least once":
  every rule test and the reference-number regression test assert the
  precise set of invoice/payment/customer IDs a rule or calculation
  should produce, so a rule silently over- or under-firing is caught, not
  just a rule going fully silent.
- **SQL crosscheck** (`tests/persistence/test_sql_crosscheck.py`, Phase 3):
  the independently-derived second method the reconciliation tests above
  deliberately weren't. Runs `execute_run` against dataset A, then
  aggregates the persisted `RunInvoicePosition` rows straight out of the
  database with a SQL `SUM`/`GROUP BY` — a genuinely different code path
  from `scripts/reference_summary.py`'s in-memory Python loop — and
  checks it against the same reference numbers (15 overdue, ₹12,02,000,
  West heaviest). Agreement between the two is real evidence the
  persistence layer isn't silently dropping or double-counting a row.
- **Error-contract tests** (`tests/persistence/test_service.py`, Phase 3):
  five deliberately broken workbooks (missing sheet, missing column,
  corrupt/non-xlsx file, an unparseable cell) each assert the resulting
  run is `FAILED` with a specific `error_code` and a plain-English
  `error_message` — and assert the literal strings `"Traceback"`/`"Error"`
  never appear in it, not just that *some* message exists.
- **API tests** (`tests/api/test_api.py`, Phase 4): the whole flow a
  reviewer would drive from `/docs` — upload, list, detail, overdue,
  exceptions (with rule/severity filters), regions, summary, run-log —
  against dataset A, plus a broken-upload case asserting `200` (not
  `500`) with a `FAILED` run in the body.
- **Control gate tests** (`tests/control/test_gate.py`, Phase 5): the
  threshold boundary (exactly 5% passes, just over blocks), zero-invoice
  edge case, and the row-rate/distinct-rate divergence on a
  repeat-offender invoice. **Fallback narrative tests**
  (`tests/ai/test_fallback.py`): the deterministic Jinja summary for
  both a `BLOCKED` and a `PASSED` run. **`tests/persistence/test_service.py`**
  proves the actual Phase 5 done-when directly: dataset A's real run
  blocks, `dataset_b_clean.xlsx`'s real run (generated by
  `scripts/make_fixtures.py`, every row touched by any exception rule
  removed) passes.
- **LLM tests** (`tests/ai/`, Phase 6): `test_guard.py` — matching
  numbers pass, an invented number fails, a reformatted date (hyphen vs.
  prose) is not mistaken for a negative sign. `test_summary_narrator.py`
  — a real (not mocked) call to local Ollama produces a narrative and
  increments `llm_calls_total` (skipped gracefully if Ollama isn't
  reachable, so this suite never hard-fails on a machine without it),
  and the fallback chain reaches the deterministic template correctly
  when Ollama is unreachable (`monkeypatch`, no real network dependency
  for that assertion). `test_provider.py`, `test_context.py`.

## Owning-doc map

| File | Owns |
|---|---|
| `README.md` (this file) | What it does, how to run, business rules, assumptions, AI tooling, validation |
| `docs/ARCHITECTURE.md` | Components, data flow, decisions, trade-offs |
| `docs/API.md` | Every endpoint: method, path, params, response schema, error codes |
| `docs/RULES.md` | The exception rule catalogue, E001-E014 |
| `docs/DEVELOPMENT.md` | Local setup, commands, git workflow, testing |
| `docs/DEMO.md` | Presentation runbook |
