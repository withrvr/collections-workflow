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
| E004 | Non-positive invoice amount | error | 1 |
| E011 | Cancelled invoice | warning | 1 |
| E012 | Credit Note invoice | warning | 1 |
| E013 | Duplicate source system reference | warning | 2 |
| E006 | Invalid GSTIN format | warning | 1 |
| E008 | Missing GSTIN | warning | 1 |
| E005 | Non-positive payment amount | error | 2 |
| E009 | Payment after report date | warning | 1 |
| E002 | Unknown customer reference (invoice or payment) | error | 2 |

## E001 — Missing due date

**Condition:** `Invoice.due_date is None`.
**Fires on:** INV-1027.
**Excludes:** the invoice from the overdue report (`calculate/overdue.py`'s
`is_eligible` requires a due date — nothing to compare against the report
date).
**Why:** an invoice with no due date cannot be classified overdue or
current; excluding it and flagging it beats guessing a date.

## E004 — Non-positive invoice amount

**Condition:** `Invoice.invoice_amount <= 0`.
**Fires on:** INV-1028 (-45,000).
**Excludes:** the invoice from the overdue report.
**Why:** a negative or zero invoice amount is either a data-entry error
or a credit that hasn't been reclassified as a Credit Note; either way
it should not silently net into the overdue total.

## E011 — Cancelled invoice

**Condition:** `Invoice.status == "Cancelled"`.
**Fires on:** INV-1029.
**Excludes:** the overdue report (`calculate/overdue.py`'s
`ELIGIBLE_STATUS`).
**Why:** correct-by-design exclusion, not defective data — shown here so
nothing silently disappears from the picture.

## E012 — Credit Note invoice

**Condition:** `Invoice.status == "Credit Note"`.
**Fires on:** INV-1030.
Same treatment and rationale as E011.

## E013 — Duplicate source system reference

**Condition:** two or more invoices share a non-blank
`Source_System_Ref`. Blank references are not compared against each
other — a shared "no reference recorded" is not a duplicate.
**Fires on:** INV-1011 and INV-1031, both `EMP-SO-0011`. Emitted as one
row per affected invoice (two rows total), each naming the sibling(s).
**Excludes:** nothing — both invoices remain in the overdue report
independently.
**Why:** a shared ERP reference across two different invoice records can
mean a duplicate entry or a legitimately split sales order; either way it
needs investigation, not an automatic guess.

## E006 — Invalid GSTIN format

**Condition:** GSTIN present but does not match
`^\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][A-Z0-9]$` (2-digit state code, 10-char PAN,
entity code digit, literal Z, checksum char — 15 chars total).
**Fires on:** C023 (`INVALIDGSTIN`).
**Format-only — no checksum validation.** This is a deliberate, documented
limitation, not an oversight (see README.md's weakest-part discussion).
**Excludes:** nothing downstream — GSTIN doesn't feed outstanding/overdue
math.
**Why:** flags master-data quality for whoever owns Customer records;
doesn't block collection reporting.

## E008 — Missing GSTIN

**Condition:** `Customer.gstin is None`.
**Fires on:** C025.
**Excludes:** nothing downstream.
**Why:** same master-data-quality rationale as E006, distinguished
because "missing" and "malformed" call for different remediation (get
the value vs. fix the value).

## E005 — Non-positive payment amount

**Condition:** `Payment.payment_amount <= 0`.
**Fires on:** PAY-2018 (0), PAY-2029 (-5,000).
**Excludes:** the payment from the valid-payments total for its invoice
(`calculate/outstanding.py`'s `is_valid_payment` requires `> 0`).
**Why:** a zero or negative payment amount cannot reduce an outstanding
balance; it is either a reversal that needs its own record or a
recording error.

## E009 — Payment after report date

**Condition:** `Payment.payment_date > report_date`.
**Fires on:** PAY-2020 (2026-08-02, report date 2026-07-31).
**Excludes:** the payment from this period's valid-payments total
(`calculate/outstanding.py`'s `is_valid_payment` requires `<=
report_date`).
**Why flagged, not just silently excluded:** the workbook's own
enumerated exception categories list this explicitly. It is expected
business activity, not bad data — hence `warning`, not `error` — but a
reviewer looking at why a position didn't move needs to see it, not
infer it.

## E002 — Unknown customer reference

**Condition:** `customer_id` on an invoice *or* a payment is not present
in the Customers sheet. One rule, checked against both sheets, since
either kind of record can carry a dangling customer reference.
**Fires on:** INV-1026 (Customer_ID C999), PAY-2025 (Customer_ID C999).
PAY-2025 also fires E003 independently (its Invoice_ID is unknown too) —
deliberately two separate rows rather than one combined flag, so each
broken reference is visible regardless of whether the other were fixed.
**Excludes:** the invoice from the overdue report; a payment referencing
an unknown customer is also, incidentally, unresolvable (see E003).
**Why:** cannot attribute a Region or a credit position to a customer
that doesn't exist in the master data.
