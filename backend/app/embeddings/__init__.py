"""
Embeddings Module (Epic 6)

Transforms CanonicalDocuments into dense vector representations
stored in Pinecone for semantic search and GraphRAG.

Pipeline:
    graph.updated → EmbeddingService → PineconeRepository → embeddings.created

Public interface:
    EmbeddingService  — main orchestrator (use via DI: get_embedding_service())
    SearchService     — semantic search (use via DI: get_search_service())
    PineconeRepository — Pinecone CRUD (use via DI: get_pinecone_repository())
"""
