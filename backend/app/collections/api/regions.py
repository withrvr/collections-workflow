"""The region breakdown endpoint. Populated in Phase 4 (MASTER_PLAN.md)."""

from fastapi import APIRouter

router = APIRouter(prefix="/regions", tags=["collections"])
