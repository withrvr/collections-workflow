# Development

Owns: local setup, commands, git workflow, commit format, testing,
release process. Does not own: business logic (see `README.md`).

Status: **Phase 8 complete — submission scope (Phases 0-8) done.**

## Local setup

This service lives entirely under `backend/app/collections/`, on top of
the unmodified `fastapi/full-stack-fastapi-template` base commit. Follow
the template's own `development.md` at the repo root for the base stack
(`docker compose up`, Postgres, etc.). One collections-specific addition
from Phase 3: `compose.override.yml`'s dev `backend` command now runs
`alembic upgrade head` before `fastapi dev`, so the `collections_run`,
`collections_run_event`, `collections_run_exception` and
`collections_run_invoice_position` tables exist automatically on a fresh
`docker compose watch`/`up`.

## Commands

```
cd backend
uv run pytest app/collections/tests -v                       # full test suite (162 tests, ~60s incl. real Ollama calls)
uv run pytest app/collections/tests/validate -v               # exception rule tests only
uv run pytest app/collections/tests/persistence -v             # run lifecycle / error contract
uv run pytest app/collections/tests/api -v                     # API tests (TestClient, in-memory SQLite)
uv run pytest app/collections/tests/control app/collections/tests/ai -v  # control gate / LLM layer
uv run python -m app.collections.scripts.reference_summary   # reference numbers against dataset A
uv run python -m app.collections.scripts.make_fixtures        # (re)generate dataset_b_clean.xlsx
uv run alembic upgrade head                                   # apply migrations (Postgres only)
uv run alembic check                                          # confirm models.py matches migrations
```

`tests/ai/` calls a real local Ollama (`phi4-mini`) where reachable, and
skips those specific tests gracefully otherwise (`pytest.mark.skipif`,
`tests/ai/conftest.py`) -- the rest of the suite never depends on Ollama,
since `summary_narrator.narrate()` always falls through to the
deterministic template when it's unavailable. Set up Ollama:

```
# On Windows (or wherever Ollama runs): ollama pull phi4-mini
export COLLECTIONS_OLLAMA_API_BASE=http://localhost:11434   # default; override if needed
```

## Git workflow

Conventional Commits, one logical change per commit. See `AGENTS.md` at
the repo root for the full standing instructions this build follows.

## Testing

Phase 1 covers boundary tests (due date exactly on the report date; a
payment landing exactly on the report date) and a reference-number
regression test against `fixtures/dataset_a_original.xlsx`
(`tests/test_reference_numbers.py`). Phase 2 added one test file per
exception rule under `tests/validate/` (positive case against dataset A
plus hand-built negative/boundary cases), a rule-coverage test
(`tests/validate/test_coverage.py`), and two reconciliation identities
(`tests/test_reconcile.py`). Phase 3 added `tests/persistence/` (an
in-memory SQLite `session` fixture, not Postgres — fast, no docker
compose required to run `pytest`; the real Postgres schema is exercised
via `alembic upgrade head` and guarded against drift by `alembic check`):
`test_service.py`'s run-lifecycle/error-contract tests (five deliberately
broken workbooks, each asserted to produce a specific `error_code` and a
readable, traceback-free `error_message`) and `test_sql_crosscheck.py`,
the independently-derived SQL recompute MASTER_PLAN.md section 10 asks
for. Phase 5 added `tests/control/test_gate.py` (threshold boundary,
zero-invoice edge case, row-rate/distinct-rate divergence) and
`tests/ai/test_fallback.py`. Phase 6 added the rest of `tests/ai/`:
`test_guard.py` (numeric containment, including the date-hyphen edge
case), `test_provider.py` and `test_summary_narrator.py` (real,
unmocked calls to local Ollama where reachable — see "Commands" above
for the skip behavior when it isn't), and `test_context.py`. Phase 7
added `test_exception_explainer.py` (every fired rule gets an
explanation, `auto_fixable` always `False`, the fallback rung reproduces
`RULE_METADATA` verbatim, and — against real Ollama — no explanation
ever names a record ID outside its own batch) and extended
`test_guard.py` with `ids_are_contained` cases. See MASTER_PLAN.md
section 10 for the full test layer breakdown.

Phase 8's frontend has no automated test suite yet (no Playwright specs
committed) -- it was verified manually, once, end to end in a real
browser rather than left unverified. Reproduce it:

```
cd backend && docker compose up -d --build backend   # from repo root; bakes the frontend build in
cd frontend
bunx playwright install chromium   # one-time; no --with-deps (needs sudo, skip it)
bun add -D playwright               # if not already a devDependency
```
Then drive it with Playwright's `chromium.launch({ args: ["--no-sandbox"] })`
against `http://localhost:8000/collections/upload` -- `nav`, `setInputFiles`
the fixture at `../backend/app/collections/fixtures/dataset_a_original.xlsx`,
click `Run`, `waitForURL(/run-detail/)`, assert `BLOCKED` renders, click
through to `/collections/exceptions` and `/collections/summary`,
`page.on("pageerror", ...)` to catch anything that throws. A real
frontend test suite (Playwright specs, not a one-off script) is a
reasonable next addition, not built as of Phase 8.

## Release process

SemVer, tagged on merge to `main`. See `docs/CHANGELOG.md` at the repo
root.
