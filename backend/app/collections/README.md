# ERP Collection Reporting Workflow

The assessment deliverable for Elevent Group: an ERP collection reporting
service built on `fastapi/full-stack-fastapi-template`. This file is the
single source of truth for what the service does and how to run it; see
`docs/` for internals (owned per file, see below).

Status: **Phase 0 (Foundation)**. This README will be filled in as each
phase lands; see `../../../docs/CHANGELOG.md` for what has shipped so far.

## What this does

_Filled in starting Phase 1-2 (MASTER_PLAN.md): business rules, the
exception catalogue summary, assumptions made where the brief was
ambiguous._

## How to run

_Filled in starting Phase 0 verification: `docker compose up`, health
check, first API call._

## Business rules

_Filled in Phase 1-2: report date, outstanding/overdue definitions,
approved-only filter, tax exclusion — see `docs/RULES.md` for the full
exception catalogue._

## Assumptions

_Filled in as judgement calls are made (e.g. no netting of credit notes,
exception-rate denominator choice) — see `QA_PREP.md` for the reasoning
behind each._

## AI tooling used

_Filled in Phase 6-7: LiteLLM seam, local-first Ollama model, numeric
guard, and the agent-side build tooling (ponytail, caveman, anydoc)._

## Validation performed

_Filled in Phase 2 and 10: rule coverage test, reconciliation test,
independent SQL recompute — see `docs/DEVELOPMENT.md` for how to run the
test suite._

## Owning-doc map

| File | Owns |
|---|---|
| `README.md` (this file) | What it does, how to run, business rules, assumptions, AI tooling, validation |
| `docs/ARCHITECTURE.md` | Components, data flow, decisions, trade-offs |
| `docs/API.md` | Every endpoint: method, path, params, response schema, error codes |
| `docs/RULES.md` | The exception rule catalogue, E001-E014 |
| `docs/DEVELOPMENT.md` | Local setup, commands, git workflow, testing |
| `docs/DEMO.md` | Presentation runbook |
