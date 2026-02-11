"""PGA Backend - FastAPI Application Entry Point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import assessment, framework, framework_docs, knowledge, questions, search
from app.services.neo4j_service import get_neo4j_service
from app.services.qdrant_service import get_qdrant_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown."""
    # Startup: Initialize database connections
    logger.info("Starting PGA Backend...")

    try:
        neo4j = get_neo4j_service()
        await neo4j.initialize()
        logger.info("Neo4j connection initialized")
    except Exception as e:
        logger.warning(f"Neo4j initialization failed (service may be unavailable): {e}")

    try:
        qdrant = get_qdrant_service()
        await qdrant.initialize()
        logger.info("Qdrant connection initialized")
    except Exception as e:
        logger.warning(
            f"Qdrant initialization failed (service may be unavailable): {e}"
        )

    logger.info("PGA Backend started successfully")

    yield

    # Shutdown: Close database connections
    logger.info("Shutting down PGA Backend...")

    try:
        neo4j = get_neo4j_service()
        await neo4j.close()
    except Exception as e:
        logger.warning(f"Error closing Neo4j connection: {e}")

    try:
        qdrant = get_qdrant_service()
        await qdrant.close()
    except Exception as e:
        logger.warning(f"Error closing Qdrant connection: {e}")

    logger.info("PGA Backend shutdown complete")


app = FastAPI(
    title="PGA Backend",
    description="Policy Gap Analysis API - Compliance analysis for BNM RMIT and ISO 27001:2022",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(assessment.router)
app.include_router(framework.router)
app.include_router(knowledge.router)
app.include_router(questions.router)
app.include_router(search.router)
app.include_router(framework_docs.router)


@app.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint for monitoring.

    Returns overall health status and status of each service:
    - neo4j: Knowledge graph database
    - qdrant: Vector search database
    """
    health = {"status": "healthy", "services": {}}

    # Check Neo4j
    try:
        neo4j = get_neo4j_service()
        neo4j_health = await neo4j.health_check()
        health["services"]["neo4j"] = neo4j_health
    except Exception as e:
        health["services"]["neo4j"] = {"status": "unavailable", "error": str(e)}

    # Check Qdrant
    try:
        qdrant = get_qdrant_service()
        qdrant_health = await qdrant.health_check()
        health["services"]["qdrant"] = qdrant_health
    except Exception as e:
        health["services"]["qdrant"] = {"status": "unavailable", "error": str(e)}

    # Overall status is degraded if any service is unhealthy
    for service_name, service_health in health["services"].items():
        if service_health.get("status") not in ("healthy", None):
            health["status"] = "degraded"
            break

    return health
