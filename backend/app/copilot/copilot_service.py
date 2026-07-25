"""
Copilot Service Orchestrator

Top-level service for Epic 8 (AI Copilot).

Orchestrates the pipeline per Copilot.md:
  User Question
  → Conversation Manager (extracts context & resolves refs)
  → Followup Handler (enriches query)
  → Hybrid Search Service (gets ContextPackage)
  → Response Generator (calls LLMGateway)
  → Response Validator (enforces constraints)
  → Citation Builder (links and scores)
  → Final Response
"""

import time
import structlog
from typing import Optional

from app.copilot.models import CopilotResponse
from app.copilot.schemas import ChatRequest
from app.search.models import HybridSearchQuery
from app.search.search_service import SearchService as HybridSearchService

from app.copilot.conversation_manager import ConversationManager
from app.copilot.followup_handler import FollowupHandler
from app.copilot.response_generator import ResponseGenerator
from app.copilot.response_validator import ResponseValidator
from app.copilot.citation_builder import CitationBuilder
from app.copilot.constants import (
    COPILOT_DEFAULT_TOP_K,
    COPILOT_DEFAULT_MIN_SCORE,
    NO_EVIDENCE_RESPONSE,
)

logger = structlog.get_logger(__name__)


class CopilotService:
    """
    Top-level orchestrator for the AI Copilot.
    """

    def __init__(
        self,
        hybrid_search: HybridSearchService,
        conv_manager: ConversationManager,
        followup_handler: FollowupHandler,
        response_generator: ResponseGenerator,
        response_validator: ResponseValidator,
        citation_builder: CitationBuilder,
    ) -> None:
        self._search = hybrid_search
        self._conv_manager = conv_manager
        self._followup_handler = followup_handler
        self._response_generator = response_generator
        self._response_validator = response_validator
        self._citation_builder = citation_builder
        logger.info("copilot_service_initialized")

    async def ask(self, request: ChatRequest) -> CopilotResponse:
        """
        Execute the full AI Copilot pipeline.

        Args:
            request: The API ChatRequest containing the question and session_id.

        Returns:
            CopilotResponse.
        """
        start_time = time.time()
        logger.info(
            "copilot_ask_start",
            session_id=request.session_id,
            question_length=len(request.question),
        )

        try:
            # 1. Conversation Context & Reference Resolution
            conv_ctx = self._conv_manager.get_context(request.session_id, request.question)
            enriched_question = self._followup_handler.resolve(request.question, conv_ctx)

            # 2. Hybrid Search (Context Package)
            # Map ChatRequest to HybridSearchQuery
            search_query = HybridSearchQuery(
                query=enriched_question,
                top_k=request.top_k or COPILOT_DEFAULT_TOP_K,
                min_score=request.min_score or COPILOT_DEFAULT_MIN_SCORE,
                expand_graph=request.expand_graph,
                rerank=True,
            )
            # Add metadata filters if requested
            if request.filters:
                for k, v in request.filters.items():
                    setattr(search_query.filters, k, v)

            search_result = await self._search.search(search_query)
            context_package = search_result.context_package

            # 3. Response Generation (LLM Gateway)
            raw_response, usage = await self._response_generator.generate(
                question=enriched_question,
                context_package=context_package,
                conv_context=conv_ctx,
            )

            # 4. Response Validation
            validated_response = self._response_validator.validate(raw_response, context_package)

            # 5. Citation Building & Final Confidence
            citations, final_confidence = self._citation_builder.build(
                raw_response=validated_response,
                context_package=context_package,
            )

            # 6. Save Turn to Memory
            # Only save if we actually gave an answer (not the empty fallback)
            if validated_response.get("answer") != NO_EVIDENCE_RESPONSE:
                # Use the processed intent/entities from search to inform the conversation context
                active_topic = context_package.processed_query.detected_intent
                active_asset = None
                if context_package.processed_query.detected_entities:
                    active_asset = context_package.processed_query.detected_entities[0]

                self._conv_manager.save_turn(
                    session_id=request.session_id,
                    question=request.question,
                    answer=validated_response.get("answer", ""),
                    active_asset=active_asset or conv_ctx.active_asset,
                    active_topic=active_topic or conv_ctx.active_topic,
                )

            # Assemble Final Output
            duration = time.time() - start_time
            diagnostics = {
                "duration_seconds": round(duration, 3),
                "enriched_question": enriched_question,
                "search_diagnostics": search_result.diagnostics,
                "token_usage": {
                    "prompt_tokens": usage.prompt_tokens if usage else 0,
                    "completion_tokens": usage.completion_tokens if usage else 0,
                    "total_tokens": usage.total_tokens if usage else 0,
                },
            }

            logger.info(
                "copilot_ask_complete",
                session_id=request.session_id,
                duration=diagnostics["duration_seconds"],
                confidence=final_confidence,
            )

            return CopilotResponse(
                answer=validated_response.get("answer", ""),
                citations=citations,
                confidence=final_confidence,
                followup_questions=validated_response.get("follow_up_suggestions", []) or validated_response.get("followup_questions", []),
                reasoning=validated_response.get("reasoning", ""),
                related_assets=validated_response.get("related_assets", []),
                diagnostics=diagnostics,
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "copilot_ask_failed",
                session_id=request.session_id,
                error=str(e),
                duration=round(duration, 3),
            )
            raise
