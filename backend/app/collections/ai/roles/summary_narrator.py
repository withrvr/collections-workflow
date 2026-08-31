"""Narrates the frozen metrics dictionary produced by calculate/. Never receives raw sheets.

Built in Phase 6 (MASTER_PLAN.md). Three-rung fallback: local Ollama,
then a configured cloud provider (only attempted if one is set), then
the deterministic Jinja template (`ai/fallback.py`) -- which cannot
fail short of a programming bug, so `narrate()` itself never raises.
Every attempt is numeric-guarded (`ai/guard.py`): a rung whose output
invents a number never in the prompt is rejected, not surfaced.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.collections.ai import fallback, guard, provider
from app.collections.control.gate import GateResult
from app.collections.observability import metrics

_PROMPT_TEMPLATE = """You are writing a one-paragraph management summary of an accounts-receivable run. Use ONLY the numbers given below -- never invent, estimate, or add any number that is not listed here. Do not use markdown formatting. Write 2 to 4 plain-English sentences.

Source file: {source_filename}
Report date: {report_date}
Invoices processed: {invoice_count}
Overdue invoices: {overdue_count}
Total outstanding: Rs {total_outstanding:,.2f}
Heaviest region: {heaviest_region}
Exceptions found: {exception_count}
Exception rate: {exception_row_rate:.1%}
Control threshold: {threshold:.0%}
Gate status: {gate_status}
"""

_RUNGS = ("ollama", "cloud")
_CALLS = {"ollama": provider.call_ollama, "cloud": provider.call_cloud}


@dataclass(frozen=True, slots=True)
class NarrativeResult:
    text: str
    source: str  # "ollama" | "cloud" | "fallback"


def narrate(
    *,
    source_filename: str,
    report_date: str,
    invoice_count: int,
    overdue_count: int,
    total_outstanding: Decimal,
    heaviest_region: str | None,
    gate: GateResult,
) -> NarrativeResult:
    context = _PROMPT_TEMPLATE.format(
        source_filename=source_filename,
        report_date=report_date,
        invoice_count=invoice_count,
        overdue_count=overdue_count,
        total_outstanding=total_outstanding,
        heaviest_region=heaviest_region or "none",
        exception_count=gate.exception_count,
        exception_row_rate=gate.exception_row_rate,
        threshold=gate.threshold,
        gate_status=gate.status,
    )

    for rung in _RUNGS:
        try:
            text = _CALLS[rung](context)
        except provider.LLMError:
            continue
        if guard.numbers_are_contained(text, context):
            return NarrativeResult(text=text, source=rung)
        metrics.increment_llm_calls(rung, "guard_rejected")

    fallback_text = fallback.render_summary(
        source_filename=source_filename,
        report_date=report_date,
        invoice_count=invoice_count,
        overdue_count=overdue_count,
        total_outstanding=total_outstanding,
        heaviest_region=heaviest_region,
        gate=gate,
    )
    return NarrativeResult(text=fallback_text, source="fallback")
