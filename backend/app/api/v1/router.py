"""
API v1 Router

Central router that registers all v1 API endpoints.
New endpoints must be added here.

Pattern: router.include_router(module.router, prefix="/prefix", tags=["Tag"])
"""

from fastapi import APIRouter
from app.api.v1 import health, documents

api_router = APIRouter()

# Health Check
api_router.include_router(health.router)

# Documents (Phase 1 — Upload)
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])

# Future routes registered as each Epic is completed:
# from app.api.v1 import auth, graph, assets, search, chat
# from app.api.v1 import compliance, maintenance, dashboard, users, admin
#
# api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
# api_router.include_router(graph.router, prefix="/graph", tags=["Knowledge Graph"])
# api_router.include_router(assets.router, prefix="/assets", tags=["Assets"])
# api_router.include_router(search.router, prefix="/search", tags=["Search"])
# api_router.include_router(chat.router, prefix="/chat", tags=["AI Copilot"])
# api_router.include_router(compliance.router, prefix="/compliance", tags=["Compliance"])
# api_router.include_router(maintenance.router, prefix="/maintenance", tags=["Maintenance"])
# api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
# api_router.include_router(users.router, prefix="/users", tags=["Users"])
# api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
