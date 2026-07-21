"""
Ontology Event Handler
"""

import time
import structlog
from app.ontology.ontology_manager import OntologyManager
from app.core.dependencies import (
    get_supabase_client,
    get_knowledge_repository,
    get_inngest_client,
    get_ontology_manager,
)

logger = structlog.get_logger(__name__)


async def handle_knowledge_extracted(
    document_id: str,
    knowledge_id: str,
    confidence: float,
    user_id: str = None,
) -> dict:
    """
    Process a `knowledge.extracted` event.
    
    Triggers the ontology normalization and validation pipeline (Epic 4),
    converting a CKO into an NKO, and emits the `ontology.updated` event.
    """
    start_time = time.time()

    logger.info(
        "ontology_handler_start",
        document_id=document_id,
        knowledge_id=knowledge_id,
    )

    try:
        supabase = get_supabase_client()
        knowledge_repo = get_knowledge_repository(supabase=supabase)
        inngest = get_inngest_client()
        ontology_manager = get_ontology_manager()
        
        # 1. Load CKO
        cko = knowledge_repo.load(document_id)
        if not cko:
            raise ValueError(f"Failed to load CKO for document {document_id}")
            
        # 2. Process via OntologyManager
        # (OntologyManager.process() now persists the NKO to Storage internally
        # via OntologyRepository.save_nko() before returning it.)
        nko = ontology_manager.process(cko)
        if not nko:
            raise ValueError(f"Ontology validation failed for document {document_id}")
            
        duration = time.time() - start_time

        # NKO storage path — mirrors OntologyRepository.NKO_PATH_TEMPLATE.
        # Included in the event payload so Graph Builder (Epic 5) can load
        # the exact persisted artifact instead of recomputing normalization.
        nko_storage_path = f"normalized/{document_id}/nko.json"

        # 3. Emit ontology.updated event for Graph Builder (Epic 5)
        inngest.send_event(
            event_name="ontology.updated",
            payload={
                "document_id": document_id,
                "nko_storage_path": nko_storage_path,
                "entity_count": len(nko.entities),
                "relationship_count": len(nko.relationships),
            },
            user_id=user_id,
        )

        logger.info(
            "ontology_handler_complete",
            document_id=document_id,
            duration_seconds=round(duration, 2),
            nko_storage_path=nko_storage_path,
        )

        return {
            "document_id": document_id,
            "status": "completed",
            "duration_seconds": round(duration, 2),
            "entity_count": len(nko.entities),
            "relationship_count": len(nko.relationships),
            "nko_storage_path": nko_storage_path,
        }

    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "ontology_handler_failed",
            document_id=document_id,
            error=str(e),
            duration_seconds=round(duration, 2),
        )
        raise