"""PGA Backend - FastAPI Application Entry Point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import assessment, framework, framework_docs, questionnaire

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown."""
    logger.info("Starting PGA Backend...")
    logger.info("PGA Backend started successfully")

    yield

    logger.info("Shutting down PGA Backend...")
    logger.info("PGA Backend shutdown complete")


app = FastAPI(
    title="PGA Backend",
    description="Policy Gap Analysis API - Compliance analysis for BNM RMIT and ISO 27001:2022",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for frontend (configurable via CORS_ORIGINS env var, comma-separated)
from app.config import get_settings

_settings = get_settings()
_cors_origins = [origin.strip() for origin in _settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(assessment.router)
app.include_router(framework.router)
app.include_router(framework_docs.router)
app.include_router(questionnaire.router)


@app.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint for monitoring.

    Returns overall health status and Supabase connectivity.
    """
    health = {"status": "healthy", "services": {}}

    # Check Supabase
    try:
        from app.db.supabase import get_async_supabase_client_async

        sb = await get_async_supabase_client_async()
        # Simple connectivity check
        await sb.table("clients").select("id", count="exact").limit(0).execute()
        health["services"]["supabase"] = {"status": "healthy"}
    except Exception as e:
        health["services"]["supabase"] = {"status": "unavailable", "error": str(e)}
        health["status"] = "degraded"

    return health
