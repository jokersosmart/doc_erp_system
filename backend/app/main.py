"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import ai, auth, documents, projects, spec_items
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup checks."""
    logger.info("DocERP backend starting — env=%s", settings.APP_ENV)
    # Future: Celery worker healthcheck, vector store init
    yield
    logger.info("DocERP backend shutting down")


app = FastAPI(
    title="DocERP API",
    version="0.1.0",
    description="Spec-Driven Document Management System for Siliconmotion",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    lifespan=lifespan,
)

# ── CORS (internal network only in production) ────────────────────────────────
allowed_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
if settings.APP_ENV == "production":
    # Restrict to internal network in production
    allowed_origins = ["http://doce-erp.siliconmotion.internal"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request ID middleware ─────────────────────────────────────────────────────
@app.middleware("http")
async def add_request_id(request: Request, call_next):  # type: ignore[no-untyped-def]
    import uuid
    request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ── Global error handler ──────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(spec_items.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")
# Additional routers (audit, fmeda, spec_items) added per phase


@app.get("/api/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}
