"""
HealthLink - Smart Health Management System
Main FastAPI application entry point.
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from config.settings import get_settings
from config.logging import setup_logging
from api.routes import router
from core.database import get_db_manager
from core.rag import load_knowledge_base


settings = get_settings()
logger = setup_logging(log_level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    logger.info("Starting HealthLink application...")

    try:
        settings.validate_config()
    except ValueError as e:
        logger.warning(
            f"Configuration incomplete: {e}. "
            "The app will start but AI features will be unavailable until keys are set."
        )

    try:
        db_manager = get_db_manager(settings)
        logger.info("Database initialized successfully")

        from core.database import seed_doctors
        import json

        doctors_file = "./data/doctors.csv"
        if os.path.exists(doctors_file):
            import pandas as pd
            doctors_df = pd.read_csv(doctors_file)
            doctors_data = doctors_df.to_dict('records')

            with db_manager.session_scope() as session:
                seed_doctors(session, doctors_data)
            logger.info("Database seeded with doctor data")
        else:
            logger.warning(f"Doctors data file not found: {doctors_file}")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)

    try:
        kb_file = "./data/symptoms_kb.json"
        if not settings.enable_rag:
            logger.info("RAG disabled (ENABLE_RAG=false); skipping knowledge base load")
        elif os.path.exists(kb_file):
            load_knowledge_base(kb_file, settings)
            logger.info("Knowledge base loaded successfully")
        else:
            logger.warning(f"Knowledge base file not found: {kb_file}")
    except Exception as e:
        logger.error(f"RAG initialization failed: {e}", exc_info=True)

    logger.info("HealthLink startup complete")

    yield

    logger.info("Shutting down HealthLink...")
    logger.info("Shutdown complete")


app = FastAPI(
    title="HealthLink API",
    description="Smart Health Management System with AI-powered symptom analysis and doctor recommendations",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later.",
            "detail": str(exc) if settings.log_level == "DEBUG" else None
        }
    )


app.include_router(router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Static frontend (React)
#
# When the React app has been built (frontend/dist exists), FastAPI serves it
# from the same origin: "/" returns index.html, hashed assets are served from
# /assets, and unknown non-API paths fall back to index.html for client-side
# routing. Because it's the same origin, the React app calls "/api/..." with no
# CORS involved.
#
# When dist is absent (local API-only dev), "/" returns the JSON info response.
# ---------------------------------------------------------------------------
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")
_frontend_built = os.path.isdir(FRONTEND_DIST) and os.path.isfile(
    os.path.join(FRONTEND_DIST, "index.html")
)


@app.get("/api", tags=["Root"])
async def api_info():
    """API information (always available, even when the SPA is served at /)."""
    return {
        "name": "HealthLink API",
        "version": "1.0.0",
        "description": "Smart Health Management System",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


if _frontend_built:
    # Serve hashed build assets.
    app.mount(
        "/assets",
        StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")),
        name="assets",
    )

    @app.get("/", include_in_schema=False)
    async def serve_index():
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """
        SPA fallback. Serve a real static file if it exists (e.g. favicon),
        otherwise return index.html so client-side routing works. API, docs and
        openapi paths are already matched by their own routes above, so they
        never reach this handler.
        """
        candidate = os.path.join(FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

    logger.info(f"Serving React frontend from {FRONTEND_DIST}")
else:
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint with API information (frontend not built)."""
        return {
            "name": "HealthLink API",
            "version": "1.0.0",
            "description": "Smart Health Management System",
            "docs": "/docs",
            "health": "/api/v1/health",
            "frontend": "not built — run `npm run build` in ./frontend",
        }
    logger.info("React frontend not built; serving JSON root at /")


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting server on {settings.api_host}:{settings.api_port}")

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower()
    )