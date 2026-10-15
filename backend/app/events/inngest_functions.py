
"""Inngest SDK registrations for the IKIP document pipeline."""

import inngest
import inngest.fast_api as inngest_fast_api

from app.core.config import settings
from app.events.processing_handler import handle_document_uploaded
from app.events.knowledge_handler import handle_document_processed
from app.events.ontology_handler import handle_knowledge_extracted
from app.events.graph_handler import handle_ontology_updated
from app.events.embedding_handler import handle_graph_updated


# The SDK client serves incoming events from the Inngest Dev Server.
# Keep the existing custom InngestClient for sending events.
inngest_client = inngest.Inngest(
    app_id="ikip-backend",
    event_key=settings.INNGEST_EVENT_KEY or None,
    signing_key=settings.INNGEST_SIGNING_KEY or None,
    is_production=not settings.is_development,
)


@inngest_client.create_function(
    fn_id="ikip-process-uploaded-document",
    trigger=inngest.TriggerEvent(event="document.uploaded"),
)
async def process_uploaded_document(ctx,step):
    data = ctx.event.data

    return await handle_document_uploaded(
        document_id=data["document_id"],
        storage_path=data["storage_path"],
        mime_type=data["mime_type"],
        file_size=data["file_size"],
        original_filename=data["original_filename"],
        user_id=data.get("user_id"),
    )


@inngest_client.create_function(
    fn_id="ikip-extract-knowledge",
    trigger=inngest.TriggerEvent(event="document.processed"),
)
async def extract_knowledge(ctx,step):
    data = ctx.event.data

    return await handle_document_processed(
        document_id=data["document_id"],
        canonical_storage_path=data["canonical_storage_path"],
        original_filename=data.get("original_filename", ""),
        user_id=data.get("user_id"),
    )


@inngest_client.create_function(
    fn_id="ikip-update-ontology",
    trigger=inngest.TriggerEvent(event="knowledge.extracted"),
)
async def update_ontology(ctx,step):
    data = ctx.event.data

    return await handle_knowledge_extracted(
        document_id=data["document_id"],
        knowledge_id=data["knowledge_id"],
        confidence=data["confidence"],
        user_id=data.get("user_id"),
    )


@inngest_client.create_function(
    fn_id="ikip-build-knowledge-graph",
    trigger=inngest.TriggerEvent(event="ontology.updated"),
)
async def build_knowledge_graph(ctx,step):
    data = ctx.event.data

    return await handle_ontology_updated(
        document_id=data["document_id"],
        nko_storage_path=data.get("nko_storage_path"),
        entity_count=data.get("entity_count", 0),
        relationship_count=data.get("relationship_count", 0),
        user_id=data.get("user_id"),
    )


@inngest_client.create_function(
    fn_id="ikip-create-embeddings",
    trigger=inngest.TriggerEvent(event="graph.updated"),
)
async def create_embeddings(ctx,step):
    data = ctx.event.data

    return await handle_graph_updated(
        document_id=data["document_id"],
        nodes_written=data.get("nodes_written", 0),
        relationships_written=data.get("relationships_written", 0),
        user_id=data.get("user_id"),
    )


inngest_functions = [
    process_uploaded_document,
    extract_knowledge,
    update_ontology,
    build_knowledge_graph,
    create_embeddings,
]


def register_inngest(app):
    """Expose the Inngest SDK endpoint through FastAPI."""
    inngest_fast_api.serve(
        app,
        inngest_client,
        inngest_functions,
        serve_path="/api/inngest",
    )
