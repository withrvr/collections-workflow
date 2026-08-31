"""Collections service configuration.

REPORT_DATE anchors every calculation to the workbook's stated reporting
date. It is read from the workbook README sheet when present and is never
derived from the clock (see AGENTS.md). The rest of this module is
populated in Phase 1+ of MASTER_PLAN.md (thresholds, LLM settings).
"""

from __future__ import annotations

import datetime


class CollectionsSettings:
    REPORT_DATE: datetime.date = datetime.date(2026, 7, 31)


settings = CollectionsSettings()
