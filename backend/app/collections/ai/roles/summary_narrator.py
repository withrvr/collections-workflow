"""Narrates the frozen metrics dictionary produced by calculate/. Never receives raw sheets.

Built in Phase 6 (MASTER_PLAN.md). Three-rung fallback: local Ollama,
then a configured cloud provider (only attempted if one is set), then
the deterministic Jinja template (`ai/fallback.py`) -- which cannot
fail short of a programming bug, so `narrate()` itself never raises.
Every attempt is numeric-guarded (`ai/guard.py`): a rung whose output
invents a number never in the prompt is rejected, not surfaced.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from app.collections.ai import fallback, guard, provider
from app.collections.control.gate import GateResult
from app.collections.observability import metrics

_PROMPT_TEMPLATE = """You are a senior accounts-receivable analyst writing a management summary of a collections run. Use ONLY the numbers given below -- never invent, estimate, or add any number that is not listed here. Do not use markdown formatting.

Write a detailed 5 to 8 sentence analysis, not a one-liner: state the overall position, call out which region and which ageing bucket carry the most risk, name the most common data-quality issues found, and close with a clear, actionable read on whether this run's numbers are safe to report as-is.

Source file: {source_filename}
Report date: {report_date}
Customers: {customer_count}
Invoices processed: {invoice_count}
Overdue invoices: {overdue_count}
Total outstanding: Rs {total_outstanding:,.2f}
Heaviest region: {heaviest_region}
Region breakdown: {region_breakdown}
Ageing breakdown: {ageing_breakdown}
Exceptions found: {exception_count}
Exception rate: {exception_row_rate:.1%}
Distinct invoices affected: {distinct_invoices_affected} ({distinct_invoice_rate:.1%})
Most common issues: {top_rules}
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
    customer_count: int,
    invoice_count: int,
    overdue_count: int,
    total_outstanding: Decimal,
    heaviest_region: str | None,
    by_region: Mapping[str, Decimal] | None = None,
    ageing: Mapping[str, Decimal] | None = None,
    rule_counts: Mapping[str, int] | None = None,
    gate: GateResult,
) -> NarrativeResult:
    sorted_regions = sorted(
        (by_region or {}).items(), key=lambda kv: kv[1], reverse=True
    )
    sorted_ageing = [(b, a) for b, a in (ageing or {}).items() if a > 0]
    sorted_rules = sorted(
        (rule_counts or {}).items(), key=lambda kv: kv[1], reverse=True
    )[:5]

    context = _PROMPT_TEMPLATE.format(
        source_filename=source_filename,
        report_date=report_date,
        customer_count=customer_count,
        invoice_count=invoice_count,
        overdue_count=overdue_count,
        total_outstanding=total_outstanding,
        heaviest_region=heaviest_region or "none",
        region_breakdown=", ".join(f"{r} Rs {a:,.2f}" for r, a in sorted_regions)
        or "none",
        ageing_breakdown=", ".join(f"{b} days Rs {a:,.2f}" for b, a in sorted_ageing)
        or "none",
        exception_count=gate.exception_count,
        exception_row_rate=gate.exception_row_rate,
        distinct_invoices_affected=gate.distinct_invoices_affected,
        distinct_invoice_rate=gate.distinct_invoice_rate,
        top_rules=", ".join(f"{c} ({n})" for c, n in sorted_rules) or "none",
        threshold=gate.threshold,
        gate_status=gate.status,
    )

    for rung in _RUNGS:
        try:
            text = _CALLS[rung](context, max_tokens=700)
        except provider.LLMError:
            continue
        if guard.numbers_are_contained(text, context):
            return NarrativeResult(text=text, source=rung)
        metrics.increment_llm_calls(rung, "guard_rejected")

    fallback_text = fallback.render_summary(
        source_filename=source_filename,
        report_date=report_date,
        customer_count=customer_count,
        invoice_count=invoice_count,
        overdue_count=overdue_count,
        total_outstanding=total_outstanding,
        heaviest_region=heaviest_region,
        by_region=by_region,
        ageing=ageing,
        rule_counts=rule_counts,
        gate=gate,
    )
    return NarrativeResult(text=fallback_text, source="fallback")
