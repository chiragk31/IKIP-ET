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
from app.ontology.ontology_repository import OntologyRepository
from app.ontology.ontology_manager import OntologyManager
from app.graph.graph_repository import GraphRepository
from app.graph.graph_service import GraphService
from app.embeddings.pinecone_repository import PineconeRepository
from app.embeddings.embedding_provider import GoogleEmbeddingProvider
from app.embeddings.embedding_service import EmbeddingService
from app.embeddings.search_service import SearchService as Epic6SearchService
from app.search.search_validator import SearchValidator
from app.search.query_processor import QueryProcessor
from app.search.query_rewriter import QueryRewriter
from app.search.semantic_search import SemanticSearch
from app.search.metadata_filter import MetadataFilter
from app.search.graph_search import GraphSearch
from app.search.context_builder import ContextBuilder
from app.search.reranker import Reranker
from app.search.search_service import SearchService as HybridSearchService


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


# -----------------------------------------------
# Ontology Management (Epic 4)
# -----------------------------------------------

def get_ontology_repository(
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> OntologyRepository:
    """Inject OntologyRepository."""
    return OntologyRepository(supabase=supabase)


def get_ontology_manager(
    ontology_repo: OntologyRepository = Depends(get_ontology_repository),
) -> OntologyManager:
    """Inject OntologyManager."""
    return OntologyManager(ontology_repo=ontology_repo)


# -----------------------------------------------
# Graph Builder (Epic 5)
# -----------------------------------------------

def get_graph_repository(
    neo4j: Neo4jClient = Depends(get_neo4j_client),
) -> GraphRepository:
    """
    Inject GraphRepository.

    This is the ONLY Neo4j writer in the entire platform.

    Args:
        neo4j: Injected Neo4j client

    Returns:
        GraphRepository instance
    """
    return GraphRepository(neo4j=neo4j)


def get_graph_service(
    ontology_repo: OntologyRepository = Depends(get_ontology_repository),
    graph_repo: GraphRepository = Depends(get_graph_repository),
) -> GraphService:
    """
    Inject GraphService.

    Orchestrates the NKO → Neo4j graph build pipeline.

    Args:
        ontology_repo: Repository to load the NKO from Supabase Storage
        graph_repo: Repository to write nodes/relationships to Neo4j

    Returns:
        GraphService instance
    """
    return GraphService(
        ontology_repo=ontology_repo,
        graph_repo=graph_repo,
    )


# -----------------------------------------------
# Pinecone Repository (Epic 6)
# -----------------------------------------------

def get_pinecone_repository() -> PineconeRepository:
    """
    Inject PineconeRepository.

    This is the ONLY module that calls the Pinecone SDK directly.

    Returns:
        PineconeRepository instance.
    """
    pinecone_client = get_pinecone_client()
    return PineconeRepository(pinecone_client=pinecone_client)


# -----------------------------------------------
# Embedding Service (Epic 6)
# -----------------------------------------------

def get_embedding_service(
    storage_repo: StorageRepository = Depends(get_storage_repository),
    ontology_repo: OntologyRepository = Depends(get_ontology_repository),
    llm_service: LLMService = Depends(get_llm_service),
    pinecone_repo: PineconeRepository = Depends(get_pinecone_repository),
) -> EmbeddingService:
    """
    Inject EmbeddingService.

    Orchestrates the CanonicalDocument → Pinecone embedding pipeline.

    Args:
        storage_repo: For loading the CanonicalDocument from Supabase Storage.
        ontology_repo: For loading the NKO from Supabase Storage.
        llm_service: For generating embeddings (routed through GoogleEmbeddingProvider).
        pinecone_repo: For upserted embedded chunks to Pinecone.

    Returns:
        EmbeddingService instance.
    """
    embedding_provider = GoogleEmbeddingProvider(llm_service=llm_service)
    return EmbeddingService(
        storage_repo=storage_repo,
        ontology_repo=ontology_repo,
        embedding_provider=embedding_provider,
        pinecone_repo=pinecone_repo,
    )


# -----------------------------------------------
# Search Service (Epic 6)
# -----------------------------------------------

def get_search_service(
    llm_service: LLMService = Depends(get_llm_service),
    pinecone_repo: PineconeRepository = Depends(get_pinecone_repository),
) -> Epic6SearchService:
    """
    Inject SearchService (Epic 6).
    """
    embedding_provider = GoogleEmbeddingProvider(llm_service=llm_service)
    return Epic6SearchService(
        embedding_provider=embedding_provider,
        pinecone_repo=pinecone_repo,
    )


# -----------------------------------------------
# Hybrid Search Service (Epic 7)
# -----------------------------------------------

def get_hybrid_search_service(
    llm_service: LLMService = Depends(get_llm_service),
    epic6_search_service: Epic6SearchService = Depends(get_search_service),
    graph_repo: GraphRepository = Depends(get_graph_repository),
) -> HybridSearchService:
    """
    Inject HybridSearchService (Epic 7 orchestrator).
    """
    validator = SearchValidator()
    processor = QueryProcessor()
    rewriter = QueryRewriter(llm_service=llm_service)
    semantic = SemanticSearch(search_svc=epic6_search_service)
    meta_filter = MetadataFilter()
    graph_search = GraphSearch(graph_repo=graph_repo)
    context_builder = ContextBuilder()
    reranker = Reranker()

    return HybridSearchService(
        validator=validator,
        processor=processor,
        rewriter=rewriter,
        semantic=semantic,
        meta_filter=meta_filter,
        graph_search=graph_search,
        context_builder=context_builder,
        reranker=reranker,
    )
