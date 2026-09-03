# Development

Owns: local setup, commands, git workflow, commit format, testing,
release process. Does not own: business logic (see `README.md`).

Status: **Phase 8 complete — core scope (Phases 0-8) done.**

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
uv run pytest app/collections/tests -v                       # full test suite (168 tests, ~60s incl. real Ollama calls)
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

## Quality gates and agent-assisted development

This section is the "how it was actually built" that a `git log` alone
doesn't show — how correctness and consistency were enforced on every
commit, not just at the end.

**Pre-commit, on every commit** (`.pre-commit-config.yaml`, repo root):
`ruff check --fix` and `ruff format` (Python lint + format), `mypy` and
`ty` (two independent type checkers on `backend/app`), `biome` (frontend
lint), `typos` (catches misspellings before they ship), plus the
template's own file hygiene hooks and an auto-regenerated frontend SDK
whenever `api/schemas.py` or the OpenAPI schema changes — so the
TypeScript client can never silently drift out of sync with the backend
it calls. None of this is optional at commit time; a failing hook blocks
the commit.

**168 tests**, run before every merge (`uv run pytest
app/collections/tests -v`) — see "Commands" and "Testing" above for the
full breakdown by phase. The suite is deliberately weighted toward
exception handling (MASTER_PLAN.md section 10): every one of the 14
rules has its own positive-and-negative test, a coverage test asserts
none of them ever goes silently unused, and a reconciliation test proves
the calculator's own arithmetic never creates or destroys a rupee. This
is what "reliable" means concretely in this codebase — not a vibe, a
gate a commit has to pass.

**Agent-side build tooling.** This codebase was built with an AI coding
agent from Phase 3 onward, using two Claude Code skills that shape how
the agent works rather than what the product does — neither is a
runtime dependency, neither ships in `requirements.txt`:

- **[ponytail](https://github.com/DietrichGebert/ponytail)** — a YAGNI
  ladder the agent runs against its own output before opening a merge
  request: does this need to exist, is it already in the codebase, does
  the standard library already do it, can it be one line instead of ten.
  Its own published benchmark, measured on a headless agent editing this
  exact FastAPI template, reports roughly 54% less code and 20% lower
  cost than a no-skill baseline, with correctness-critical categories
  (validation, error handling, security) explicitly excluded from what
  it's allowed to cut. `/ponytail-review` ran at the end of every phase
  in this build and produced a delete-list before each merge request.
- **[caveman](https://github.com/JuliusBrussee/caveman)** — compresses
  the agent's own prose (explanations, commit-message drafts, planning
  text) while leaving code and error messages byte-exact, so more of a
  session's context budget goes to the actual codebase instead of the
  agent talking about it. `/caveman-commit` produced the terse
  Conventional Commit messages this project's history uses.

Together with the commit discipline below, these are the concrete
answer to "how did you use AI to build this, not just inside it" —
QA_PREP.md keeps this as one of the two questions worth hoping a
reviewer asks.

## Git workflow

Conventional Commits, one logical change per commit — enforced in
practice, not just described: `type(scope): summary` under 72
characters, with the body explaining *why* a change was made, not
restating the diff. If a commit body needs the word "and," it's usually
two commits. Feature-by-feature merge requests, one phase's worth of
changes landing across several small MRs rather than one large one, so
each is reviewable on its own and the owning documentation file is
updated in the same commit as the behavior it describes — a docs update
is never a separate, later task. See `AGENTS.md` at the repo root for
the full standing instructions this build follows.

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
