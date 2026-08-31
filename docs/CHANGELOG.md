# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
