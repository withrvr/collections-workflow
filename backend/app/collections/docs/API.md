# API

Owns: every endpoint — method, path, params, response schema, status
codes, error codes. Does not own: business rationale (see `README.md`),
setup (see `DEVELOPMENT.md`).

Status: **Phase 0 skeleton.** Router stubs exist under
`backend/app/collections/api/` (`runs`, `overdue`, `exceptions`,
`regions`, `summary`, `run-log`, `mappings`), all mounted under
`/api/v1/collections`. None has real handlers yet — populated in Phase 4.

## Health check

`GET /api/v1/utils/health-check/` — from the base template, returns `true`.

## Endpoints

_Filled in Phase 4: one section per endpoint, with request/response
schemas and error codes. The error contract itself (`PipelineError`,
`error_code`/`error_message` on a `FAILED` run) is built and documented
in `ARCHITECTURE.md`'s "The error contract" section as of Phase 3 —
Phase 4 wires it to HTTP responses, not from scratch._
