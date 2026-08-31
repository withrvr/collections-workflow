# Development

Owns: local setup, commands, git workflow, commit format, testing,
release process. Does not own: business logic (see `README.md`).

Status: **Phase 0 skeleton.**

## Local setup

This service lives entirely under `backend/app/collections/`, on top of
the unmodified `fastapi/full-stack-fastapi-template` base commit. Follow
the template's own `development.md` at the repo root for the base stack
(`docker compose up`, Postgres, etc.); nothing collections-specific
changes that flow yet.

## Commands

```
cd backend
uv run pytest app/collections/tests -v                       # Phase 1 test suite
uv run python -m app.collections.scripts.reference_summary   # reference numbers against dataset A
```

## Git workflow

Conventional Commits, one logical change per commit. See `AGENTS.md` at
the repo root for the full standing instructions this build follows.

## Testing

Phase 1 covers boundary tests (due date exactly on the report date; a
payment landing exactly on the report date) and a reference-number
regression test against `fixtures/dataset_a_original.xlsx`
(`tests/test_reference_numbers.py`). Rule-unit/coverage/gate/guard/
failure/reconcile layers are added from Phase 2 on — see MASTER_PLAN.md
section 10 for the full test layer breakdown.

## Release process

SemVer, tagged on merge to `main`. See `docs/CHANGELOG.md` at the repo
root.
