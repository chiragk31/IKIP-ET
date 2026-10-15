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
    [Sequential AI Stages]
        ├── Stage 1: Entity Extraction
        ├── Stage 2: Relationship Extraction (uses entity registry from Stage 1)
        ├── Stage 3: Measurement Extraction (uses entity registry from Stage 1)
        ├── Stage 4: Procedure Extraction (uses entity registry from Stage 1)
        ├── Stage 5: Risk Extraction (uses entity registry from Stage 1)
        ├── Stage 6: Summary Generation
        └── Stage 7: Ontology Discovery (uses entity registry from Stage 1)
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
    - Entity registry is built after Stage 1 and passed to Stages 2–7 for ID consistency.
    - Token usage is accumulated across all stages and stored in the CKO.
    - Every call is logged with prompt version, latency, token usage.
    - Sequential execution only (Gemini Free API rate limits require this).
"""

import json
import time
from typing import Any, Dict, List, Optional, Tuple
import structlog

from app.ai.llm_service import LLMService, TokenUsage
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
PROMPT_VERSION = "1.1"

# Confidence threshold for flagging low-quality entities
LOW_CONFIDENCE_THRESHOLD = 0.75

# Maximum document text length sent to AI (avoid exceeding token limits)
MAX_TEXT_CHARS = 60_000

# Stage display names for terminal output (stage_index, display_name)
STAGE_DISPLAY_NAMES = [
    "Entity Extraction",
    "Relationship Extraction",
    "Measurement Extraction",
    "Procedure Extraction",
    "Risk Extraction",
    "Summary Generation",
    "Ontology Discovery",
]
TOTAL_STAGES = len(STAGE_DISPLAY_NAMES)


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

            # --- Print pipeline header to terminal ---
            self._print_pipeline_header(filename or document_id)

            # Accumulate token usage across all stages
            accumulated_tokens = TokenUsage.zero()
            # Track how many stages failed by exception (vs. empty-but-ok results)
            failed_stages: list[str] = []

            # --- Stage 1: Entity Extraction ---
            entities_result, entity_latency, entity_tokens = await self._run_stage_entities(
                document_id, document_text, stage_index=1
            )
            if entity_tokens.total_tokens == 0:
                failed_stages.append("entity_extraction")
            accumulated_tokens = accumulated_tokens + entity_tokens

            # --- Build entity registry immediately after Stage 1 ---
            # All later stages use this registry for entity ID consistency.
            entity_registry = self._build_entity_registry(entities_result.entities)

            # --- Stage 2: Relationship Extraction ---
            relationships_result, rel_latency, rel_tokens = await self._run_stage_relationships(
                document_id, document_text, entities_result, stage_index=2
            )
            if rel_tokens.total_tokens == 0:
                failed_stages.append("relationship_extraction")
            accumulated_tokens = accumulated_tokens + rel_tokens

            # --- Stage 3: Measurement Extraction ---
            measurements_result, meas_latency, meas_tokens = await self._run_stage_measurements(
                document_id, document_text, entity_registry, stage_index=3
            )
            if meas_tokens.total_tokens == 0:
                failed_stages.append("measurement_extraction")
            accumulated_tokens = accumulated_tokens + meas_tokens

            # --- Stage 4: Procedure Extraction ---
            procedures_result, proc_latency, proc_tokens = await self._run_stage_procedures(
                document_id, document_text, entity_registry, stage_index=4
            )
            if proc_tokens.total_tokens == 0:
                failed_stages.append("procedure_extraction")
            accumulated_tokens = accumulated_tokens + proc_tokens

            # --- Stage 5: Risk Extraction ---
            risks_result, risk_latency, risk_tokens = await self._run_stage_risks(
                document_id, document_text, entity_registry, stage_index=5
            )
            if risk_tokens.total_tokens == 0:
                failed_stages.append("risk_extraction")
            accumulated_tokens = accumulated_tokens + risk_tokens

            # --- Stage 6: Summary Generation ---
            summary_result, summary_latency, summary_tokens = await self._run_stage_summary(
                document_id, document_text, filename, stage_index=6
            )
            if summary_tokens.total_tokens == 0:
                failed_stages.append("summary_generation")
            accumulated_tokens = accumulated_tokens + summary_tokens

            # --- Stage 7: Ontology Discovery ---
            ontology_result, ontology_latency, ontology_tokens = await self._run_stage_ontology(
                document_id, document_text, entity_registry, stage_index=7
            )
            if ontology_tokens.total_tokens == 0:
                failed_stages.append("ontology_discovery")
            accumulated_tokens = accumulated_tokens + ontology_tokens

            # --- Guard: all stages failed = infrastructure failure, not empty doc ---
            # When every stage returns zero tokens it means every LLM call raised
            # an exception. Treat this as a retryable infrastructure failure rather
            # than silently persisting an empty CKO and emitting a success event.
            if len(failed_stages) == TOTAL_STAGES:
                error_msg = (
                    f"All {TOTAL_STAGES} extraction stages failed for document "
                    f"{document_id}. Failed stages: {failed_stages}. "
                    "This is an infrastructure error (e.g. LLM misconfiguration), "
                    "not an empty document. Treating as pipeline failure."
                )
                logger.error(
                    "extraction_all_stages_failed",
                    document_id=document_id,
                    failed_stages=failed_stages,
                )
                raise RuntimeError(error_msg)

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

            # --- Print pipeline summary to terminal ---
            self._print_pipeline_summary(
                total_duration=total_duration,
                overall_confidence=overall_confidence,
                accumulated_tokens=accumulated_tokens,
                stage_latencies=stage_latencies,
            )

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
                total_prompt_tokens=accumulated_tokens.prompt_tokens,
                total_completion_tokens=accumulated_tokens.completion_tokens,
                total_tokens_used=accumulated_tokens.total_tokens,
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
                total_tokens=accumulated_tokens.total_tokens,
                total_prompt_tokens=accumulated_tokens.prompt_tokens,
                total_completion_tokens=accumulated_tokens.completion_tokens,
                estimated_cost_usd=round(accumulated_tokens.estimated_cost_usd, 6),
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
            print(f"\n{'='*50}")
            print(f"  EXTRACTION FAILED")
            print(f"  Document: {document_id}")
            print(f"  Error: {e}")
            print(f"{'='*50}\n")
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
        stage_index: int = 1,
    ) -> Tuple[EntityExtractionResult, float, TokenUsage]:
        """
        Stage 1: Entity Extraction.

        Extracts all industrial entities from the document text.
        On failure, returns an empty result (graceful degradation).

        Args:
            document_id: For logging
            document_text: Truncated document text
            stage_index: Display index for terminal output

        Returns:
            Tuple of (EntityExtractionResult, latency_seconds, TokenUsage)
        """
        start = time.time()
        self._print_stage_start(stage_index, "Entity Extraction")
        logger.info("extraction_stage_start", stage="entity_extraction", document_id=document_id)

        try:
            raw, token_usage = await self._llm.generate(
                prompt_name="entity_extraction",
                variables={
                    "document_text": document_text,
                    "document_id": document_id,
                },
            )
            result = self._validator.validate_entities(raw, document_id)
            latency = time.time() - start

            # Compute average entity confidence for display
            avg_conf = (
                round(sum(e.confidence for e in result.entities) / len(result.entities), 3)
                if result.entities else 0.0
            )

            self._print_stage_complete(
                stage_index=stage_index,
                stage_name="Entity Extraction",
                latency=latency,
                tokens=token_usage.total_tokens,
                count=len(result.entities),
                count_label="Entities",
                confidence=avg_conf,
            )
            logger.info(
                "extraction_stage_complete",
                stage="entity_extraction",
                document_id=document_id,
                count=len(result.entities),
                latency_seconds=round(latency, 3),
                tokens=token_usage.total_tokens,
            )
            return result, latency, token_usage

        except Exception as e:
            latency = time.time() - start
            self._print_stage_failed(stage_index, "Entity Extraction", latency, str(e))
            logger.error(
                "extraction_stage_failed",
                stage="entity_extraction",
                document_id=document_id,
                error=str(e),
                latency_seconds=round(latency, 3),
            )
            return EntityExtractionResult(entities=[]), latency, TokenUsage.zero()

    async def _run_stage_relationships(
        self,
        document_id: str,
        document_text: str,
        entities_result: EntityExtractionResult,
        stage_index: int = 2,
    ) -> Tuple[RelationshipExtractionResult, float, TokenUsage]:
        """
        Stage 2: Relationship Extraction.

        Uses the extracted entities from Stage 1 to find relationships.
        Provides the entity registry as context to ensure ID consistency.

        Args:
            document_id: For logging
            document_text: Document text
            entities_result: Output from Stage 1
            stage_index: Display index for terminal output

        Returns:
            Tuple of (RelationshipExtractionResult, latency_seconds, TokenUsage)
        """
        start = time.time()
        self._print_stage_start(stage_index, "Relationship Extraction")
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

            raw, token_usage = await self._llm.generate(
                prompt_name="relationship_extraction",
                variables={
                    "document_text": document_text,
                    "entities": entities_summary,
                },
            )
            result = self._validator.validate_relationships(raw, document_id)
            latency = time.time() - start
            self._print_stage_complete(
                stage_index=stage_index,
                stage_name="Relationship Extraction",
                latency=latency,
                tokens=token_usage.total_tokens,
                count=len(result.relationships),
                count_label="Relationships",
            )
            logger.info(
                "extraction_stage_complete",
                stage="relationship_extraction",
                document_id=document_id,
                count=len(result.relationships),
                latency_seconds=round(latency, 3),
                tokens=token_usage.total_tokens,
            )
            return result, latency, token_usage

        except Exception as e:
            latency = time.time() - start
            self._print_stage_failed(stage_index, "Relationship Extraction", latency, str(e))
            logger.error(
                "extraction_stage_failed",
                stage="relationship_extraction",
                document_id=document_id,
                error=str(e),
                latency_seconds=round(latency, 3),
            )
            return RelationshipExtractionResult(relationships=[]), latency, TokenUsage.zero()

    async def _run_stage_measurements(
        self,
        document_id: str,
        document_text: str,
        entity_registry: str,
        stage_index: int = 3,
    ) -> Tuple[MeasurementExtractionResult, float, TokenUsage]:
        """
        Stage 3: Measurement Extraction.

        Extracts all numerical measurements and physical quantities.
        Receives the entity registry so applies_to_entity IDs remain canonical.

        Args:
            document_id: For logging
            document_text: Document text
            entity_registry: JSON-serialized entity registry from Stage 1
            stage_index: Display index for terminal output

        Returns:
            Tuple of (MeasurementExtractionResult, latency_seconds, TokenUsage)
        """
        start = time.time()
        self._print_stage_start(stage_index, "Measurement Extraction")
        logger.info("extraction_stage_start", stage="measurement_extraction", document_id=document_id)

        try:
            raw, token_usage = await self._llm.generate(
                prompt_name="measurement_extraction",
                variables={
                    "document_text": document_text,
                    "document_id": document_id,
                    "entity_registry": entity_registry,
                },
            )
            result = self._validator.validate_measurements(raw, document_id)
            latency = time.time() - start
            self._print_stage_complete(
                stage_index=stage_index,
                stage_name="Measurement Extraction",
                latency=latency,
                tokens=token_usage.total_tokens,
                count=len(result.measurements),
                count_label="Measurements",
            )
            logger.info(
                "extraction_stage_complete",
                stage="measurement_extraction",
                document_id=document_id,
                count=len(result.measurements),
                latency_seconds=round(latency, 3),
                tokens=token_usage.total_tokens,
            )
            return result, latency, token_usage

        except Exception as e:
            latency = time.time() - start
            self._print_stage_failed(stage_index, "Measurement Extraction", latency, str(e))
            logger.error(
                "extraction_stage_failed",
                stage="measurement_extraction",
                document_id=document_id,
                error=str(e),
                latency_seconds=round(latency, 3),
            )
            return MeasurementExtractionResult(measurements=[]), latency, TokenUsage.zero()

    async def _run_stage_procedures(
        self,
        document_id: str,
        document_text: str,
        entity_registry: str,
        stage_index: int = 4,
    ) -> Tuple[ProcedureExtractionResult, float, TokenUsage]:
        """
        Stage 4: Procedure Extraction.

        Extracts maintenance procedures, safety instructions, and workflows.
        Receives entity registry for applies_to_entity ID consistency.

        Args:
            document_id: For logging
            document_text: Document text
            entity_registry: JSON-serialized entity registry from Stage 1
            stage_index: Display index for terminal output

        Returns:
            Tuple of (ProcedureExtractionResult, latency_seconds, TokenUsage)
        """
        start = time.time()
        self._print_stage_start(stage_index, "Procedure Extraction")
        logger.info("extraction_stage_start", stage="procedure_extraction", document_id=document_id)

        try:
            raw, token_usage = await self._llm.generate(
                prompt_name="procedure_extraction",
                variables={
                    "document_text": document_text,
                    "document_id": document_id,
                    "entity_registry": entity_registry,
                },
            )
            result = self._validator.validate_procedures(raw, document_id)
            latency = time.time() - start
            self._print_stage_complete(
                stage_index=stage_index,
                stage_name="Procedure Extraction",
                latency=latency,
                tokens=token_usage.total_tokens,
                count=len(result.procedures),
                count_label="Procedures",
            )
            logger.info(
                "extraction_stage_complete",
                stage="procedure_extraction",
                document_id=document_id,
                count=len(result.procedures),
                latency_seconds=round(latency, 3),
                tokens=token_usage.total_tokens,
            )
            return result, latency, token_usage

        except Exception as e:
            latency = time.time() - start
            self._print_stage_failed(stage_index, "Procedure Extraction", latency, str(e))
            logger.error(
                "extraction_stage_failed",
                stage="procedure_extraction",
                document_id=document_id,
                error=str(e),
                latency_seconds=round(latency, 3),
            )
            return ProcedureExtractionResult(procedures=[]), latency, TokenUsage.zero()

    async def _run_stage_risks(
        self,
        document_id: str,
        document_text: str,
        entity_registry: str,
        stage_index: int = 5,
    ) -> Tuple[RiskExtractionResult, float, TokenUsage]:
        """
        Stage 5: Risk Extraction.

        Identifies hazards, safety risks, failure modes, and compliance gaps.
        Receives entity registry for applies_to_entity ID consistency.

        Args:
            document_id: For logging
            document_text: Document text
            entity_registry: JSON-serialized entity registry from Stage 1
            stage_index: Display index for terminal output

        Returns:
            Tuple of (RiskExtractionResult, latency_seconds, TokenUsage)
        """
        start = time.time()
        self._print_stage_start(stage_index, "Risk Extraction")
        logger.info("extraction_stage_start", stage="risk_extraction", document_id=document_id)

        try:
            raw, token_usage = await self._llm.generate(
                prompt_name="risk_analysis",
                variables={
                    "document_text": document_text,
                    "document_id": document_id,
                    "entity_registry": entity_registry,
                },
            )
            result = self._validator.validate_risks(raw, document_id)
            latency = time.time() - start
            self._print_stage_complete(
                stage_index=stage_index,
                stage_name="Risk Extraction",
                latency=latency,
                tokens=token_usage.total_tokens,
                count=len(result.risks),
                count_label="Risks",
            )
            logger.info(
                "extraction_stage_complete",
                stage="risk_extraction",
                document_id=document_id,
                risk_count=len(result.risks),
                warning_count=len(result.warnings),
                compliance_gap_count=len(result.compliance_gaps),
                latency_seconds=round(latency, 3),
                tokens=token_usage.total_tokens,
            )
            return result, latency, token_usage

        except Exception as e:
            latency = time.time() - start
            self._print_stage_failed(stage_index, "Risk Extraction", latency, str(e))
            logger.error(
                "extraction_stage_failed",
                stage="risk_extraction",
                document_id=document_id,
                error=str(e),
                latency_seconds=round(latency, 3),
            )
            return RiskExtractionResult(risks=[], warnings=[], compliance_gaps=[]), latency, TokenUsage.zero()

    async def _run_stage_summary(
        self,
        document_id: str,
        document_text: str,
        filename: str,
        stage_index: int = 6,
    ) -> Tuple[DocumentSummaryResult, float, TokenUsage]:
        """
        Stage 6: Document Summary Generation.

        Generates executive summary, document type classification, keywords, and topics.

        Args:
            document_id: For logging
            document_text: Document text
            filename: Original filename for context
            stage_index: Display index for terminal output

        Returns:
            Tuple of (DocumentSummaryResult, latency_seconds, TokenUsage)
        """
        start = time.time()
        self._print_stage_start(stage_index, "Summary Generation")
        logger.info("extraction_stage_start", stage="summary_generation", document_id=document_id)

        try:
            raw, token_usage = await self._llm.generate(
                prompt_name="summary",
                variables={
                    "document_text": document_text,
                    "filename": filename,
                },
            )
            result = self._validator.validate_summary(raw, document_id)
            latency = time.time() - start
            self._print_stage_complete(
                stage_index=stage_index,
                stage_name="Summary Generation",
                latency=latency,
                tokens=token_usage.total_tokens,
            )
            logger.info(
                "extraction_stage_complete",
                stage="summary_generation",
                document_id=document_id,
                summary_length=len(result.summary),
                keyword_count=len(result.keywords),
                latency_seconds=round(latency, 3),
                tokens=token_usage.total_tokens,
            )
            return result, latency, token_usage

        except Exception as e:
            latency = time.time() - start
            self._print_stage_failed(stage_index, "Summary Generation", latency, str(e))
            logger.error(
                "extraction_stage_failed",
                stage="summary_generation",
                document_id=document_id,
                error=str(e),
                latency_seconds=round(latency, 3),
            )
            return DocumentSummaryResult(), latency, TokenUsage.zero()

    async def _run_stage_ontology(
        self,
        document_id: str,
        document_text: str,
        entity_registry: str,
        stage_index: int = 7,
    ) -> Tuple[OntologyDiscoveryResult, float, TokenUsage]:
        """
        Stage 7: Ontology Discovery.

        Suggests new entity types and concepts not in the current core ontology.
        These suggestions are passed to Epic 4 (Ontology Management) for validation.
        Receives entity registry so it knows what types are already known.

        Args:
            document_id: For logging
            document_text: Document text
            entity_registry: JSON-serialized entity registry from Stage 1
            stage_index: Display index for terminal output

        Returns:
            Tuple of (OntologyDiscoveryResult, latency_seconds, TokenUsage)
        """
        start = time.time()
        self._print_stage_start(stage_index, "Ontology Discovery")
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
            raw, token_usage = await self._llm.generate(
                prompt_name="ontology_discovery",
                variables={
                    "document_text": document_text,
                    "current_ontology": current_ontology,
                    "entity_registry": entity_registry,
                },
            )
            result = self._validator.validate_ontology_discovery(raw, document_id)
            latency = time.time() - start
            self._print_stage_complete(
                stage_index=stage_index,
                stage_name="Ontology Discovery",
                latency=latency,
                tokens=token_usage.total_tokens,
                count=len(result.new_concepts),
                count_label="New Concepts",
            )
            logger.info(
                "extraction_stage_complete",
                stage="ontology_discovery",
                document_id=document_id,
                new_concepts=len(result.new_concepts),
                latency_seconds=round(latency, 3),
                tokens=token_usage.total_tokens,
            )
            return result, latency, token_usage

        except Exception as e:
            latency = time.time() - start
            self._print_stage_failed(stage_index, "Ontology Discovery", latency, str(e))
            logger.error(
                "extraction_stage_failed",
                stage="ontology_discovery",
                document_id=document_id,
                error=str(e),
                latency_seconds=round(latency, 3),
            )
            return OntologyDiscoveryResult(new_concepts=[]), latency, TokenUsage.zero()

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

    @staticmethod
    def _build_entity_registry(entities: List[ExtractedEntity]) -> str:
        """
        Build a serialized entity registry from the extracted entity list.

        This registry is passed to Stages 2–7 so the LLM can reference
        canonical entity IDs instead of inventing new ones.

        Args:
            entities: Extracted entities from Stage 1

        Returns:
            JSON string of the entity registry
        """
        registry = [
            {
                "entity_id": e.entity_id,
                "label": e.label,
                "entity_type": e.entity_type,
                "aliases": e.aliases,
            }
            for e in entities
        ]
        return json.dumps(registry, indent=2)

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

    # -----------------------------------------------
    # Terminal Output Helpers (Bug 3)
    # -----------------------------------------------

    @staticmethod
    def _print_pipeline_header(filename: str) -> None:
        """
        Print the extraction pipeline start banner to terminal.

        Args:
            filename: Document filename or ID for display
        """
        print(f"\n{'='*52}")
        print(f"  Document: {filename}")
        print(f"  Knowledge Extraction Started")
        print(f"{'='*52}\n")

    @staticmethod
    def _print_stage_start(stage_index: int, stage_name: str) -> None:
        """
        Print stage start line to terminal.

        Args:
            stage_index: 1-based stage number
            stage_name: Human-readable stage name
        """
        print(f"[{stage_index}/{TOTAL_STAGES}] {stage_name}")
        print(f"  Started...")

    @staticmethod
    def _print_stage_complete(
        stage_index: int,
        stage_name: str,
        latency: float,
        tokens: int,
        count: Optional[int] = None,
        count_label: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> None:
        """
        Print stage completion details to terminal.

        Args:
            stage_index: 1-based stage number
            stage_name: Human-readable stage name
            latency: Stage duration in seconds
            tokens: Total tokens consumed by this stage
            count: Number of items extracted (optional)
            count_label: Label for the count (e.g., "Entities", "Relationships")
            confidence: Average confidence score (optional)
        """
        print(f"  ✓ Completed")
        if count is not None and count_label:
            print(f"  {count_label}: {count}")
        if confidence is not None:
            print(f"  Confidence: {confidence}")
        if tokens:
            print(f"  Tokens: {tokens}")
        print(f"  Duration: {round(latency, 1)} sec")
        print(f"{'-'*52}")

    @staticmethod
    def _print_stage_failed(
        stage_index: int,
        stage_name: str,
        latency: float,
        error: str,
    ) -> None:
        """
        Print stage failure details to terminal.

        Args:
            stage_index: 1-based stage number
            stage_name: Human-readable stage name
            latency: Stage duration in seconds
            error: Error message
        """
        print(f"  ✗ FAILED")
        print(f"  Stage: {stage_name}")
        print(f"  Reason: {error[:200]}")
        print(f"  Duration: {round(latency, 1)} sec")
        print(f"  Continuing with empty result for this stage.")
        print(f"{'-'*52}")

    @staticmethod
    def _print_pipeline_summary(
        total_duration: float,
        overall_confidence: float,
        accumulated_tokens: TokenUsage,
        stage_latencies: Dict[str, float],
    ) -> None:
        """
        Print the pipeline completion summary to terminal.

        Args:
            total_duration: Total pipeline duration in seconds
            overall_confidence: Overall extraction confidence score
            accumulated_tokens: Accumulated token usage across all stages
            stage_latencies: Per-stage latencies dict
        """
        print(f"\n{'='*52}")
        print(f"  Knowledge Extraction Finished")
        print(f"  Total Time: {round(total_duration, 1)} sec")
        print(f"  Total Prompt Tokens: {accumulated_tokens.prompt_tokens}")
        print(f"  Total Completion Tokens: {accumulated_tokens.completion_tokens}")
        print(f"  Total Tokens: {accumulated_tokens.total_tokens}")
        print(f"  Estimated Cost: ${round(accumulated_tokens.estimated_cost_usd, 6)}")
        print(f"  Overall Confidence: {overall_confidence}")
        print(f"{'='*52}\n")
