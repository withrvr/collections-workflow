# Exception Rule Catalogue

Owns: the exception rule catalogue, single source of truth for E001-E014.
Does not own: anything that isn't a rule.

Status: **Phase 2 in progress.** Rules are implemented and documented
together — this file is the single source of truth for the catalogue and
must match `backend/app/collections/validate/rules.py` exactly. Updated
incrementally, one rule per commit, as each lands.

## Severity

`error` — the rule excludes a real rupee amount from a downstream figure
a reader would otherwise take at face value. `warning` — the money is
already handled correctly (or none moves), but the fact still merits
review. This is a different vocabulary from `run_events.level` (Phase 3),
which describes pipeline-stage health, not business weight.

## Summary

| Code | Category | Severity | Dataset A count |
|---|---|---|---|
| E001 | Missing due date | error | 1 |

## E001 — Missing due date

**Condition:** `Invoice.due_date is None`.
**Fires on:** INV-1027.
**Excludes:** the invoice from the overdue report (`calculate/overdue.py`'s
`is_eligible` requires a due date — nothing to compare against the report
date).
**Why:** an invoice with no due date cannot be classified overdue or
current; excluding it and flagging it beats guessing a date.
