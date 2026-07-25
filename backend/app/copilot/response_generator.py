"""
Response Generator

Builds the prompt from context package + conversation history, calls LLM Gateway.
"""

import json
import structlog
from typing import Any, Dict, Tuple

from app.copilot.models import ConversationContext
from app.search.models import ContextPackage
from app.copilot.llm_gateway import LLMGateway
from app.copilot.conversation_manager import ConversationManager

logger = structlog.get_logger(__name__)


class ResponseGenerator:
    """
    Generates Copilot responses using the LLMGateway.
    """

    def __init__(self, llm_gateway: LLMGateway, conv_manager: ConversationManager) -> None:
        self._llm = llm_gateway
        self._conv_manager = conv_manager
        logger.info("response_generator_initialized")

    async def generate(
        self,
        question: str,
        context_package: ContextPackage,
        conv_context: ConversationContext,
    ) -> Tuple[Dict[str, Any], Any]:
        """
        Generate raw AI response from the ContextPackage.

        Args:
            question: Enriched user question.
            context_package: Hybrid search ContextPackage.
            conv_context: Session memory context.

        Returns:
            Tuple of (Raw response dict, TokenUsage).
        """
        logger.info(
            "response_generation_start",
            chunks=len(context_package.chunks),
            graph_nodes=len(context_package.graph_nodes),
            history_length=len(conv_context.history),
        )

        # 1. Format ContextPackage for injection
        retrieved_text = self._format_chunks(context_package)
        graph_text = self._format_graph_nodes(context_package)

        # 2. Format Conversation History
        history_text = self._conv_manager.format_history_for_prompt(conv_context.history)

        # 3. Call LLM Gateway
        variables = {
            "conversation": history_text,
            "question": question,
            "retrieved_chunks": retrieved_text,
            "graph_context": graph_text,
        }

        # Prompt template: chat.md
        result, usage = await self._llm.generate("chat", variables)

        logger.info(
            "response_generation_complete",
            answer_length=len(result.get("answer", "")),
        )
        return result, usage

    # -------------------------------------------------------------------
    # Private Formatting Helpers
    # -------------------------------------------------------------------

    def _format_chunks(self, package: ContextPackage) -> str:
        if not package.chunks:
            return "(No semantic context available)"

        lines = []
        for i, chunk in enumerate(package.chunks, 1):
            doc_name = chunk.citation.document_name if chunk.citation else chunk.document_id
            lines.append(f"--- Chunk {i} [ID: {chunk.chunk_id}] [Score: {chunk.score}] [Doc: {doc_name}] ---")
            lines.append(chunk.text.strip())
            lines.append("")
        return "\n".join(lines)

    def _format_graph_nodes(self, package: ContextPackage) -> str:
        if not package.graph_nodes:
            return "(No knowledge graph context available)"

        # Group by seed entity
        grouped = {}
        for node in package.graph_nodes:
            if node.seed_entity_id not in grouped:
                grouped[node.seed_entity_id] = []
            grouped[node.seed_entity_id].append(node)

        lines = []
        for seed, nodes in grouped.items():
            lines.append(f"Entity: {seed}")
            for n in nodes:
                rel = n.relationship or "CONNECTED_TO"
                lines.append(f"  -[{rel}]-> {n.node_id} ({n.node_label}: {n.node_name})")
        return "\n".join(lines)
