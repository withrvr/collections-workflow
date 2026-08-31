"""The pipeline error contract: every user-facing run failure is one of these,
never a raw traceback (MASTER_PLAN.md section 7).

`code` is a stable machine code the frontend can key off of (e.g. to pick an
icon), `user_message` is written for a finance person reading a run's
timeline, `stage` is the pipeline stage that raised it, and `detail` is
extra structured context for the log / the expandable event detail --
never a substitute for `user_message`.

`service.py`'s orchestrator is the only place that catches this: every
`ingest`/`validate`/`calculate` exception either already is a
PipelineError, or gets translated into one at the stage boundary. Nothing
downstream of that boundary should ever see a bare KeyError/ValueError.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PipelineError(Exception):
    code: str
    stage: str
    user_message: str
    detail: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        Exception.__init__(self, self.user_message)

    def __str__(self) -> str:
        return f"[{self.code}] {self.user_message}"
