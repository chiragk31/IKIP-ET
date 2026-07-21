"""
Ontology API Endpoints
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
import structlog

from app.core.dependencies import get_ontology_manager, get_knowledge_repository
from app.ontology.ontology_manager import OntologyManager
from app.repositories.knowledge_repository import KnowledgeRepository
from app.utils.response import success_response, error_response

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post(
    "/{document_id}/normalize",
    summary="Trigger ontology normalization for an extracted document",
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_normalization(
    document_id: str,
    background_tasks: BackgroundTasks,
    ontology_manager: OntologyManager = Depends(get_ontology_manager),
    knowledge_repo: KnowledgeRepository = Depends(get_knowledge_repository),
):
    """
    Manually trigger the ontology normalization pipeline for a document.
    Requires that the knowledge extraction pipeline (Epic 3) has completed.
    
    In production, this is triggered automatically by the `knowledge.extracted` event.
    """
    logger.info("ontology_normalization_trigger", document_id=document_id)

    # Verify CKO exists
    record = knowledge_repo.get_record(document_id)
    if not record or record.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge extraction not completed for document {document_id}",
        )

    async def run_normalization():
        try:
            cko = knowledge_repo.load(document_id)
            if not cko:
                logger.error("failed_to_load_cko_for_normalization", document_id=document_id)
                return
            
            nko = ontology_manager.process(cko)
            if nko:
                logger.info("ontology_normalization_successful", document_id=document_id)
                # In the future, emit ontology.updated event here for manual triggers
                # Currently the event handler handles event emission.
        except Exception as e:
            logger.error("background_normalization_failed", document_id=document_id, error=str(e))

    background_tasks.add_task(run_normalization)

    return success_response(
        message="Ontology normalization started",
        data={"document_id": document_id, "status": "normalizing"},
        status_code=status.HTTP_202_ACCEPTED,
    )
