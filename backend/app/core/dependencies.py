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
from app.repositories.storage_repository import StorageRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.knowledge_repository import KnowledgeRepository
from app.events.inngest_client import InngestClient
from app.services.upload_service import UploadService
from app.services.document_service import DocumentService
from app.services.extraction_service import ExtractionService


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
# Repositories
# -----------------------------------------------

def get_storage_repository(
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> StorageRepository:
    """
    Inject StorageRepository.

    Args:
        supabase: Injected Supabase client

    Returns:
        StorageRepository instance
    """
    return StorageRepository(supabase=supabase)


def get_document_repository(
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> DocumentRepository:
    """
    Inject DocumentRepository.

    Args:
        supabase: Injected Supabase client

    Returns:
        DocumentRepository instance
    """
    return DocumentRepository(supabase=supabase)


# -----------------------------------------------
# Events
# -----------------------------------------------

@lru_cache()
def get_inngest_client() -> InngestClient:
    """
    Inject InngestClient (cached singleton).

    Returns:
        InngestClient configured for dev or production
    """
    settings = get_settings()
    return InngestClient(
        event_key=settings.INNGEST_EVENT_KEY,
        is_development=settings.is_development,
    )


# -----------------------------------------------
# Services
# -----------------------------------------------

def get_upload_service(
    storage_repo: StorageRepository = Depends(get_storage_repository),
    document_repo: DocumentRepository = Depends(get_document_repository),
    inngest: InngestClient = Depends(get_inngest_client),
) -> UploadService:
    """
    Inject UploadService.

    Args:
        storage_repo: Injected StorageRepository
        document_repo: Injected DocumentRepository
        inngest: Injected InngestClient

    Returns:
        UploadService instance
    """
    return UploadService(
        storage_repo=storage_repo,
        document_repo=document_repo,
        inngest=inngest,
    )


def get_document_service(
    document_repo: DocumentRepository = Depends(get_document_repository),
    storage_repo: StorageRepository = Depends(get_storage_repository),
) -> DocumentService:
    """
    Inject DocumentService.

    Args:
        document_repo: Injected DocumentRepository
        storage_repo: Injected StorageRepository (for delete operations)

    Returns:
        DocumentService instance
    """
    return DocumentService(
        document_repo=document_repo,
        storage_repo=storage_repo,
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


# -----------------------------------------------
# Knowledge Repository (Epic 3)
# -----------------------------------------------

def get_knowledge_repository(
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> KnowledgeRepository:
    """
    Inject KnowledgeRepository.

    Args:
        supabase: Injected Supabase client

    Returns:
        KnowledgeRepository instance
    """
    return KnowledgeRepository(supabase=supabase)


# -----------------------------------------------
# Extraction Service (Epic 3)
# -----------------------------------------------

def get_extraction_service(
    llm_service: LLMService = Depends(get_llm_service),
    knowledge_repo: KnowledgeRepository = Depends(get_knowledge_repository),
    storage_repo: StorageRepository = Depends(get_storage_repository),
    document_repo: DocumentRepository = Depends(get_document_repository),
    inngest: InngestClient = Depends(get_inngest_client),
) -> ExtractionService:
    """
    Inject ExtractionService.

    This is the AI knowledge extraction pipeline service.
    It orchestrates all 7 AI extraction stages.

    Args:
        llm_service: LLM gateway (only Gemini caller)
        knowledge_repo: CKO persistence
        storage_repo: Storage access for canonical docs
        document_repo: Document status updates
        inngest: Event emitter

    Returns:
        ExtractionService instance
    """
    return ExtractionService(
        llm_service=llm_service,
        knowledge_repo=knowledge_repo,
        storage_repo=storage_repo,
        document_repo=document_repo,
        inngest=inngest,
    )
