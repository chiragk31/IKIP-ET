"""
Relationship Validator
"""

from typing import List, Set
import structlog
from app.schemas.knowledge import ExtractedRelationship
from app.ontology.models import NormalizedRelationship, NormalizedEntity
from app.ontology.constants import VALID_RELATIONSHIP_TYPES

logger = structlog.get_logger(__name__)


class RelationshipValidator:
    """
    Validates relationships ensuring referential integrity and valid types.
    """

    def validate(
        self,
        raw_relationships: List[ExtractedRelationship],
        normalized_entities: List[NormalizedEntity],
    ) -> List[NormalizedRelationship]:
        """
        Validate relationships against normalized entities and core types.
        """
        valid_entity_ids: Set[str] = {e.entity_id for e in normalized_entities}
        valid_relationships: List[NormalizedRelationship] = []

        for raw in raw_relationships:
            # 1. Validate source and target exist
            if raw.source not in valid_entity_ids:
                logger.debug("relationship_source_not_found", source=raw.source)
                continue
            if raw.target not in valid_entity_ids:
                logger.debug("relationship_target_not_found", target=raw.target)
                continue

            # 2. No self-links
            if raw.source == raw.target:
                logger.debug("relationship_self_link_rejected", source=raw.source)
                continue

            # 3. Validate relationship type
            rel_type = raw.relationship.strip().upper()
            if rel_type not in VALID_RELATIONSHIP_TYPES:
                logger.debug("invalid_relationship_type", type=rel_type)
                continue

            # 4. Confidence threshold check (already done in Epic 3, but good to have)
            if raw.confidence < 0.6: # MIN_RELATIONSHIP_CONFIDENCE
                logger.debug("relationship_low_confidence", confidence=raw.confidence)
                continue
                
            valid_relationships.append(
                NormalizedRelationship(
                    source_id=raw.source,
                    relationship=rel_type,
                    target_id=raw.target,
                    confidence=raw.confidence,
                    metadata=raw.properties or {},
                )
            )

        logger.info(
            "relationships_validated",
            raw_count=len(raw_relationships),
            valid_count=len(valid_relationships),
        )
        return valid_relationships
