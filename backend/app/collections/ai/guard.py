"""Post-generation numeric containment check: every number in LLM output must appear in its input.

Built in Phase 6 (MASTER_PLAN.md), extended in Phase 7 with an ID
containment check for `ai/roles/exception_explainer.py`. The LLM never
computes, chooses, or corrects a number or an ID (AGENTS.md) -- it
narrates and explains. This is the check that makes that a guarantee
rather than a hope: if the model's output contains a number or a
record ID that was never in the prompt we gave it, the output is
rejected outright, never surfaced as if it were real.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

_NUMBER_RE = re.compile(r"\d[\d,]*\.?\d*")
# The dataset's own ID conventions: INV-1001, PAY-2001, C001. Deliberately
# specific rather than a generic "any capitalized token" pattern, which
# would flag ordinary words like "GSTIN" or "Region" as IDs.
_ID_RE = re.compile(r"\b(?:INV|PAY|C)-?\d{2,6}\b")


def _extract_numbers(text: str) -> set[Decimal]:
    """No leading sign: every number this narrator ever handles (counts,
    totals, rates) is non-negative, and treating a hyphen in a date like
    "2026-07-31" as a minus sign would make "31" and "-31" compare
    unequal for no real reason."""
    numbers: set[Decimal] = set()
    for match in _NUMBER_RE.finditer(text):
        cleaned = match.group().replace(",", "")
        if cleaned in ("", "."):
            continue
        try:
            numbers.add(Decimal(cleaned))
        except InvalidOperation:
            continue
    return numbers


def numbers_are_contained(output: str, context: str) -> bool:
    """True if every number literal in `output` also appears in
    `context` (as a `Decimal`, so "1202000" and "1,202,000.00" match).
    The model may phrase things differently, round differently, or add
    words -- it may never introduce a number that was not given to it.
    A narrative with zero numbers trivially passes."""
    output_numbers = _extract_numbers(output)
    if not output_numbers:
        return True
    context_numbers = _extract_numbers(context)
    return output_numbers <= context_numbers


def ids_are_contained(output: str, allowed_ids: set[str]) -> bool:
    """True if every record ID (`INV-1001`, `PAY-2001`, `C001`-style)
    mentioned in `output` is in `allowed_ids` -- the actual
    invoice/payment/customer IDs the batch this explanation covers.
    Catches the model citing a specific example that was never in its
    input (e.g. naming a different invoice than the ones it was shown)."""
    output_ids = {match.group().upper() for match in _ID_RE.finditer(output)}
    if not output_ids:
        return True
    allowed = {id_.upper() for id_ in allowed_ids}
    return output_ids <= allowed
