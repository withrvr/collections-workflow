"""Explains exception rows, batched by rule code -- cause, impact, suggested fix, owner.

Built in Phase 7 (MASTER_PLAN.md). Batched by `rule_code`, not per row:
one explanation per rule that fired in a run, shared by every exception
row carrying that code -- the fourteen rules are a fixed catalogue
(`docs/RULES.md`), so "why did E001 fire" has one answer regardless of
how many invoices it fired on.

`auto_fixable` is hardcoded `False`, never LLM-controlled -- the LLM
explains, it does not decide whether something is safe to auto-correct
(AGENTS.md: never fix a bad row automatically, silently or otherwise).

Same three-rung fallback as `ai/roles/summary_narrator.py`, guarded at
every LLM rung by `ai/guard.py`'s `ids_are_contained`: an explanation
that names an invoice/payment/customer ID never in its own batch is
rejected outright and the chain falls through. The deterministic third
rung (`RULE_METADATA` below) is not per-batch -- it is the rule's fixed,
general explanation, the same words `docs/RULES.md` already establishes
for that code.

Cached per `(rule_code, sorted affected IDs)`: identical batches (the
overwhelmingly common case -- most runs are dataset A) never re-hit the
LLM.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from app.collections.ai import guard, provider
from app.collections.contracts import ExceptionRow

# One entry per rule in docs/RULES.md, in the same words as that
# catalogue's own "Why" prose -- the deterministic fallback is not
# improvised, it is the rule's own documented rationale.
RULE_METADATA: dict[str, dict[str, str]] = {
    "E001": {
        "cause": "Due Date was left blank on the invoice.",
        "impact": "The invoice cannot be classified overdue or current, so it is excluded from the overdue report entirely.",
        "suggested_fix": "Backfill Due Date on the source invoice in the ERP and re-run.",
        "owner": "AR / Order-to-Cash team",
    },
    "E002": {
        "cause": "Customer_ID on this invoice or payment does not exist in the Customers sheet.",
        "impact": "Cannot attribute a Region or credit position to a customer that doesn't exist in master data; the record is excluded.",
        "suggested_fix": "Confirm the correct Customer_ID and either fix the source record or add the missing customer master row.",
        "owner": "Master Data / ERP admin",
    },
    "E003": {
        "cause": "A payment references an Invoice_ID that does not exist in the Invoices sheet.",
        "impact": "The payment cannot be applied to any invoice, so it does not reduce any invoice's outstanding balance.",
        "suggested_fix": "Verify the invoice number on the payment record and correct it, or confirm the invoice was omitted from the export.",
        "owner": "AR / Cash Application team",
    },
    "E004": {
        "cause": "Invoice_Amount_INR is zero or negative.",
        "impact": "The invoice cannot be meaningfully classified overdue or current, so it is excluded from the overdue report.",
        "suggested_fix": "Review the invoice in the ERP -- likely a data entry error or an unposted credit.",
        "owner": "Billing team",
    },
    "E005": {
        "cause": "Payment_Amount_INR is zero or negative.",
        "impact": "The payment is excluded from the valid-payments total and does not reduce any invoice's outstanding balance.",
        "suggested_fix": "Confirm whether this is a reversal that should be recorded differently, or a data entry error.",
        "owner": "Cash Application team",
    },
    "E006": {
        "cause": "The customer's GSTIN does not match the standard 15-character format.",
        "impact": "Warning only -- does not affect any financial calculation, but is a compliance data-quality risk.",
        "suggested_fix": "Verify and correct the customer's GSTIN in the ERP master data.",
        "owner": "Master Data / Compliance",
    },
    "E007": {
        "cause": "The payment's Customer_ID differs from the invoice's own Customer_ID.",
        "impact": "The payment is excluded from that invoice's outstanding balance rather than silently reassigned to a different customer.",
        "suggested_fix": "Confirm the correct customer and invoice for this payment, then reassign it manually if appropriate.",
        "owner": "Cash Application team",
    },
    "E008": {
        "cause": "GSTIN is blank on the customer record.",
        "impact": "Warning only -- a compliance data-quality gap, not a calculation issue.",
        "suggested_fix": "Collect and record the customer's GSTIN.",
        "owner": "Master Data / Compliance",
    },
    "E009": {
        "cause": "Payment_Date is after the fixed report date.",
        "impact": "Correctly excluded from this report's outstanding calculation -- a future-dated payment cannot reduce a past position.",
        "suggested_fix": "No fix needed; confirm the payment date was not mis-keyed if this is unexpected.",
        "owner": "Cash Application team (verification only)",
    },
    "E010": {
        "cause": "Payment_Date is earlier than the invoice's own Invoice_Date.",
        "impact": "Warning only -- the payment still counts toward outstanding, but the date sequence looks wrong and merits review.",
        "suggested_fix": "Confirm both the invoice date and payment date are correct in the source system.",
        "owner": "Billing / Cash Application team",
    },
    "E011": {
        "cause": "Invoice status is Cancelled.",
        "impact": "Excluded from the overdue report; flagged here rather than silently dropped.",
        "suggested_fix": "No fix needed -- cancelled invoices are expected to be excluded.",
        "owner": "N/A (informational)",
    },
    "E012": {
        "cause": "Invoice status is Credit Note.",
        "impact": "Excluded from the overdue report; flagged here rather than silently dropped.",
        "suggested_fix": "No fix needed -- credit notes are expected to be excluded.",
        "owner": "N/A (informational)",
    },
    "E013": {
        "cause": "Two or more invoices share the same Source_System_Ref.",
        "impact": "Warning only -- may indicate a duplicate export or a genuine re-issued invoice.",
        "suggested_fix": "Confirm with the source ERP whether this is a true duplicate or a legitimate re-issue.",
        "owner": "Master Data / ERP admin",
    },
    "E014": {
        "cause": "Valid payments against this invoice exceed the invoice amount.",
        "impact": "Warning only -- outstanding is floored at zero; the overpaid amount itself is not tracked as a receivable here.",
        "suggested_fix": "Confirm whether the overpayment should be refunded or applied as credit to another invoice.",
        "owner": "Cash Application team",
    },
}


@dataclass(frozen=True, slots=True)
class RuleExplanation:
    rule_code: str
    cause: str
    impact: str
    suggested_fix: str
    owner: str
    auto_fixable: bool  # always False -- see module docstring
    source: str  # "ollama" | "cloud" | "fallback"


def _affected_ids(rows: list[ExceptionRow]) -> set[str]:
    ids: set[str] = set()
    for row in rows:
        for id_ in (row.invoice_id, row.payment_id, row.customer_id):
            if id_:
                ids.add(id_)
    return ids


def _fallback_explanation(rule_code: str) -> RuleExplanation:
    meta = RULE_METADATA[rule_code]
    return RuleExplanation(
        rule_code=rule_code,
        cause=meta["cause"],
        impact=meta["impact"],
        suggested_fix=meta["suggested_fix"],
        owner=meta["owner"],
        auto_fixable=False,
        source="fallback",
    )


@lru_cache(maxsize=256)
def _cached_explanation(
    rule_code: str, category: str, affected_ids: tuple[str, ...]
) -> RuleExplanation:
    meta = RULE_METADATA[rule_code]
    context = (
        f"Rule {rule_code} ({category}) fired on: {', '.join(affected_ids) if affected_ids else 'no specific records'}.\n"
        f"General cause: {meta['cause']}\n"
        f"General impact: {meta['impact']}\n"
        "Write ONE short sentence adding batch-specific context (e.g. how many records, "
        "which ones by ID) -- use ONLY the IDs listed above, never invent one. "
        "Do not restate the general cause/impact verbatim; add to it."
    )
    for rung, call in (
        ("ollama", provider.call_ollama),
        ("cloud", provider.call_cloud),
    ):
        try:
            addition = call(context)
        except provider.LLMError:
            continue
        if guard.ids_are_contained(addition, set(affected_ids)):
            return RuleExplanation(
                rule_code=rule_code,
                cause=f"{meta['cause']} {addition}",
                impact=meta["impact"],
                suggested_fix=meta["suggested_fix"],
                owner=meta["owner"],
                auto_fixable=False,
                source=rung,
            )
    return _fallback_explanation(rule_code)


def explain_rules(exception_rows: list[ExceptionRow]) -> dict[str, RuleExplanation]:
    """One `RuleExplanation` per distinct `rule_code` present in
    `exception_rows` -- every exception row's rule_code is a key here,
    so "every exception row carries an explanation" by lookup."""
    grouped: dict[str, list[ExceptionRow]] = {}
    for row in exception_rows:
        grouped.setdefault(row.rule_code, []).append(row)

    explanations: dict[str, RuleExplanation] = {}
    for rule_code, rows in grouped.items():
        if rule_code not in RULE_METADATA:
            continue
        affected_ids = tuple(sorted(_affected_ids(rows)))
        explanations[rule_code] = _cached_explanation(
            rule_code, rows[0].category, affected_ids
        )
    return explanations
