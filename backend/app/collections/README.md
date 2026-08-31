# ERP Collection Reporting Workflow

The assessment deliverable for Elevent Group: an ERP collection reporting
service built on `fastapi/full-stack-fastapi-template`. This file is the
single source of truth for what the service does and how to run it; see
`docs/` for internals (owned per file, see below).

Status: **Phase 1 (Domain core)**. This README will be filled in as each
phase lands; see `../../../docs/CHANGELOG.md` for what has shipped so far.

## What this does

Computes an overdue collections position — invoice-level and by
region/customer — from an ERP export (Customers, Invoices, Payments,
Region_Mapping sheets), as of a fixed report date. Phase 1 covers the pure
calculation core: loading the workbook into typed records and computing
outstanding/overdue/ageing/region figures. No API, database, or exception
reporting yet — see `docs/CHANGELOG.md` for what each phase adds.

## How to run

```
cd backend
uv run python -m app.collections.scripts.reference_summary
uv run pytest app/collections/tests -v
```
The script loads `fixtures/dataset_a_original.xlsx` and prints the overdue
count, total outstanding, and region breakdown.

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
