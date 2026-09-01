"""Developer-facing logging: the "for you, debugging" channel from
MASTER_PLAN.md section 7's three-channel table. `observability/events.py`
is the other channel, "for the user".

Plain stdlib `logging` for now, not structlog -- Phase 12 (MASTER_PLAN.md,
presentation scope) is where structlog JSON output and the `/metrics`
Prometheus endpoint land as real requirements with real consumers (a log
aggregator, a scrape target). Adding structlog here in Phase 3 for a
single `logger.exception()` call would be a dependency with no reader
yet. `get_logger` is the seam Phase 12 upgrades in place; call sites
elsewhere in `collections/` do not change when it does.
"""

from __future__ import annotations

import logging


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
