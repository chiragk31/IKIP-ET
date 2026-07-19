"""
FastAPI Dependency Injection

Provides reusable dependencies for all API routes.
All external service clients are created here and injected as dependencies.

Pattern: API Route → Dependency → Service → Repository → SDK
"""

from functools import lru_cache
from fastapi import Depends
from app.core.config import Settings, get_settings
from app.database.supabase import SupabaseClient
from app.database.neo4j_client import Neo4jClient
from app.database.pinecone_client import PineconeClient
from app.ai.llm_service import LLMService
from app.ai.prompt_manager import PromptManager


# -----------------------------------------------
# Settings Dependency
# -----------------------------------------------

def get_app_settings() -> Settings:
    """
    Inject application settings.

    Returns:
        Settings: Application configuration
    """
    return get_settings()


# -----------------------------------------------
# Database Clients
# -----------------------------------------------

@lru_cache()
def get_supabase_client() -> SupabaseClient:
    """
    Inject Supabase client (cached singleton).

    Returns:
        SupabaseClient: Configured Supabase client
    """
    settings = get_settings()
    return SupabaseClient(
        url=settings.SUPABASE_URL,
        service_role_key=settings.SUPABASE_SERVICE_ROLE_KEY,
    )


@lru_cache()
def get_neo4j_client() -> Neo4jClient:
    """
    Inject Neo4j driver (cached singleton).

    Returns:
        Neo4jClient: Configured Neo4j client
    """
    settings = get_settings()
    return Neo4jClient(
        uri=settings.NEO4J_URI,
        username=settings.NEO4J_USERNAME,
        password=settings.NEO4J_PASSWORD,
    )


@lru_cache()
def get_pinecone_client() -> PineconeClient:
    """
    Inject Pinecone client (cached singleton).

    Returns:
        PineconeClient: Configured Pinecone client
    """
    settings = get_settings()
    return PineconeClient(
        api_key=settings.PINECONE_API_KEY,
        index_name=settings.PINECONE_INDEX,
    )


# -----------------------------------------------
# AI Services
# -----------------------------------------------

@lru_cache()
def get_prompt_manager() -> PromptManager:
    """
    Inject PromptManager (cached singleton).
    Loads all prompt templates from disk on first call.

    Returns:
        PromptManager: Prompt template manager
    """
    return PromptManager()


@lru_cache()
def get_llm_service(
    prompt_manager: PromptManager = Depends(get_prompt_manager),
) -> LLMService:
    """
    Inject LLMService (cached singleton).
    This is the ONLY service that may call Gemini directly.

    Args:
        prompt_manager: Injected PromptManager

    Returns:
        LLMService: Configured LLM gateway
    """
    settings = get_settings()
    return LLMService(
        api_key=settings.GEMINI_API_KEY,
        model=settings.GEMINI_MODEL,
        temperature=settings.GEMINI_TEMPERATURE,
        max_retries=settings.GEMINI_MAX_RETRIES,
        timeout=settings.GEMINI_TIMEOUT,
        prompt_manager=prompt_manager,
    )
