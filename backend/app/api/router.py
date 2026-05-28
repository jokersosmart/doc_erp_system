"""Top-level API router composition."""

from fastapi import APIRouter

from app.api.routes.ai_reviews import router as ai_reviews_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.documents import router as documents_router
from app.api.routes.exports import router as exports_router
from app.api.routes.imports import router as imports_router
from app.api.routes.traceability import router as traceability_router

api_router = APIRouter()
api_router.include_router(documents_router)
api_router.include_router(traceability_router)
api_router.include_router(ai_reviews_router)
api_router.include_router(exports_router)
api_router.include_router(dashboard_router)
api_router.include_router(imports_router)
