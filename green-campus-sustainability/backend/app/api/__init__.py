"""API package — main router combining all sub-routers."""
from fastapi import APIRouter
from backend.app.api import (
    health, buildings, datasets, audit,
    analytics, actions, verification, reports, settings_api,
)

router = APIRouter()
router.include_router(health.router,        prefix="/health",       tags=["Health"])
router.include_router(buildings.router,     prefix="/buildings",    tags=["Buildings"])
router.include_router(datasets.router,      prefix="/datasets",     tags=["Datasets"])
router.include_router(audit.router,         prefix="/audit",        tags=["Audit"])
router.include_router(analytics.router,     prefix="/analytics",    tags=["Analytics"])
router.include_router(actions.router,       prefix="/actions",      tags=["Actions"])
router.include_router(verification.router,  prefix="/verification", tags=["Verification"])
router.include_router(reports.router,       prefix="/reports",      tags=["Reports"])
router.include_router(settings_api.router,  prefix="/settings",     tags=["Settings"])
