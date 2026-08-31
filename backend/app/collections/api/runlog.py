"""GET /run-log/{id}/events: the user-visible run timeline. Populated in Phase 4 (MASTER_PLAN.md)."""

from fastapi import APIRouter

router = APIRouter(prefix="/run-log", tags=["collections"])
