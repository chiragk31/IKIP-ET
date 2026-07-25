"""
LLM Gateway

Thin wrapper around LLMService enforcing provider independence.

Per Copilot.md §Provider Independence:
"Switching providers should require configuration only."
Currently, LLMService abstracts Gemini. LLMGateway abstracts LLMService
so Copilot is fully decoupled from the underlying provider's specifics
(e.g., handling TokenUsage tuple returns, which Search.QueryRewriter also dealt with).
"""

import structlog
from typing import Any, Dict, Tuple

from app.ai.llm_service import LLMService, TokenUsage

logger = structlog.get_logger(__name__)


class LLMGateway:
    """
    Decouples the AI Copilot from the underlying LLM provider implementation.
    """

    def __init__(self, llm_service: LLMService) -> None:
        """
        Initialize the LLM Gateway.

        Args:
            llm_service: The underlying provider service (currently Gemini).
        """
        self._llm = llm_service
        logger.info("llm_gateway_initialized")

    async def generate(
        self,
        prompt_name: str,
        variables: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], TokenUsage]:
        """
        Generate a structured JSON response from the underlying provider.

        Args:
            prompt_name: Prompt template name without .md extension.
            variables: Variables to inject.

        Returns:
            Tuple of (Parsed JSON dictionary, TokenUsage).
        """
        logger.debug("llm_gateway_request", prompt_name=prompt_name)
        result, token_usage = await self._llm.generate(
            prompt_name=prompt_name,
            variables=variables,
        )
        return result, token_usage
