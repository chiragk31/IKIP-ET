"""
AI Response Parser

Validates and normalizes all AI (Gemini) responses before they are used
by any business service.

Rules:
- Every AI response must be validated before use.
- Required fields must be present.
- Confidence scores must be within range.
- Empty responses trigger retry logic.
- Duplicate entities must be detected and removed.

The response parser ensures that raw AI output never reaches Neo4j or Pinecone
without structural validation.
"""

import json
from typing import Any, Dict, List, Optional, Type
import structlog
from pydantic import BaseModel, ValidationError

logger = structlog.get_logger(__name__)


class ResponseParser:
    """
    Validates and parses AI responses from Gemini.

    Every AI response flows through this parser before being used by services.
    Invalid responses are logged and errors are raised with clear messages.
    """

    @staticmethod
    def parse_json(raw_response: str) -> Dict[str, Any]:
        """
        Parse raw AI response string into a dictionary.

        Args:
            raw_response: Raw string from Gemini (expected to be valid JSON)

        Returns:
            Parsed dictionary

        Raises:
            ValueError: If response is not valid JSON
        """
        if not raw_response or not raw_response.strip():
            raise ValueError("Empty AI response received")

        try:
            # Remove markdown code blocks if present
            cleaned = raw_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(
                "ai_response_json_parse_failed",
                error=str(e),
                raw_response=raw_response[:200],
            )
            raise ValueError(f"AI response is not valid JSON: {e}")

    @staticmethod
    def validate_schema(
        data: Dict[str, Any],
        schema: Type[BaseModel],
    ) -> BaseModel:
        """
        Validate a parsed response against a Pydantic schema.

        Args:
            data: Parsed response dictionary
            schema: Pydantic model class for validation

        Returns:
            Validated Pydantic model instance

        Raises:
            ValueError: If validation fails
        """
        try:
            return schema.model_validate(data)
        except ValidationError as e:
            logger.error(
                "ai_response_schema_validation_failed",
                schema=schema.__name__,
                errors=e.errors(),
            )
            raise ValueError(f"AI response failed schema validation: {e}")

    @staticmethod
    def validate_confidence(
        entities: List[Dict[str, Any]],
        min_confidence: float = 0.5,
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Split entities into accepted and flagged based on confidence threshold.

        Args:
            entities: List of entity dicts with confidence field
            min_confidence: Minimum confidence threshold (default 0.5)

        Returns:
            Tuple of (accepted_entities, flagged_entities)
        """
        accepted = []
        flagged = []

        for entity in entities:
            confidence = entity.get("confidence", 0.0)
            if confidence >= min_confidence:
                accepted.append(entity)
            else:
                flagged.append(entity)
                logger.warning(
                    "low_confidence_entity_flagged",
                    entity_id=entity.get("entity_id"),
                    entity_type=entity.get("entity_type"),
                    confidence=confidence,
                )

        return accepted, flagged

    @staticmethod
    def deduplicate_entities(
        entities: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Remove duplicate entities by entity_id.

        Args:
            entities: List of entity dicts

        Returns:
            Deduplicated list of entities
        """
        seen_ids = set()
        unique_entities = []

        for entity in entities:
            entity_id = entity.get("entity_id")
            if entity_id and entity_id not in seen_ids:
                seen_ids.add(entity_id)
                unique_entities.append(entity)
            elif entity_id in seen_ids:
                logger.warning(
                    "duplicate_entity_removed",
                    entity_id=entity_id,
                )

        return unique_entities

    @staticmethod
    def require_fields(
        data: Dict[str, Any],
        required_fields: List[str],
        context: str = "",
    ) -> None:
        """
        Verify required fields exist in the response.

        Args:
            data: Parsed response dictionary
            required_fields: List of field names that must be present
            context: Context string for error messages

        Raises:
            ValueError: If any required field is missing
        """
        missing = [f for f in required_fields if f not in data]
        if missing:
            logger.error(
                "ai_response_missing_required_fields",
                context=context,
                missing_fields=missing,
            )
            raise ValueError(
                f"AI response missing required fields: {missing}"
                + (f" (context: {context})" if context else "")
            )
