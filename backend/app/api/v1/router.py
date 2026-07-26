from fastapi import APIRouter
from app.api.v1 import health, documents, knowledge, ontology, graph, embeddings

api_router = APIRouter()

# Health Check
api_router.include_router(health.router)

# Documents (Phase 1 — Upload)
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])

# Knowledge Extraction (Phase 3 — AI Extraction)
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["Knowledge Extraction"])

# Ontology (Phase 2 — Structural Mapping)
api_router.include_router(ontology.router, prefix="/ontology", tags=["Ontology"])

# Knowledge Graph (Phase 5 — Graph Builder)
api_router.include_router(graph.router, prefix="/graph", tags=["Knowledge Graph"])

# Semantic Embeddings & Search (Phase 6 — Embeddings)
api_router.include_router(embeddings.router, prefix="/embeddings", tags=["Embeddings & Search"])

# Future routes registered as each Epic is completed:
# from app.api.v1 import auth, assets, chat
from app.api.v1 import search, chat, assets
# from app.api.v1 import compliance, maintenance, dashboard, users, admin
#
# api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
# api_router.include_router(assets.router, prefix="/assets", tags=["Assets"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(chat.router, prefix="/chat", tags=["AI Copilot"])
api_router.include_router(assets.router, prefix="/assets", tags=["Asset Intelligence"])
# api_router.include_router(compliance.router, prefix="/compliance", tags=["Compliance"])
# api_router.include_router(maintenance.router, prefix="/maintenance", tags=["Maintenance"])
# api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
# api_router.include_router(users.router, prefix="/users", tags=["Users"])
# api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
