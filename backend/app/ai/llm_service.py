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

Rules:
- AI only produces structured JSON.
- Backend validates everything before use.
- AI never writes to databases.
- AI never generates Cypher.
- Prompts are always loaded from .md files.
"""

import time
from typing import Any, Dict, Optional
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.ai.prompt_manager import PromptManager

logger = structlog.get_logger(__name__)


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
    ) -> Dict[str, Any]:
        """
        Generate a structured JSON response from Gemini.

        Args:
            prompt_name: Name of the prompt template to use (without .md extension)
            variables: Variables to inject into the prompt template
            system_prompt: Optional system-level instruction override

        Returns:
            Parsed JSON response as dictionary

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

            duration = time.time() - start_time
            logger.info(
                "llm_generate_success",
                prompt_name=prompt_name,
                duration_ms=round(duration * 1000, 2),
            )
            return result

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
            )
            embedding = result["embedding"]

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
