"""
Cloud Waste Hunter - Main FastAPI Application
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import api_router
from app.database import close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Startup: Nothing needed (tables already exist from one-time setup)
    Shutdown: Close database connection pool
    """
    yield
    # Shutdown: Close database connections
    await close_db()


app = FastAPI(
    title="Cloud Waste Hunter API",
    description="Automated AWS Cost Optimization with ML-Powered Waste Detection",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "cloud-waste-hunter", "version": "1.0.0"}


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",  # TODO: Add actual DB health check
        "aws": "configured",  # TODO: Add AWS connectivity check
    }
