"""
Entity Mapper
"""

from typing import Dict, List, Tuple
import structlog
from app.schemas.knowledge import ExtractedEntity
from app.ontology.models import NormalizedEntity
from app.ontology.synonym_resolver import SynonymResolver
from app.ontology.alias_resolver import AliasResolver
from app.ontology.constants import CORE_ENTITY_TYPES

logger = structlog.get_logger(__name__)


class EntityMapper:
    """
    Maps and normalizes extracted entities into NormalizedEntities.
    Handles deduplication, synonym resolution, and alias merging.
    """

    def __init__(self) -> None:
        self.synonym_resolver = SynonymResolver()
        self.alias_resolver = AliasResolver()

    def normalize_entities(
        self, document_id: str, raw_entities: List[ExtractedEntity]
    ) -> List[NormalizedEntity]:
        """
        Convert raw ExtractedEntity objects into NormalizedEntity objects,
        merging duplicates and resolving names.
        """
        normalized_map: Dict[str, NormalizedEntity] = {}

        for raw in raw_entities:
            # 1. Normalize type
            entity_type = self.synonym_resolver.resolve_type(raw.entity_type)
            if entity_type not in CORE_ENTITY_TYPES:
                # Map unknown types to "Concept" or keep them if dynamic ontology is allowed
                # We'll keep them but log it
                logger.debug("non_core_entity_type_found", type=entity_type)

            # 2. Normalize label & resolve synonyms
            canonical_name = self.synonym_resolver.resolve_label(raw.label)
            # Try to normalize tags (e.g. Pump P101 -> Pump P-101)
            # A simplistic approach: if it has a tag structure, normalize it.
            # E.g., "Pump P101" -> "Pump P-101"
            parts = canonical_name.split()
            if len(parts) == 2 and parts[0].isalpha():
                norm_tag = self.alias_resolver.normalize_tag(parts[1])
                canonical_name = f"{parts[0]} {norm_tag}"
            else:
                 canonical_name = self.alias_resolver.normalize_tag(canonical_name)

            # 3. Handle Aliases
            aliases = self.alias_resolver.deduplicate_aliases(canonical_name, raw.aliases)
            # Also add the original raw label if it differs from canonical name
            if raw.label != canonical_name and raw.label not in aliases:
                aliases.append(raw.label)

            # 4. Merge Duplicates (by entity_id)
            entity_id = raw.entity_id.strip().lower()

            if entity_id in normalized_map:
                existing = normalized_map[entity_id]
                # Merge aliases
                existing.aliases = list(set(existing.aliases + aliases))
                # Keep highest confidence
                existing.confidence = max(existing.confidence, raw.confidence)
                # Merge properties
                existing.metadata.update(raw.properties)
            else:
                # Create new
                normalized_map[entity_id] = NormalizedEntity(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    canonical_name=canonical_name,
                    aliases=aliases,
                    confidence=raw.confidence,
                    metadata=raw.properties or {},
                    source_document_ids=[document_id],
                )

        result = list(normalized_map.values())
        logger.info(
            "entities_normalized",
            raw_count=len(raw_entities),
            normalized_count=len(result),
        )
        return result
