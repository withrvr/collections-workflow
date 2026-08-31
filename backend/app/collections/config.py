"""Collections service configuration.

REPORT_DATE anchors every calculation to the workbook's stated reporting
date. It is read from the workbook README sheet when present and is never
derived from the clock (see AGENTS.md). The rest of this module is
populated in Phase 1+ of MASTER_PLAN.md (thresholds, LLM settings).

LLM settings (Phase 6): local Ollama is the default and the only one
required -- COLLECTIONS_OLLAMA_API_BASE/MODEL point at it, always. A
cloud rung is opt-in only: COLLECTIONS_CLOUD_LLM_MODEL unset (the
default) means ai/roles/summary_narrator.py skips straight from Ollama
to the deterministic fallback, never requiring a cloud API key to run.
"""

from __future__ import annotations

import datetime
import os


class CollectionsSettings:
    REPORT_DATE: datetime.date = datetime.date(2026, 7, 31)

    OLLAMA_API_BASE: str = os.environ.get(
        "COLLECTIONS_OLLAMA_API_BASE", "http://localhost:11434"
    )
    OLLAMA_MODEL: str = os.environ.get("COLLECTIONS_OLLAMA_MODEL", "phi4-mini")
    # A LiteLLM model string, e.g. "gpt-4o-mini" or "claude-haiku-4-5" --
    # unset by default, and never required for this project to run.
    CLOUD_LLM_MODEL: str | None = os.environ.get("COLLECTIONS_CLOUD_LLM_MODEL") or None
    LLM_TIMEOUT_SECONDS: float = float(
        os.environ.get("COLLECTIONS_LLM_TIMEOUT_SECONDS", "20")
    )


settings = CollectionsSettings()
