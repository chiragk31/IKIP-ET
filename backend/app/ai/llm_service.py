"""
LLM Service — The Only Gemini Gateway

This is the SINGLE entry point for all Gemini AI calls in the platform.

No other module, service, agent, or repository may call Gemini directly.
Every AI interaction must flow through this service.

Architecture:
    Business Service → LLMService → Gemini → Structured JSON Response

Responsibilities:
- Load and render prompt templates via PromptManager
- Call Gemini with retry logic and timeout handling
- Parse and validate AI responses
- Log all AI interactions with timing and status
- Handle rate limiting and errors gracefully
- Return token usage per call so callers can accumulate totals

Rules:
- AI only produces structured JSON.
- Backend validates everything before use.
- AI never writes to databases.
- AI never generates Cypher.
- Prompts are always loaded from .md files.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.ai.prompt_manager import PromptManager

logger = structlog.get_logger(__name__)


@dataclass
class TokenUsage:
    """
    Token usage metadata returned by a single LLM call.

    Callers (ExtractionService) should accumulate these across stages
    to build accurate total token counts for the CKO.
    """
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        """Support accumulation with + operator."""
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            estimated_cost_usd=self.estimated_cost_usd + other.estimated_cost_usd,
        )

    @classmethod
    def zero(cls) -> "TokenUsage":
        """Return a zero-valued TokenUsage for accumulation start."""
        return cls(prompt_tokens=0, completion_tokens=0, total_tokens=0, estimated_cost_usd=0.0)


class LLMService:
    """
    LLM Gateway — Central service for all Gemini interactions.

    This class is a singleton injected via FastAPI dependencies.
    It is the ONLY class in the system allowed to call Gemini.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float,
        max_retries: int,
        timeout: int,
        prompt_manager: PromptManager,
    ) -> None:
        """
        Initialize the LLM Service.

        Args:
            api_key: Google Gemini API key
            model: Model name (e.g., gemini-2.5-flash)
            temperature: Sampling temperature (0.0 = deterministic)
            max_retries: Maximum retry attempts on failure
            timeout: Request timeout in seconds
            prompt_manager: Prompt template manager
        """
        self.model_name = model
        self.temperature = temperature
        self.max_retries = max_retries
        self.timeout = timeout
        self.prompt_manager = prompt_manager
        self._model = None

        # Initialize Gemini client
        self._initialize_client(api_key)
        logger.info("llm_service_initialized", model=model, temperature=temperature)

    def _initialize_client(self, api_key: str) -> None:
        """
        Initialize the Google Generative AI client.

        Args:
            api_key: Gemini API key
        """
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self._model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config={
                    "temperature": self.temperature,
                    "response_mime_type": "application/json",
                },
            )
            logger.info("gemini_client_configured", model=self.model_name)
        except ImportError:
            logger.warning("gemini_sdk_not_installed")
            self._model = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True,
    )
    async def generate(
        self,
        prompt_name: str,
        variables: Dict[str, Any],
        system_prompt: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], TokenUsage]:
        """
        Generate a structured JSON response from Gemini.

        Returns BOTH the parsed result and the token usage so callers
        can accumulate token counts across multiple LLM stages.

        Args:
            prompt_name: Name of the prompt template to use (without .md extension)
            variables: Variables to inject into the prompt template
            system_prompt: Optional system-level instruction override

        Returns:
            Tuple of (parsed JSON response dict, TokenUsage)

        Raises:
            ValueError: If response is not valid JSON or fails validation
            Exception: If Gemini API call fails after retries
        """
        start_time = time.time()
        logger.info("llm_generate_start", prompt_name=prompt_name)

        try:
            # Load and render the prompt template
            rendered_prompt = self.prompt_manager.render(prompt_name, variables)

            if self._model is None:
                raise RuntimeError("Gemini model not initialized. Check API key configuration.")

            # Call Gemini
            response = self._model.generate_content(rendered_prompt)
            raw_text = response.text

            # Parse JSON response
            import json
            result = json.loads(raw_text)

            # Extract token usage and compute cost
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0
            estimated_cost = 0.0

            if hasattr(response, "usage_metadata") and response.usage_metadata:
                prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
                completion_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
                total_tokens = getattr(response.usage_metadata, "total_token_count", 0) or 0
                # Gemini 2.5 Flash prices: $0.075/M input, $0.30/M output
                estimated_cost = (prompt_tokens * 0.075 / 1_000_000) + (completion_tokens * 0.30 / 1_000_000)

            usage = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=round(estimated_cost, 6),
            )

            duration = time.time() - start_time
            logger.info(
                "llm_generate_success",
                prompt_name=prompt_name,
                model_name=self.model_name,
                duration_ms=round(duration * 1000, 2),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=round(estimated_cost, 6),
            )
            return result, usage

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "llm_generate_failed",
                prompt_name=prompt_name,
                error=str(e),
                duration_ms=round(duration * 1000, 2),
            )
            raise

    async def generate_embedding(self, text: str) -> list[float]:
        """
        Generate a text embedding using Google's embedding model.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            Exception: If embedding generation fails
        """
        start_time = time.time()
        logger.info("llm_embedding_start", text_length=len(text))

        try:
            import google.generativeai as genai
            from app.core.config import settings

            result = genai.embed_content(
                model=settings.EMBEDDING_MODEL,
                content=text,
                task_type="retrieval_document",
                output_dimensionality=settings.EMBEDDING_DIMENSION,  # AD-022: MRL 768-d truncation
            )
            embedding = result["embedding"]

            # Fail loud if API returns a different dimension than config expects.
            # This would indicate a model/config drift and must surface immediately,
            # not silently produce wrong-shaped vectors that land in Pinecone.
            # (AD-022: this pattern caught the text-embedding-004 → gemini-embedding-001
            #  migration gap during live verification — not by the unit test suite.)
            if len(embedding) != settings.EMBEDDING_DIMENSION:
                raise ValueError(
                    f"Embedding dimension mismatch: config expects "
                    f"{settings.EMBEDDING_DIMENSION}d but model '{settings.EMBEDDING_MODEL}' "
                    f"returned {len(embedding)}d. Update EMBEDDING_MODEL or "
                    f"EMBEDDING_DIMENSION in config.py."
                )

            duration = time.time() - start_time
            logger.info(
                "llm_embedding_success",
                dimension=len(embedding),
                duration_ms=round(duration * 1000, 2),
            )
            return embedding

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "llm_embedding_failed",
                error=str(e),
                duration_ms=round(duration * 1000, 2),
            )
            raise

    async def health_check(self) -> Dict[str, Any]:
        """
        Verify Gemini API is accessible.

        Returns:
            Dict with status and model info
        """
        try:
            if self._model is None:
                return {"status": "down", "error": "Model not initialized"}

            # Send a minimal test prompt
            response = self._model.generate_content(
                '{"test": true}',
            )
            return {
                "status": "up",
                "model": self.model_name,
                "response_received": True,
            }
        except Exception as e:
            logger.error("gemini_health_check_failed", error=str(e))
            return {"status": "down", "error": str(e)}
