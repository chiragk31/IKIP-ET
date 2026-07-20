"""
AI Knowledge Extraction Service

Orchestrates the multi-stage AI pipeline that transforms a CanonicalDocument
into a Canonical Knowledge Object (CKO).

Architecture:
    document.processed event
        ↓
    KnowledgeHandler
        ↓
    ExtractionService.extract(document_id, canonical_storage_path)
        ↓
    [Parallel/Sequential AI Stages]
        ├── Stage 1: Entity Extraction
        ├── Stage 2: Relationship Extraction (uses entities from Stage 1)
        ├── Stage 3: Measurement Extraction
        ├── Stage 4: Procedure Extraction
        ├── Stage 5: Risk Extraction
        ├── Stage 6: Summary Generation
        └── Stage 7: Ontology Discovery
        ↓
    Validation → Confidence Filtering → CKO Assembly
        ↓
    KnowledgeRepository.save(cko)
        ↓
    InngestClient.send_knowledge_extracted_event()

Rules:
    - ONLY this service calls LLMService.
    - No other module runs AI extraction.
    - Each stage is independent and fault-tolerant.
    - A stage failure results in an empty result for that stage (graceful degradation).
    - Every call is logged with prompt version, latency, token usage.
"""

import json
import time
from typing import Any, Dict, Optional
import structlog

from app.ai.llm_service import LLMService
from app.ai.validator import AIValidator
from app.schemas.knowledge import (
    CanonicalKnowledgeObject,
    EntityExtractionResult,
    RelationshipExtractionResult,
    MeasurementExtractionResult,
    ProcedureExtractionResult,
    RiskExtractionResult,
    DocumentSummaryResult,
    OntologyDiscoveryResult,
    ExtractedEntity,
    ExtractedRelationship,
)
from app.repositories.knowledge_repository import KnowledgeRepository
from app.repositories.storage_repository import StorageRepository
from app.repositories.document_repository import DocumentRepository
from app.events.inngest_client import InngestClient
from app.utils.constants import ProcessingStage

logger = structlog.get_logger(__name__)

# Current prompt version — update when prompts are changed
PROMPT_VERSION = "1.0"

# Confidence threshold for flagging low-quality entities
LOW_CONFIDENCE_THRESHOLD = 0.75

# Maximum document text length sent to AI (avoid exceeding token limits)
MAX_TEXT_CHARS = 60_000


class ExtractionService:
    """
    Orchestrates the multi-stage AI knowledge extraction pipeline.

    Each document processed by Epic 2 is passed through this service,
    which calls Gemini (via LLMService) in multiple focused stages,
    assembles the results into a CKO, and persists it.

    This is the only service that calls LLMService for knowledge extraction.
    """

    def __init__(
        self,
        llm_service: LLMService,
        knowledge_repo: KnowledgeRepository,
        storage_repo: StorageRepository,
        document_repo: DocumentRepository,
        inngest: InngestClient,
    ) -> None:
        """
        Initialize the ExtractionService.

        Args:
            llm_service: The LLM gateway (only Gemini caller)
            knowledge_repo: Persistence for CKOs
            storage_repo: Download canonical JSON from storage
            document_repo: Update document processing stage
            inngest: Event emitter for knowledge.extracted
        """
        self._llm = llm_service
        self._knowledge_repo = knowledge_repo
        self._storage_repo = storage_repo
        self._document_repo = document_repo
        self._inngest = inngest
        self._validator = AIValidator()
        logger.info("extraction_service_initialized")

    # -----------------------------------------------
    # Public Entry Point
    # -----------------------------------------------

    async def extract(
        self,
        document_id: str,
        canonical_storage_path: str,
        original_filename: str = "",
        user_id: Optional[str] = None,
    ) -> CanonicalKnowledgeObject:
        """
        Run the full multi-stage AI extraction pipeline for a document.

        Downloads the CanonicalDocument JSON from storage, runs all AI
        extraction stages, assembles the CKO, persists it, and emits
        the knowledge.extracted event.

        Args:
            document_id: Supabase document UUID
            canonical_storage_path: Storage path to canonical JSON (from Epic 2)
            original_filename: Original filename for context
            user_id: Uploader user ID (for event attribution)

        Returns:
            Assembled CanonicalKnowledgeObject

        Raises:
            Exception: On unrecoverable failure (CKO still saved as failed)
        """
        pipeline_start = time.time()

        logger.info(
            "extraction_pipeline_start",
            document_id=document_id,
            canonical_path=canonical_storage_path,
            filename=original_filename,
        )

        # Update document status to extracting
        self._update_status(document_id, "processing", ProcessingStage.EXTRACTING.value)

        try:
            # --- Load CanonicalDocument from Supabase Storage ---
            canonical_doc = self._load_canonical_document(
                document_id, canonical_storage_path
            )
            document_text = self._prepare_text(canonical_doc)
            filename = original_filename or canonical_doc.get("original_filename", "")

            logger.info(
                "canonical_document_loaded",
                document_id=document_id,
                text_length=len(document_text),
                filename=filename,
            )

            # --- Stage 1: Entity Extraction ---
            entities_result, entity_latency = await self._run_stage_entities(
                document_id, document_text
            )

            # --- Stage 2: Relationship Extraction ---
            relationships_result, rel_latency = await self._run_stage_relationships(
                document_id, document_text, entities_result
            )

            # --- Stage 3: Measurement Extraction ---
            measurements_result, meas_latency = await self._run_stage_measurements(
                document_id, document_text
            )

            # --- Stage 4: Procedure Extraction ---
            procedures_result, proc_latency = await self._run_stage_procedures(
                document_id, document_text
            )

            # --- Stage 5: Risk Extraction ---
            risks_result, risk_latency = await self._run_stage_risks(
                document_id, document_text
            )

            # --- Stage 6: Summary Generation ---
            summary_result, summary_latency = await self._run_stage_summary(
                document_id, document_text, filename
            )

            # --- Stage 7: Ontology Discovery ---
            ontology_result, ontology_latency = await self._run_stage_ontology(
                document_id, document_text
            )

            # --- Confidence Filtering ---
            accepted_entities, flagged_entities = self._validator.split_by_confidence(
                entities_result.entities, LOW_CONFIDENCE_THRESHOLD
            )
            accepted_relationships, flagged_relationships = self._validator.split_relationships_by_confidence(
                relationships_result.relationships
            )

            # --- Overall Confidence ---
            overall_confidence = AIValidator.compute_overall_confidence(
                accepted_entities, accepted_relationships, bool(summary_result.summary)
            )

            # --- Collect Standards ---
            standards = []
            for proc in procedures_result.procedures:
                standards.extend(proc.applicable_standards)
            for risk in risks_result.risks:
                standards.extend(risk.applicable_standards)
            # Deduplicate
            standards = list(dict.fromkeys(standards))

            # --- Stage Latency Map ---
            stage_latencies = {
                "entity_extraction": round(entity_latency, 3),
                "relationship_extraction": round(rel_latency, 3),
                "measurement_extraction": round(meas_latency, 3),
                "procedure_extraction": round(proc_latency, 3),
                "risk_extraction": round(risk_latency, 3),
                "summary_generation": round(summary_latency, 3),
                "ontology_discovery": round(ontology_latency, 3),
            }

            total_duration = time.time() - pipeline_start

            # --- Assemble CKO ---
            cko = CanonicalKnowledgeObject(
                document_id=document_id,
                document={
                    "id": document_id,
                    "original_filename": filename,
                    "storage_path": canonical_storage_path,
                    "metadata": canonical_doc.get("metadata", {}),
                },
                summary=summary_result.summary,
                document_type=summary_result.document_type,
                language=summary_result.language or canonical_doc.get("language", "en"),
                keywords=summary_result.keywords,
                topics=summary_result.topics,
                key_findings=summary_result.key_findings,
                key_assets=summary_result.key_assets,
                entities=accepted_entities,
                relationships=accepted_relationships,
                measurements=measurements_result.measurements,
                procedures=procedures_result.procedures,
                risks=risks_result.risks,
                standards=standards,
                warnings=risks_result.warnings,
                compliance_gaps=risks_result.compliance_gaps,
                new_concepts=ontology_result.new_concepts,
                confidence=overall_confidence,
                flagged_entities=flagged_entities,
                flagged_relationships=flagged_relationships,
                model_version=self._llm.model_name,
                prompt_version=PROMPT_VERSION,
                extraction_time_seconds=round(total_duration, 3),
                stage_latencies=stage_latencies,
            )

            # --- Persist CKO ---
            record = self._knowledge_repo.save(cko)

            # --- Update document status to completed ---
            self._update_status(document_id, "completed", ProcessingStage.COMPLETED.value)

            # --- Emit knowledge.extracted event ---
            self._inngest.send_knowledge_extracted_event(
                document_id=document_id,
                knowledge_id=record.id,
                confidence=overall_confidence,
                user_id=user_id,
            )

            logger.info(
                "extraction_pipeline_complete",
                document_id=document_id,
                knowledge_id=record.id,
                total_duration_seconds=round(total_duration, 2),
                entity_count=len(accepted_entities),
                relationship_count=len(accepted_relationships),
                measurement_count=len(measurements_result.measurements),
                procedure_count=len(procedures_result.procedures),
                risk_count=len(risks_result.risks),
                flagged_entity_count=len(flagged_entities),
                confidence=overall_confidence,
            )

            return cko

        except Exception as e:
            total_duration = time.time() - pipeline_start
            logger.error(
                "extraction_pipeline_failed",
                document_id=document_id,
                error=str(e),
                duration_seconds=round(total_duration, 2),
            )
            # Save failure record for traceability
            self._knowledge_repo.save_failed(
                document_id=document_id,
                error_message=str(e),
                model_version=self._llm.model_name,
                prompt_version=PROMPT_VERSION,
            )
            self._update_status(document_id, "failed")
            raise

    # -----------------------------------------------
    # Pipeline Stages
    # -----------------------------------------------

    async def _run_stage_entities(
        self,
        document_id: str,
        document_text: str,
    ) -> tuple[EntityExtractionResult, float]:
        """
        Stage 1: Entity Extraction.

        Extracts all industrial entities from the document text.
        On failure, returns an empty result (graceful degradation).

        Args:
            document_id: For logging
            document_text: Truncated document text

        Returns:
            Tuple of (EntityExtractionResult, latency_seconds)
        """
        start = time.time()
        logger.info("extraction_stage_start", stage="entity_extraction", document_id=document_id)

        try:
            raw = await self._llm.generate(
                prompt_name="entity_extraction",
                variables={
                    "document_text": document_text,
                    "document_id": document_id,
                },
            )
            result = self._validator.validate_entities(raw, document_id)
            latency = time.time() - start
            logger.info(
                "extraction_stage_complete",
                stage="entity_extraction",
                document_id=document_id,
                count=len(result.entities),
                latency_seconds=round(latency, 3),
            )
            return result, latency

        except Exception as e:
            latency = time.time() - start
            logger.error(
                "extraction_stage_failed",
                stage="entity_extraction",
                document_id=document_id,
                error=str(e),
                latency_seconds=round(latency, 3),
            )
            return EntityExtractionResult(entities=[]), latency

    async def _run_stage_relationships(
        self,
        document_id: str,
        document_text: str,
        entities_result: EntityExtractionResult,
    ) -> tuple[RelationshipExtractionResult, float]:
        """
        Stage 2: Relationship Extraction.

        Uses the extracted entities from Stage 1 to find relationships.
        Requires entities to be available for context.

        Args:
            document_id: For logging
            document_text: Document text
            entities_result: Output from Stage 1

        Returns:
            Tuple of (RelationshipExtractionResult, latency_seconds)
        """
        start = time.time()
        logger.info("extraction_stage_start", stage="relationship_extraction", document_id=document_id)

        try:
            # Serialize entities summary for the relationship prompt
            entities_summary = json.dumps(
                [
                    {
                        "entity_id": e.entity_id,
                        "entity_type": e.entity_type,
                        "label": e.label,
                    }
                    for e in entities_result.entities
                ],
                indent=2,
            )

            raw = await self._llm.generate(
                prompt_name="relationship_extraction",
                variables={
                    "document_text": document_text,
                    "entities": entities_summary,
                },
            )
            result = self._validator.validate_relationships(raw, document_id)
            latency = time.time() - start
            logger.info(
                "extraction_stage_complete",
                stage="relationship_extraction",
                document_id=document_id,
                count=len(result.relationships),
                latency_seconds=round(latency, 3),
            )
            return result, latency

        except Exception as e:
            latency = time.time() - start
            logger.error(
                "extraction_stage_failed",
                stage="relationship_extraction",
                document_id=document_id,
                error=str(e),
                latency_seconds=round(latency, 3),
            )
            return RelationshipExtractionResult(relationships=[]), latency

    async def _run_stage_measurements(
        self,
        document_id: str,
        document_text: str,
    ) -> tuple[MeasurementExtractionResult, float]:
        """
        Stage 3: Measurement Extraction.

        Extracts all numerical measurements and physical quantities.

        Args:
            document_id: For logging
            document_text: Document text

        Returns:
            Tuple of (MeasurementExtractionResult, latency_seconds)
        """
        start = time.time()
        logger.info("extraction_stage_start", stage="measurement_extraction", document_id=document_id)

        try:
            raw = await self._llm.generate(
                prompt_name="measurement_extraction",
                variables={
                    "document_text": document_text,
                    "document_id": document_id,
                },
            )
            result = self._validator.validate_measurements(raw, document_id)
            latency = time.time() - start
            logger.info(
                "extraction_stage_complete",
                stage="measurement_extraction",
                document_id=document_id,
                count=len(result.measurements),
                latency_seconds=round(latency, 3),
            )
            return result, latency

        except Exception as e:
            latency = time.time() - start
            logger.error(
                "extraction_stage_failed",
                stage="measurement_extraction",
                document_id=document_id,
                error=str(e),
                latency_seconds=round(latency, 3),
            )
            return MeasurementExtractionResult(measurements=[]), latency

    async def _run_stage_procedures(
        self,
        document_id: str,
        document_text: str,
    ) -> tuple[ProcedureExtractionResult, float]:
        """
        Stage 4: Procedure Extraction.

        Extracts maintenance procedures, safety instructions, and workflows.

        Args:
            document_id: For logging
            document_text: Document text

        Returns:
            Tuple of (ProcedureExtractionResult, latency_seconds)
        """
        start = time.time()
        logger.info("extraction_stage_start", stage="procedure_extraction", document_id=document_id)

        try:
            raw = await self._llm.generate(
                prompt_name="procedure_extraction",
                variables={
                    "document_text": document_text,
                    "document_id": document_id,
                },
            )
            result = self._validator.validate_procedures(raw, document_id)
            latency = time.time() - start
            logger.info(
                "extraction_stage_complete",
                stage="procedure_extraction",
                document_id=document_id,
                count=len(result.procedures),
                latency_seconds=round(latency, 3),
            )
            return result, latency

        except Exception as e:
            latency = time.time() - start
            logger.error(
                "extraction_stage_failed",
                stage="procedure_extraction",
                document_id=document_id,
                error=str(e),
                latency_seconds=round(latency, 3),
            )
            return ProcedureExtractionResult(procedures=[]), latency

    async def _run_stage_risks(
        self,
        document_id: str,
        document_text: str,
    ) -> tuple[RiskExtractionResult, float]:
        """
        Stage 5: Risk Extraction.

        Identifies hazards, safety risks, failure modes, and compliance gaps.

        Args:
            document_id: For logging
            document_text: Document text

        Returns:
            Tuple of (RiskExtractionResult, latency_seconds)
        """
        start = time.time()
        logger.info("extraction_stage_start", stage="risk_extraction", document_id=document_id)

        try:
            raw = await self._llm.generate(
                prompt_name="risk_analysis",
                variables={
                    "document_text": document_text,
                    "document_id": document_id,
                },
            )
            result = self._validator.validate_risks(raw, document_id)
            latency = time.time() - start
            logger.info(
                "extraction_stage_complete",
                stage="risk_extraction",
                document_id=document_id,
                risk_count=len(result.risks),
                warning_count=len(result.warnings),
                compliance_gap_count=len(result.compliance_gaps),
                latency_seconds=round(latency, 3),
            )
            return result, latency

        except Exception as e:
            latency = time.time() - start
            logger.error(
                "extraction_stage_failed",
                stage="risk_extraction",
                document_id=document_id,
                error=str(e),
                latency_seconds=round(latency, 3),
            )
            return RiskExtractionResult(risks=[], warnings=[], compliance_gaps=[]), latency

    async def _run_stage_summary(
        self,
        document_id: str,
        document_text: str,
        filename: str,
    ) -> tuple[DocumentSummaryResult, float]:
        """
        Stage 6: Document Summary Generation.

        Generates executive summary, document type classification, keywords, and topics.

        Args:
            document_id: For logging
            document_text: Document text
            filename: Original filename for context

        Returns:
            Tuple of (DocumentSummaryResult, latency_seconds)
        """
        start = time.time()
        logger.info("extraction_stage_start", stage="summary_generation", document_id=document_id)

        try:
            raw = await self._llm.generate(
                prompt_name="summary",
                variables={
                    "document_text": document_text,
                    "filename": filename,
                },
            )
            result = self._validator.validate_summary(raw, document_id)
            latency = time.time() - start
            logger.info(
                "extraction_stage_complete",
                stage="summary_generation",
                document_id=document_id,
                summary_length=len(result.summary),
                keyword_count=len(result.keywords),
                latency_seconds=round(latency, 3),
            )
            return result, latency

        except Exception as e:
            latency = time.time() - start
            logger.error(
                "extraction_stage_failed",
                stage="summary_generation",
                document_id=document_id,
                error=str(e),
                latency_seconds=round(latency, 3),
            )
            return DocumentSummaryResult(), latency

    async def _run_stage_ontology(
        self,
        document_id: str,
        document_text: str,
    ) -> tuple[OntologyDiscoveryResult, float]:
        """
        Stage 7: Ontology Discovery.

        Suggests new entity types and concepts not in the current core ontology.
        These suggestions are passed to Epic 4 (Ontology Management) for validation.

        Args:
            document_id: For logging
            document_text: Document text

        Returns:
            Tuple of (OntologyDiscoveryResult, latency_seconds)
        """
        start = time.time()
        logger.info("extraction_stage_start", stage="ontology_discovery", document_id=document_id)

        # Current core ontology description for the prompt
        current_ontology = (
            "Core entity types: Document, Asset, Person, Organization, Location, "
            "Procedure, Event, Measurement, Risk, Failure, Regulation. "
            "Core relationships: MENTIONS, HAS_FAILURE, LOCATED_IN, PERFORMED, "
            "HAS_MEASUREMENT, REFERENCES, CONNECTED_TO, CAUSED_BY, USES, REQUIRES, "
            "MITIGATED_BY, RECORDED_FOR, INVOLVES, OWNS, RELATED_TO."
        )

        try:
            raw = await self._llm.generate(
                prompt_name="ontology_discovery",
                variables={
                    "document_text": document_text,
                    "current_ontology": current_ontology,
                },
            )
            result = self._validator.validate_ontology_discovery(raw, document_id)
            latency = time.time() - start
            logger.info(
                "extraction_stage_complete",
                stage="ontology_discovery",
                document_id=document_id,
                new_concepts=len(result.new_concepts),
                latency_seconds=round(latency, 3),
            )
            return result, latency

        except Exception as e:
            latency = time.time() - start
            logger.error(
                "extraction_stage_failed",
                stage="ontology_discovery",
                document_id=document_id,
                error=str(e),
                latency_seconds=round(latency, 3),
            )
            return OntologyDiscoveryResult(new_concepts=[]), latency

    # -----------------------------------------------
    # Helpers
    # -----------------------------------------------

    def _load_canonical_document(
        self,
        document_id: str,
        storage_path: str,
    ) -> Dict[str, Any]:
        """
        Download and parse the CanonicalDocument JSON from Supabase Storage.

        Args:
            document_id: For logging
            storage_path: Storage path from Epic 2

        Returns:
            Parsed canonical document dictionary

        Raises:
            RuntimeError: If download or parse fails
        """
        try:
            content = self._storage_repo.download_file(storage_path)
            return json.loads(content.decode("utf-8"))
        except Exception as e:
            logger.error(
                "canonical_document_load_failed",
                document_id=document_id,
                storage_path=storage_path,
                error=str(e),
            )
            raise RuntimeError(f"Failed to load canonical document: {e}")

    @staticmethod
    def _prepare_text(canonical_doc: Dict[str, Any]) -> str:
        """
        Prepare document text for AI consumption.

        Truncates to MAX_TEXT_CHARS to avoid LLM token limit errors.
        Includes sections and tables for richer context.

        Args:
            canonical_doc: Parsed CanonicalDocument dict

        Returns:
            Concatenated, truncated document text
        """
        full_text = canonical_doc.get("full_text", "")

        # Append table markdown for structured data
        tables = canonical_doc.get("tables", [])
        if tables:
            table_text = "\n\n--- TABLES ---\n"
            for table in tables[:10]:  # Limit to first 10 tables
                table_text += table.get("markdown", "") + "\n"
            full_text = full_text + table_text

        # Truncate to stay within token budget
        if len(full_text) > MAX_TEXT_CHARS:
            full_text = full_text[:MAX_TEXT_CHARS] + "\n...[text truncated for AI processing]"

        return full_text.strip()

    def _update_status(
        self,
        document_id: str,
        status: str,
        processing_stage: Optional[str] = None,
    ) -> None:
        """
        Update document processing status in Supabase.

        Failures are logged but never re-raised — status updates are
        non-critical compared to the extraction itself.

        Args:
            document_id: Document UUID
            status: New status value
            processing_stage: Optional stage label
        """
        try:
            self._document_repo.update_status(
                document_id=document_id,
                status=status,
                processing_stage=processing_stage,
            )
        except Exception as e:
            logger.warning(
                "status_update_failed",
                document_id=document_id,
                status=status,
                error=str(e),
            )
