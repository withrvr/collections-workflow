"""Aggregates every collections route module into one router.

Wired into the template's app/api/main.py with a single include_router
line, so that file stays the only template file this service touches.
"""

from fastapi import APIRouter

from app.collections.api import (
    exceptions,
    mappings,
    overdue,
    regions,
    runlog,
    runs,
    summary,
)

router = APIRouter(prefix="/collections")
router.include_router(runs.router)
router.include_router(overdue.router)
router.include_router(exceptions.router)
router.include_router(regions.router)
router.include_router(summary.router)
router.include_router(runlog.router)
router.include_router(mappings.router)
