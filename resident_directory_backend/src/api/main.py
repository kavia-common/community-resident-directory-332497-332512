from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.core.settings import settings
from src.api.routers.announcements import router as announcements_router
from src.api.routers.audit import router as audit_router
from src.api.routers.auth import router as auth_router
from src.api.routers.invitations import router as invitations_router
from src.api.routers.realtime import router as realtime_router
from src.api.routers.residents import router as residents_router

openapi_tags = [
    {"name": "Auth", "description": "Authentication endpoints (JWT)."},
    {"name": "Invitations", "description": "Admin-managed invitations and onboarding/signup flow."},
    {"name": "Residents", "description": "Resident profiles, directory search, and privacy-enforced access."},
    {"name": "Announcements", "description": "Announcements REST endpoints and live update broadcasting."},
    {"name": "Realtime", "description": "WebSocket endpoints for live updates."},
    {"name": "Audit", "description": "Admin-only audit logs."},
]


app = FastAPI(
    title="Resident Directory Backend",
    description=(
        "Backend API for the Resident Directory app.\n\n"
        "WebSocket usage:\n"
        "- Connect to `/realtime/announcements?token=<JWT>` for live announcement events.\n"
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_allow_origins.split(",")] if settings.cors_allow_origins != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/",
    summary="Health check",
    description="Health check endpoint for deployment monitoring.",
    tags=["Auth"],
)
def health_check():
    return {"message": "Healthy"}


@app.get(
    "/docs/realtime",
    summary="Realtime (WebSocket) usage help",
    description="Documentation helper describing how to connect to WebSocket endpoints.",
    tags=["Realtime"],
)
def realtime_docs():
    return {
        "websocket_endpoints": [
            {
                "path": "/realtime/announcements",
                "query_params": {"token": "JWT access token"},
                "events": ["announcement.created", "announcement.updated"],
            }
        ]
    }


app.include_router(auth_router)
app.include_router(invitations_router)
app.include_router(residents_router)
app.include_router(announcements_router)
app.include_router(realtime_router)
app.include_router(audit_router)
