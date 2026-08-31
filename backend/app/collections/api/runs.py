"""POST /run to start a run, GET /runs to list them. Populated in Phase 4 (MASTER_PLAN.md)."""

from fastapi import APIRouter

router = APIRouter(prefix="/runs", tags=["collections"])
