"""
AI Response Validator

Validates all Gemini responses before they are used by business services.

This module is the quality gate for the AI pipeline. Nothing leaves
the AI layer without passing through this validator.

Responsibilities:
  - JSON schema validation via Pydantic
  - Required field checks
  - Confidence threshold filtering
  - Duplicate entity/relationship deduplication
  - Malformed response handling
  - Partial result recovery (graceful degradation)

Rules:
  - Invalid responses are REJECTED, never silently passed through.
  - Low-confidence items are FLAGGED, not discarded.
  - Validation errors are LOGGED with full context.
  - Business logic never needs to validate AI output — this module does it.
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple, Type
from pydantic import BaseModel, ValidationError
import structlog

from app.schemas.knowledge import (
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
from app.utils.constants import MIN_ENTITY_CONFIDENCE, MIN_RELATIONSHIP_CONFIDENCE

logger = structlog.get_logger(__name__)

# Default low-confidence review threshold
LOW_CONFIDENCE_THRESHOLD = 0.75


class ValidationResult(BaseModel):
    """
    Result of a validation pass.

    Contains both the valid output and any flagged/rejected items.
    """
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []


class AIValidator:
    """
    Validates and normalises all AI output from Gemini.

    Every AI stage result passes through this validator before it is
    assembled into the Canonical Knowledge Object.

    Usage:
        validator = AIValidator()
        result = validator.validate_entities(raw_dict)
        # → EntityExtractionResult (validated)
    """

    # -----------------------------------------------
    # JSON Parsing
    # -----------------------------------------------

    @staticmethod
    def parse_json_response(raw_response: Any) -> Dict[str, Any]:
        """
        Parse raw AI response into a clean dictionary.

        Handles:
        - Already-parsed dicts (from Gemini JSON mode)
        - Raw JSON strings
        - Markdown-fenced JSON blocks

        Args:
            raw_response: Raw response from LLMService.generate()

        Returns:
            Parsed dictionary

        Raises:
            ValueError: If response cannot be parsed as JSON
        """
        if isinstance(raw_response, dict):
            return raw_response

        if not isinstance(raw_response, str):
            raise ValueError(f"Unexpected AI response type: {type(raw_response)}")

        cleaned = raw_response.strip()

        # Strip markdown code fences
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(
                "ai_response_json_parse_failed",
                error=str(e),
                snippet=cleaned[:300],
            )
            raise ValueError(f"AI response is not valid JSON: {e}")

    # -----------------------------------------------
    # Schema Validation
    # -----------------------------------------------

    @staticmethod
    def _validate_schema(
        data: Dict[str, Any],
        schema: Type[BaseModel],
        context: str,
    ) -> BaseModel:
        """
        Validate a dictionary against a Pydantic schema.

        Args:
            data: Parsed response dict
            schema: Pydantic model class
            context: Stage name for error context

        Returns:
            Validated Pydantic model

        Raises:
            ValueError: If validation fails
        """
        try:
            return schema.model_validate(data)
        except ValidationError as e:
            logger.error(
                "ai_response_schema_validation_failed",
                context=context,
                schema=schema.__name__,
                errors=e.errors(),
            )
            raise ValueError(f"AI {context} response failed schema validation: {e}")

    # -----------------------------------------------
    # Stage Validators
    # -----------------------------------------------

    def validate_entities(
        self,
        raw: Any,
        document_id: str = "",
    ) -> EntityExtractionResult:
        """
        Validate and deduplicate entity extraction results.

        Args:
            raw: Raw AI response (dict or string)
            document_id: For logging context

        Returns:
            Validated EntityExtractionResult

        Raises:
            ValueError: On schema or JSON parse failure
        """
        data = self.parse_json_response(raw)
        result = self._validate_schema(data, EntityExtractionResult, "entity_extraction")
        result = self._deduplicate_entities(result)
        logger.info(
            "entity_validation_complete",
            document_id=document_id,
            entity_count=len(result.entities),
        )
        return result

    def validate_relationships(
        self,
        raw: Any,
        document_id: str = "",
    ) -> RelationshipExtractionResult:
        """
        Validate and deduplicate relationship extraction results.

        Args:
            raw: Raw AI response
            document_id: For logging context

        Returns:
            Validated RelationshipExtractionResult

        Raises:
            ValueError: On schema or JSON parse failure
        """
        data = self.parse_json_response(raw)
        result = self._validate_schema(data, RelationshipExtractionResult, "relationship_extraction")
        result = self._deduplicate_relationships(result)
        logger.info(
            "relationship_validation_complete",
            document_id=document_id,
            relationship_count=len(result.relationships),
        )
        return result

    def validate_measurements(
        self,
        raw: Any,
        document_id: str = "",
    ) -> MeasurementExtractionResult:
        """
        Validate measurement extraction results.

        Args:
            raw: Raw AI response
            document_id: For logging context

        Returns:
            Validated MeasurementExtractionResult
        """
        data = self.parse_json_response(raw)
        result = self._validate_schema(data, MeasurementExtractionResult, "measurement_extraction")
        logger.info(
            "measurement_validation_complete",
            document_id=document_id,
            measurement_count=len(result.measurements),
        )
        return result

    def validate_procedures(
        self,
        raw: Any,
        document_id: str = "",
    ) -> ProcedureExtractionResult:
        """
        Validate procedure extraction results.

        Args:
            raw: Raw AI response
            document_id: For logging context

        Returns:
            Validated ProcedureExtractionResult
        """
        data = self.parse_json_response(raw)
        result = self._validate_schema(data, ProcedureExtractionResult, "procedure_extraction")
        logger.info(
            "procedure_validation_complete",
            document_id=document_id,
            procedure_count=len(result.procedures),
        )
        return result

    def validate_risks(
        self,
        raw: Any,
        document_id: str = "",
    ) -> RiskExtractionResult:
        """
        Validate risk extraction results.

        Args:
            raw: Raw AI response
            document_id: For logging context

        Returns:
            Validated RiskExtractionResult
        """
        data = self.parse_json_response(raw)
        result = self._validate_schema(data, RiskExtractionResult, "risk_extraction")
        logger.info(
            "risk_validation_complete",
            document_id=document_id,
            risk_count=len(result.risks),
            warning_count=len(result.warnings),
        )
        return result

    def validate_summary(
        self,
        raw: Any,
        document_id: str = "",
    ) -> DocumentSummaryResult:
        """
        Validate document summary result.

        Args:
            raw: Raw AI response
            document_id: For logging context

        Returns:
            Validated DocumentSummaryResult
        """
        data = self.parse_json_response(raw)
        result = self._validate_schema(data, DocumentSummaryResult, "summary")
        logger.info(
            "summary_validation_complete",
            document_id=document_id,
            summary_length=len(result.summary),
        )
        return result

    def validate_ontology_discovery(
        self,
        raw: Any,
        document_id: str = "",
    ) -> OntologyDiscoveryResult:
        """
        Validate ontology discovery results.

        Args:
            raw: Raw AI response
            document_id: For logging context

        Returns:
            Validated OntologyDiscoveryResult
        """
        data = self.parse_json_response(raw)
        result = self._validate_schema(data, OntologyDiscoveryResult, "ontology_discovery")
        logger.info(
            "ontology_discovery_validation_complete",
            document_id=document_id,
            new_concept_count=len(result.new_concepts),
        )
        return result

    # -----------------------------------------------
    # Confidence Filtering
    # -----------------------------------------------

    def split_by_confidence(
        self,
        entities: List[ExtractedEntity],
        threshold: float = LOW_CONFIDENCE_THRESHOLD,
    ) -> Tuple[List[ExtractedEntity], List[ExtractedEntity]]:
        """
        Split entities into accepted and flagged based on confidence threshold.

        Args:
            entities: List of extracted entities
            threshold: Minimum confidence to accept without flagging

        Returns:
            Tuple of (accepted_entities, flagged_entities)
        """
        accepted = []
        flagged = []
        for entity in entities:
            if entity.confidence >= threshold:
                accepted.append(entity)
            else:
                flagged.append(entity)
                logger.warning(
                    "low_confidence_entity_flagged",
                    entity_id=entity.entity_id,
                    entity_type=entity.entity_type,
                    confidence=entity.confidence,
                    threshold=threshold,
                )
        return accepted, flagged

    def split_relationships_by_confidence(
        self,
        relationships: List[ExtractedRelationship],
        threshold: float = MIN_RELATIONSHIP_CONFIDENCE,
    ) -> Tuple[List[ExtractedRelationship], List[ExtractedRelationship]]:
        """
        Split relationships into accepted and flagged based on confidence threshold.

        Args:
            relationships: List of extracted relationships
            threshold: Minimum confidence threshold

        Returns:
            Tuple of (accepted, flagged)
        """
        accepted = []
        flagged = []
        for rel in relationships:
            if rel.confidence >= threshold:
                accepted.append(rel)
            else:
                flagged.append(rel)
                logger.warning(
                    "low_confidence_relationship_flagged",
                    source=rel.source,
                    relationship=rel.relationship,
                    target=rel.target,
                    confidence=rel.confidence,
                )
        return accepted, flagged

    # -----------------------------------------------
    # Deduplication
    # -----------------------------------------------

    @staticmethod
    def _deduplicate_entities(
        result: EntityExtractionResult,
    ) -> EntityExtractionResult:
        """
        Remove duplicate entities by entity_id.

        Keeps the entity with the highest confidence when duplicates exist.

        Args:
            result: EntityExtractionResult to deduplicate

        Returns:
            Deduplicated EntityExtractionResult
        """
        seen: Dict[str, ExtractedEntity] = {}
        for entity in result.entities:
            eid = entity.entity_id
            if eid not in seen or entity.confidence > seen[eid].confidence:
                if eid in seen:
                    logger.warning(
                        "duplicate_entity_merged",
                        entity_id=eid,
                        kept_confidence=entity.confidence,
                    )
                seen[eid] = entity

        result.entities = list(seen.values())
        return result

    @staticmethod
    def _deduplicate_relationships(
        result: RelationshipExtractionResult,
    ) -> RelationshipExtractionResult:
        """
        Remove duplicate relationships by (source, relationship, target) tuple.

        Keeps highest confidence duplicate.

        Args:
            result: RelationshipExtractionResult to deduplicate

        Returns:
            Deduplicated RelationshipExtractionResult
        """
        seen: Dict[tuple, ExtractedRelationship] = {}
        for rel in result.relationships:
            key = (rel.source, rel.relationship, rel.target)
            if key not in seen or rel.confidence > seen[key].confidence:
                if key in seen:
                    logger.warning(
                        "duplicate_relationship_merged",
                        source=rel.source,
                        relationship=rel.relationship,
                        target=rel.target,
                    )
                seen[key] = rel

        result.relationships = list(seen.values())
        return result

    # -----------------------------------------------
    # Overall Confidence Score
    # -----------------------------------------------

    @staticmethod
    def compute_overall_confidence(
        entities: List[ExtractedEntity],
        relationships: List[ExtractedRelationship],
        summary_present: bool,
    ) -> float:
        """
        Compute an overall confidence score for the entire CKO.

        Uses average entity confidence, penalised by low relationship confidence
        and absence of summary.

        Args:
            entities: All extracted entities
            relationships: All extracted relationships
            summary_present: Whether a valid summary was generated

        Returns:
            Overall confidence score [0.0, 1.0]
        """
        scores = []

        if entities:
            avg_entity_conf = sum(e.confidence for e in entities) / len(entities)
            scores.append(avg_entity_conf)

        if relationships:
            avg_rel_conf = sum(r.confidence for r in relationships) / len(relationships)
            scores.append(avg_rel_conf)

        if summary_present:
            scores.append(0.9)  # A summary existing is a quality signal

        if not scores:
            return 0.0

        return round(sum(scores) / len(scores), 4)
