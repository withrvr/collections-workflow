"""Post-generation numeric containment check: every number in LLM output must appear in its input.

Built in Phase 6 (MASTER_PLAN.md). The LLM never computes, chooses, or
corrects a number (AGENTS.md) -- it narrates. This is the check that
makes that a guarantee rather than a hope: if the model's output
contains a number that was never in the prompt we gave it, the output
is rejected outright, never surfaced to a user as if it were a real
figure.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

_NUMBER_RE = re.compile(r"\d[\d,]*\.?\d*")


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
