"""
Chalkin - Boulder Climbing Tracker API
Track your climbing sessions, log ascents, and monitor progress.
"""
import os
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

# Import routers
from app.routers.auth import router as auth_router
from app.routers.gyms import router as gyms_router
from app.routers.grades import router as grades_router
from app.routers.sessions import router as sessions_router
from app.routers.ascents import router as ascents_router
from app.routers.stats import router as stats_router

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API for tracking boulder climbing sessions and progress",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(auth_router, prefix="/api")
app.include_router(gyms_router, prefix="/api")
app.include_router(grades_router, prefix="/api")
app.include_router(sessions_router, prefix="/api")
app.include_router(ascents_router, prefix="/api")
app.include_router(stats_router, prefix="/api")

# Set the correct paths for static files and templates
base_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(base_dir, "static")
template_dir = os.path.join(static_dir, "templates")

# Serve static files
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=FileResponse)
def serve_index():
    """Serve the main web app."""
    return os.path.join(template_dir, "index.html")


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "app": settings.app_name, "version": settings.app_version}


