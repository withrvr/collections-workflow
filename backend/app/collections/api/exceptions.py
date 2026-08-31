"""The exceptions report endpoint. Populated in Phase 4 (MASTER_PLAN.md)."""

from fastapi import APIRouter

router = APIRouter(prefix="/exceptions", tags=["collections"])
