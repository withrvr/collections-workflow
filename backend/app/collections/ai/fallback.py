"""Deterministic Jinja template summary, the last rung of the LLM
fallback chain (Phase 6 adds the LLM rungs above this one; this rung
always works, no network, no model).

Built in Phase 5 (MASTER_PLAN.md). Deliberately detailed, not a single
terse line -- this is the summary a Docker-run backend actually
produces whenever it can't reach Ollama (container loopback isolation,
see ARCHITECTURE.md), so it needs to stand on its own as a real
management summary, not just a safety-net stub.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal

from jinja2 import Template

from app.collections.control.gate import GateResult

_TEMPLATE = Template(
    "Run against {{ source_filename }} as of {{ report_date }}. "
    "{{ invoice_count }} invoice(s) were processed across {{ customer_count }} "
    "customer(s), producing {{ overdue_count }} overdue invoice(s) totaling "
    "Rs {{ '{:,.2f}'.format(total_outstanding) }}"
    "{% if heaviest_region %} -- {{ heaviest_region }} carries the largest single exposure{% endif %}."
    " "
    "{% if by_region %}Regional breakdown: "
    "{% for region, amount in by_region %}{{ region }} (Rs {{ '{:,.2f}'.format(amount) }})"
    "{% if not loop.last %}, {% endif %}{% endfor %}. "
    "{% endif %}"
    "{% if ageing %}Of that overdue balance, "
    "{% for bucket, amount in ageing %}Rs {{ '{:,.2f}'.format(amount) }} is {{ bucket }} days past due"
    "{% if not loop.last %}, {% endif %}{% endfor %}. "
    "{% endif %}"
    "Validation found {{ gate.exception_count }} exception(s) across "
    "{{ rule_count }} distinct rule(s) ({{ '{:.1%}'.format(gate.exception_row_rate) }} "
    "of invoices by row count, {{ gate.distinct_invoices_affected }} distinct "
    "invoice(s) affected -- {{ '{:.1%}'.format(gate.distinct_invoice_rate) }}). "
    "{% if top_rules %}The most common issues: "
    "{% for code, count in top_rules %}{{ code }} ({{ count }})"
    "{% if not loop.last %}, {% endif %}{% endfor %}. "
    "{% endif %}"
    "{% if gate.status == 'BLOCKED' %}"
    "This run is BLOCKED: the exception rate exceeds the {{ '{:.0%}'.format(gate.threshold) }} "
    "control threshold, so the position above should not be treated as clean "
    "until the flagged rows are corrected at the source and the file is re-run."
    "{% else %}"
    "This run PASSED: the exception rate is within the {{ '{:.0%}'.format(gate.threshold) }} "
    "control threshold, and the figures above are ready to report."
    "{% endif %}"
)


def render_summary(
    *,
    source_filename: str,
    report_date: str,
    customer_count: int,
    invoice_count: int,
    overdue_count: int,
    total_outstanding: Decimal,
    heaviest_region: str | None,
    by_region: Mapping[str, Decimal] | None,
    ageing: Mapping[str, Decimal] | None,
    rule_counts: Mapping[str, int] | None,
    gate: GateResult,
) -> str:
    """Plain-English, deterministic -- no LLM call, always succeeds."""
    sorted_regions: Sequence[tuple[str, Decimal]] = sorted(
        (by_region or {}).items(), key=lambda kv: kv[1], reverse=True
    )
    sorted_ageing: Sequence[tuple[str, Decimal]] = [
        (bucket, amount) for bucket, amount in (ageing or {}).items() if amount > 0
    ]
    sorted_rules: Sequence[tuple[str, int]] = sorted(
        (rule_counts or {}).items(), key=lambda kv: kv[1], reverse=True
    )[:3]

    return _TEMPLATE.render(
        source_filename=source_filename,
        report_date=report_date,
        customer_count=customer_count,
        invoice_count=invoice_count,
        overdue_count=overdue_count,
        total_outstanding=total_outstanding,
        heaviest_region=heaviest_region,
        by_region=sorted_regions,
        ageing=sorted_ageing,
        rule_count=len(rule_counts or {}),
        top_rules=sorted_rules,
        gate=gate,
    )
