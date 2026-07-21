"""
Ontology Repository
"""

import json
import uuid
from typing import List, Optional
import structlog
from app.database.supabase import SupabaseClient
from app.ontology.models import DiscoveredConcept, NormalizedKnowledgeObject

logger = structlog.get_logger(__name__)

CONCEPTS_TABLE = "ontology_concepts"
STORAGE_BUCKET = "documents"
NKO_PATH_TEMPLATE = "normalized/{document_id}/nko.json"


class OntologyRepository:
    """
    Persistence layer for ontology output.

    Responsibilities:
    - Save/load the NormalizedKnowledgeObject (NKO) JSON to Storage —
      this is the artifact Graph Builder (Epic 5) consumes.
    - Save discovered concepts to the `ontology_concepts` table for
      human review.
    """

    def __init__(self, supabase: SupabaseClient) -> None:
        self._supabase = supabase

    # ------------------------------------------------------------------
    # NKO persistence (new)
    # ------------------------------------------------------------------

    def save_nko(self, nko: NormalizedKnowledgeObject) -> str:
        """
        Persist the NormalizedKnowledgeObject to Supabase Storage.

        Mirrors the CKO storage pattern from Epic 3
        (knowledge/{document_id}/cko.json) so downstream modules can
        rely on a predictable, versioned artifact rather than
        recomputing normalization.

        Args:
            nko: The validated NormalizedKnowledgeObject

        Returns:
            The storage path the NKO was written to.

        Raises:
            Exception if the upload fails — callers should NOT swallow
            this, since a "successful" normalization with no persisted
            artifact is worse than a visible failure.
        """
        storage_path = NKO_PATH_TEMPLATE.format(document_id=nko.document_id)
        payload = nko.model_dump_json(indent=None).encode("utf-8")

        try:
            self._supabase.client.storage.from_(STORAGE_BUCKET).upload(
                path=storage_path,
                file=payload,
                file_options={
                    "content-type": "application/json",
                    "upsert": "true",  # allow reprocessing to overwrite
                },
            )
        except Exception as e:
            logger.error(
                "failed_to_save_nko",
                document_id=nko.document_id,
                storage_path=storage_path,
                error=str(e),
            )
            raise

        logger.info(
            "nko_saved",
            document_id=nko.document_id,
            storage_path=storage_path,
            entities=len(nko.entities),
            relationships=len(nko.relationships),
        )
        return storage_path

    def load_nko(self, document_id: str) -> Optional[NormalizedKnowledgeObject]:
        """
        Load a previously persisted NormalizedKnowledgeObject.

        Args:
            document_id: The document whose NKO to load

        Returns:
            NormalizedKnowledgeObject, or None if not found / not yet processed.
        """
        storage_path = NKO_PATH_TEMPLATE.format(document_id=document_id)

        try:
            raw_bytes = self._supabase.client.storage.from_(STORAGE_BUCKET).download(
                storage_path
            )
        except Exception as e:
            logger.warning(
                "nko_not_found",
                document_id=document_id,
                storage_path=storage_path,
                error=str(e),
            )
            return None

        try:
            data = json.loads(raw_bytes)
            return NormalizedKnowledgeObject(**data)
        except Exception as e:
            logger.error(
                "failed_to_parse_nko",
                document_id=document_id,
                storage_path=storage_path,
                error=str(e),
            )
            return None

    # ------------------------------------------------------------------
    # Discovered concepts (existing)
    # ------------------------------------------------------------------

    def save_discovered_concepts(
        self, concepts: List[DiscoveredConcept]
    ) -> int:
        """
        Save newly discovered concepts to Supabase.

        Args:
            concepts: List of DiscoveredConcept objects

        Returns:
            Number of concepts saved
        """
        if not concepts:
            return 0

        saved_count = 0
        for concept in concepts:
            try:
                data = {
                    "id": str(uuid.uuid4()),
                    "concept_name": concept.concept_name,
                    "category": concept.category,
                    "description": concept.description,
                    "confidence": concept.confidence,
                    "justification": concept.justification,
                    "source_document_id": concept.source_document_id,
                    "status": "pending",  # Requires human review before adding to core
                }

                response = (
                    self._supabase.client.table(CONCEPTS_TABLE)
                    .select("id")
                    .eq("concept_name", concept.concept_name)
                    .limit(1)
                    .execute()
                )

                if not response.data:
                    self._supabase.client.table(CONCEPTS_TABLE).insert(data).execute()
                    saved_count += 1
                else:
                    logger.debug("concept_already_exists_in_db", concept=concept.concept_name)

            except Exception as e:
                logger.error(
                    "failed_to_save_discovered_concept",
                    concept=concept.concept_name,
                    error=str(e),
                )

        logger.info("discovered_concepts_saved", saved_count=saved_count, total_provided=len(concepts))
        return saved_count