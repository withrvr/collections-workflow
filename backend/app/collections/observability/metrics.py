"""Prometheus collectors exposed at /metrics.

Formally built in Phase 12 (MASTER_PLAN.md), where a real Prometheus
`Counter` and a `/metrics` scrape endpoint land as actual requirements
with a real consumer. Phase 6 needs `llm_calls_total` to exist and be
checkable now (its own done-when: "llm_calls_total shows local calls
succeeding") -- this is a plain in-process counter, the seam Phase 12
upgrades to `prometheus_client.Counter` in place; call sites elsewhere
in `collections/` do not change when it does.
"""

from __future__ import annotations

from collections import Counter

_llm_calls: Counter[tuple[str, str]] = Counter()


def increment_llm_calls(rung: str, status: str) -> None:
    """`rung` is "ollama"/"cloud"; `status` is "success"/"error"/"guard_rejected"."""
    _llm_calls[(rung, status)] += 1


def llm_calls_total(rung: str | None = None, status: str | None = None) -> int:
    return sum(
        count
        for (call_rung, call_status), count in _llm_calls.items()
        if (rung is None or call_rung == rung)
        and (status is None or call_status == status)
    )


def reset_llm_calls() -> None:
    """Test-only: clears the counter between test cases."""
    _llm_calls.clear()
