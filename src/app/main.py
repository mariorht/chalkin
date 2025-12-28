"""
Chalkin - Boulder Climbing Tracker API
Track your climbing sessions, log ascents, and monitor progress.
"""
import os
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
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
from app.routers.social import router as social_router
from app.routers.notifications import router as notifications_router
from app.routers.strava import router as strava_router

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
app.include_router(social_router, prefix="/api")
app.include_router(notifications_router, prefix="/api")
app.include_router(strava_router, prefix="/api")

# Set the correct paths for static files and templates
base_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(base_dir, "static")
template_dir = os.path.join(static_dir, "templates")

# Ensure data/uploads directory exists
data_dir = os.path.abspath(settings.data_dir)
uploads_dir = os.path.join(data_dir, "uploads")
profiles_dir = os.path.join(uploads_dir, "profiles")
try:
    os.makedirs(profiles_dir, exist_ok=True)
except PermissionError:
    # Fallback to a directory relative to the app
    uploads_dir = os.path.join(base_dir, "uploads")
    profiles_dir = os.path.join(uploads_dir, "profiles")
    os.makedirs(profiles_dir, exist_ok=True)

# Custom StaticFiles with cache headers
class CachedStaticFiles(StaticFiles):
    def __init__(self, *args, **kwargs):
        self.cache_max_age = kwargs.pop("cache_max_age", 3600)
        super().__init__(*args, **kwargs)

    async def get_response(self, path: str, scope) -> Response:
        response = await super().get_response(path, scope)
        # Add cache headers for icons and other static assets
        if path.startswith("icons/") or path.endswith((".png", ".jpg", ".svg", ".ico")):
            response.headers["Cache-Control"] = f"public, max-age={self.cache_max_age}"
        return response

# Serve static files with cache headers
app.mount("/static", CachedStaticFiles(directory=static_dir, cache_max_age=86400), name="static")

# Serve manifest.json at root
@app.get("/manifest.json")
async def serve_manifest():
    manifest_path = os.path.join(static_dir, "manifest.json")
    return FileResponse(manifest_path, media_type="application/manifest+json")

# Serve service worker at root scope
# DESACTIVADO TEMPORALMENTE - Descomentar cuando se quiera usar
# @app.get("/sw.js", response_class=FileResponse)
# def serve_sw():
#     return os.path.join(static_dir, "sw.js")

# Serve uploaded files from uploads directory
try:
    app.mount("/data/uploads", StaticFiles(directory=uploads_dir), name="uploads")
except RuntimeError:
    pass  # Directory doesn't exist yet, will be created on first upload


@app.get("/", response_class=FileResponse)
def serve_index():
    """Serve the main web app."""
    return os.path.join(template_dir, "index.html")


@app.get("/login", response_class=FileResponse)
def serve_login():
    """Serve the login page."""
    return os.path.join(template_dir, "login.html")


@app.get("/register", response_class=FileResponse)
def serve_register():
    """Serve the registration page."""
    return os.path.join(template_dir, "register.html")


@app.get("/gyms/new", response_class=FileResponse)
def serve_new_gym():
    """Serve the new gym page."""
    return os.path.join(template_dir, "gym-new.html")


@app.get("/dashboard", response_class=FileResponse)
def serve_dashboard():
    """Serve the dashboard page."""
    return os.path.join(template_dir, "dashboard.html")


@app.get("/sessions/new", response_class=FileResponse)
def serve_new_session():
    """Serve the new session page."""
    return os.path.join(template_dir, "session-new.html")


@app.get("/sessions/{session_id}", response_class=FileResponse)
def serve_session_detail(session_id: int):
    """Serve the session detail page."""
    return os.path.join(template_dir, "session-detail.html")


@app.get("/gyms/edit", response_class=FileResponse)
def serve_gym_edit():
    """Serve the gym edit page."""
    return os.path.join(template_dir, "gym-edit.html")


@app.get("/gyms", response_class=FileResponse)
def serve_gyms_list():
    """Serve the gyms list page."""
    return os.path.join(template_dir, "gyms.html")


@app.get("/sessions", response_class=FileResponse)
def serve_sessions_list():
    """Serve the sessions list page."""
    return os.path.join(template_dir, "sessions.html")


@app.get("/friends", response_class=FileResponse)
def serve_friends():
    """Serve the friends page."""
    return os.path.join(template_dir, "friends.html")


@app.get("/feed", response_class=FileResponse)
def serve_feed():
    """Serve the activity feed page."""
    return os.path.join(template_dir, "feed.html")


@app.get("/stats", response_class=FileResponse)
def serve_stats():
    """Serve the statistics page."""
    return os.path.join(template_dir, "stats.html")


@app.get("/profile", response_class=FileResponse)
def serve_profile():
    """Serve the profile edit page."""
    return os.path.join(template_dir, "profile.html")


@app.get("/support", response_class=FileResponse)
def serve_support():
    """Serve the support page."""
    return os.path.join(template_dir, "support.html")


@app.get("/users", response_class=FileResponse)
def serve_user_profile():
    """Serve the user profile page."""
    return os.path.join(template_dir, "user-profile.html")


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "app": settings.app_name, "version": settings.app_version}


