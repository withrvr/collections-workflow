# Exception Rule Catalogue

Owns: the exception rule catalogue, single source of truth for E001-E014.
Does not own: anything that isn't a rule.

Status: **14/14 rules implemented and complete.** `validate/rules.py`
defines each rule; `validate/engine.py`'s `RULE_REGISTRY` registers all
14; `tests/validate/test_coverage.py` asserts every rule fires on
dataset A and the registry covers exactly E001-E014;
`tests/test_reconcile.py` proves no invoice or payment rupee is lost.
This file is the single source of truth for the catalogue and must match
the code exactly.

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
| E002 | Unknown customer reference (invoice or payment) | error | 2 |
| E003 | Unknown invoice reference | error | 1 |
| E004 | Non-positive invoice amount | error | 1 |
| E005 | Non-positive payment amount | error | 2 |
| E006 | Invalid GSTIN format | warning | 1 |
| E007 | Payment-to-invoice customer mismatch | error | 1 |
| E008 | Missing GSTIN | warning | 1 |
| E009 | Payment after report date | warning | 1 |
| E010 | Payment before invoice date | warning | 1 |
| E011 | Cancelled invoice | warning | 1 |
| E012 | Credit Note invoice | warning | 1 |
| E013 | Duplicate source system reference | warning | 2 |
| E014 | Overpayment (payments exceed invoice amount) | warning | 1 |

17 exception rows total against 36 invoice records (~47%) — consistent
with QA_PREP.md Q7's "roughly 16 to 19, about 45%" as an independent
sanity check that this catalogue is calibrated correctly.

## E001 — Missing due date

**Condition:** `Invoice.due_date is None`.
**Fires on:** INV-1027.
**Excludes:** the invoice from the overdue report (`calculate/overdue.py`'s
`is_eligible` requires a due date — nothing to compare against the report
date).
**Why:** an invoice with no due date cannot be classified overdue or
current; excluding it and flagging it beats guessing a date.

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

## E003 — Unknown invoice reference

**Condition:** `Payment.invoice_id` is not present in the Invoices sheet.
**Fires on:** PAY-2025 (Invoice_ID INV-9999). PAY-2025 also fires E002
independently (its Customer_ID is C999) — see E002 above.
**Excludes:** the payment is never applied to anything —
`calculate/outstanding.py` indexes payments by real invoice IDs, so there
is nothing to index it under.
**Why:** cash received against a reference that doesn't exist needs a
human to say what it was actually for.

## E004 — Non-positive invoice amount

**Condition:** `Invoice.invoice_amount <= 0`.
**Fires on:** INV-1028 (-45,000).
**Excludes:** the invoice from the overdue report.
**Why:** a negative or zero invoice amount is either a data-entry error
or a credit that hasn't been reclassified as a Credit Note; either way
it should not silently net into the overdue total.

## E005 — Non-positive payment amount

**Condition:** `Payment.payment_amount <= 0`.
**Fires on:** PAY-2018 (0), PAY-2029 (-5,000).
**Excludes:** the payment from the valid-payments total for its invoice
(`calculate/outstanding.py`'s `is_valid_payment` requires `> 0`).
**Why:** a zero or negative payment amount cannot reduce an outstanding
balance; it is either a reversal that needs its own record or a
recording error.

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

## E007 — Payment-to-invoice customer mismatch

**Condition:** `Payment.customer_id != Invoice.customer_id` for the
invoice the payment names (only evaluated when that invoice exists — see
E003).
**Fires on:** PAY-2026 — recorded against customer C003, but INV-1002
belongs to C002.
**Excludes:** the payment from C002's valid paid total, so C002 correctly
still shows overdue rather than being credited with someone else's cash.
**Why (worked example, matches MASTER_PLAN.md section 8 and QA_PREP.md
Q11):** the payment is flagged rather than reassigned, since reassignment
would be a silent data correction moving cash between ledgers on a guess.
Owner: Accounts Receivable.

## E008 — Missing GSTIN

**Condition:** `Customer.gstin is None`.
**Fires on:** C025.
**Excludes:** nothing downstream.
**Why:** same master-data-quality rationale as E006, distinguished
because "missing" and "malformed" call for different remediation (get
the value vs. fix the value).

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

## E010 — Payment before invoice date

**Condition:** `Payment.payment_date < Invoice.invoice_date` (only when
the invoice resolves — see E003).
**Fires on:** PAY-2027 (2026-06-05) against INV-1004 (invoice date
2026-06-10).
**Does NOT exclude** the payment from `compute_outstanding` — see
README.md Assumptions; this is a data-quality-only flag.
**Why:** worth a human's eye (possibly a misdated invoice or a
pre-payment against a purchase order), but the workbook doesn't
authorize excluding it, so the calculation still counts it in full.

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

## E014 — Overpayment (payments exceeding invoice amount)

**Condition:** sum of valid payments for an invoice (the same
`valid_payments_total` the calculator itself uses) exceeds
`Invoice.invoice_amount`.
**Fires on:** INV-1007 — invoice amount 88,000; PAY-2008 (30,000) +
PAY-2028 (80,000) = 110,000, an overpayment of 22,000.
**Not on the original required list** — added because the data
called for it (see QA_PREP.md Q5).
**Excludes nothing further:** `compute_outstanding` already floors at
zero, so no negative/credit figure leaks into the overdue report; this
rule surfaces *why* that floor applied.
**Why not net against the customer's other invoices:** netting is a
business decision the workbook doesn't define — surfaced, not assumed.

## Notes on rule interactions

- PAY-2025 fires both E002 and E003 (see E002/E003 above) — by design,
  not a bug in either rule.
- E006 and E008 are mutually exclusive per customer (E006 requires a
  non-null GSTIN).
- E007 and E010 both skip a payment whose `invoice_id` doesn't resolve
  (that case is E003's alone) rather than raising or comparing against
  nothing.
- E014 only evaluates invoices with `invoice_amount > 0`, to avoid a
  spurious fire against an already-E004-flagged negative-amount invoice
  with zero payments against it. It also doesn't distinguish "genuine
  overpayment" from "a floored negative amount" in the same way as the
  reconciliation identity in `tests/test_reconcile.py` — see that file's
  docstring for the subtlety this uncovered.
