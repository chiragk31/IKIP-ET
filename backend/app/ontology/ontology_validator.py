"""
Ontology Validator
"""

import structlog
from app.ontology.models import NormalizedKnowledgeObject

logger = structlog.get_logger(__name__)


class OntologyValidator:
    """
    Validates the final NormalizedKnowledgeObject before it is passed downstream.
    """

    def validate(self, nko: NormalizedKnowledgeObject) -> bool:
        """
        Perform a final sanity check on the normalized data.
        Returns True if valid, False otherwise.
        """
        if not nko.document_id:
            logger.error("nko_missing_document_id")
            return False

        if not nko.entities and not nko.relationships:
            logger.warning("nko_empty", document_id=nko.document_id)
            # Technically valid, just empty. We'll allow it but log it.
            return True

        # Check for referential integrity one last time
        entity_ids = {e.entity_id for e in nko.entities}
        for rel in nko.relationships:
            if rel.source_id not in entity_ids or rel.target_id not in entity_ids:
                logger.error(
                    "nko_referential_integrity_failed",
                    document_id=nko.document_id,
                    source_id=rel.source_id,
                    target_id=rel.target_id,
                )
                return False

        logger.info("nko_validation_passed", document_id=nko.document_id)
        return True
