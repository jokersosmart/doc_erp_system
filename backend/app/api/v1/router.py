"""API v1 router - assembles all endpoint routers."""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, attributes, documents, partitions, projects

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(projects.router, prefix="/projects", tags=["Projects"])
router.include_router(partitions.router, prefix="/partitions", tags=["Partitions"])
router.include_router(documents.router, prefix="/documents", tags=["Documents"])
router.include_router(
    attributes.router, prefix="/attribute-definitions", tags=["Attribute Definitions"]
)
