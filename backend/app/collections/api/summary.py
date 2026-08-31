"""The management summary endpoint, including the control-gate blocked payload.

Populated in Phase 4/5 (MASTER_PLAN.md).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/summary", tags=["collections"])
