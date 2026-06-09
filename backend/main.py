"""
main.py – FastAPI application factory with lifespan (MongoDB + Beanie init)
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from backend.config import settings
from backend.middleware.rate_limiter import limiter, rate_limit_exceeded_handler
from backend.models.db_models import User, DocumentRecord, QueryLog, UsageStat
from backend.routers import auth, documents, query, stats

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


# ─── Lifespan (startup / shutdown) ───────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: connect to MongoDB and initialise Beanie ODM
    logger.info("Connecting to MongoDB...")
    motor_client = AsyncIOMotorClient(settings.mongodb_url)
    await init_beanie(
        database=motor_client[settings.mongodb_db_name],
        document_models=[User, DocumentRecord, QueryLog, UsageStat],
    )
    logger.info("MongoDB connected ✓")
    yield
    # Shutdown
    motor_client.close()
    logger.info("MongoDB disconnected")


# ─── App factory ──────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="Multi-Tenant RAG SaaS API",
        description=(
            "Per-user isolated knowledge bases powered by "
            "Pinecone · Gemini Embeddings · Groq LLaMA · MongoDB"
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── Slowapi rate limiter state ────────────────────────────────────────────
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(auth.router,      prefix="/api/v1")
    app.include_router(documents.router, prefix="/api/v1")
    app.include_router(query.router,     prefix="/api/v1")
    app.include_router(stats.router,     prefix="/api/v1")

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["System"])
    async def health():
        return {"status": "ok", "version": "1.0.0"}

    # ── Global exception handler ──────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error. Please try again later."},
        )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app_env == "development",
        log_level=settings.log_level.lower(),
    )
