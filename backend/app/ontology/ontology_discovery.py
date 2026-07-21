"""
Ontology Discovery
"""

from typing import List
import structlog
from app.schemas.knowledge import NewOntologyConcept
from app.ontology.models import DiscoveredConcept
from app.ontology.constants import CORE_ENTITY_TYPES

logger = structlog.get_logger(__name__)


class OntologyDiscovery:
    """
    Processes new concepts suggested by AI for ontology enrichment.
    """

    def process(
        self, document_id: str, new_concepts: List[NewOntologyConcept]
    ) -> List[DiscoveredConcept]:
        """
        Filter and map new concepts. Ensure they aren't already in core types.
        """
        discovered: List[DiscoveredConcept] = []

        for concept in new_concepts:
            # 1. Ensure it's not already a core type (basic string matching)
            name = concept.concept_name.strip()
            if not name or name.title() in CORE_ENTITY_TYPES:
                logger.debug("concept_already_core_type", concept=name)
                continue

            # 2. Map to DiscoveredConcept model
            discovered.append(
                DiscoveredConcept(
                    concept_name=name,
                    category=concept.category.strip(),
                    description=concept.description.strip(),
                    confidence=concept.confidence,
                    justification=concept.justification.strip(),
                    source_document_id=document_id,
                )
            )

        logger.info(
            "ontology_concepts_discovered",
            raw_count=len(new_concepts),
            processed_count=len(discovered),
        )
        return discovered
