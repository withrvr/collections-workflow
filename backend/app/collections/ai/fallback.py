"""Deterministic Jinja template summary, the last rung of the LLM
fallback chain (Phase 6 adds the LLM rungs above this one; this rung
always works, no network, no model).

Built in Phase 5 (MASTER_PLAN.md).
"""

from __future__ import annotations

from decimal import Decimal

from jinja2 import Template

from app.collections.control.gate import GateResult

_TEMPLATE = Template(
    "Run against {{ source_filename }} as of {{ report_date }}: "
    "{{ invoice_count }} invoice(s) processed, {{ overdue_count }} overdue "
    "totaling Rs {{ '{:,.2f}'.format(total_outstanding) }}"
    "{% if heaviest_region %} ({{ heaviest_region }} heaviest){% endif %}. "
    "{{ gate.exception_count }} exception(s) found "
    "({{ '{:.1%}'.format(gate.exception_row_rate) }} of invoices, "
    "{{ gate.distinct_invoices_affected }} distinct invoice(s) affected, "
    "{{ '{:.1%}'.format(gate.distinct_invoice_rate) }}) -- "
    "{% if gate.status == 'BLOCKED' %}"
    "BLOCKED: exceeds the {{ '{:.0%}'.format(gate.threshold) }} control threshold."
    "{% else %}"
    "PASSED: within the {{ '{:.0%}'.format(gate.threshold) }} control threshold."
    "{% endif %}"
)


def render_summary(
    *,
    source_filename: str,
    report_date: str,
    invoice_count: int,
    overdue_count: int,
    total_outstanding: Decimal,
    heaviest_region: str | None,
    gate: GateResult,
) -> str:
    """Plain-English, deterministic -- no LLM call, always succeeds."""
    return _TEMPLATE.render(
        source_filename=source_filename,
        report_date=report_date,
        invoice_count=invoice_count,
        overdue_count=overdue_count,
        total_outstanding=total_outstanding,
        heaviest_region=heaviest_region,
        gate=gate,
    )
