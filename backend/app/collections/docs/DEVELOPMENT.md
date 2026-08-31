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

_Filled in as they exist (fixture generation, rule coverage tests,
reconciliation tests)._

## Git workflow

Conventional Commits, one logical change per commit. See `AGENTS.md` at
the repo root for the full standing instructions this build follows.

## Testing

_Filled in Phase 1-2 onward — see MASTER_PLAN.md section 10 for the test
layer breakdown (rule unit tests, coverage, boundary, reconciliation,
gate, guard, failure, independent recompute)._

## Release process

SemVer, tagged on merge to `main`. See `docs/CHANGELOG.md` at the repo
root.
