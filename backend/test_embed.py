"""
Phase 6 Full Live Verification Script

Checklist:
1. Confirm embedding produces correct 768-d vectors (gemini-embedding-001 + output_dimensionality)
2. Trigger embed on test document — confirm vectors land in Pinecone with correct count
3. Run semantic search — confirm relevant result is returned with expected metadata  
4. Run embed a SECOND time — confirm idempotency (vector count does NOT increase)
"""
import asyncio
import json
import dataclasses
from app.core.config import settings
from app.core.dependencies import (
    get_storage_repository, get_ontology_repository, 
    get_llm_service, get_pinecone_repository, get_supabase_client
)
from app.embeddings.embedding_provider import GoogleEmbeddingProvider
from app.embeddings.embedding_service import EmbeddingService
from app.embeddings.search_service import SearchService
from app.embeddings.models import SearchQuery
from app.canonical.canonical_models import (
    CanonicalDocument, CanonicalSection, CanonicalPage, DocumentMetadata
)
from app.ontology.models import NormalizedKnowledgeObject, NormalizedEntity

DOC_ID = "test-doc-embed-live-01"

def get_pinecone_vector_count(pinecone_repo, doc_id: str) -> int:
    """Fetch exact vector count for this document from Pinecone."""
    # Query top_k=100 to count existing vectors
    result = pinecone_repo.query(
        vector=[0.0] * 768,
        top_k=100,
        filter={"document_id": {"$eq": doc_id}},
    )
    return len(result.get("matches", []))


async def main():
    print("=" * 60)
    print("Phase 6 — Full Live Verification")
    print(f"Model: {settings.EMBEDDING_MODEL}")
    print(f"Dimension: {settings.EMBEDDING_DIMENSION}")
    print("=" * 60)

    # --- Init services ---
    supabase = get_supabase_client()
    storage = get_storage_repository(supabase)
    ontology = get_ontology_repository(supabase)
    llm = get_llm_service()
    pinecone_repo = get_pinecone_repository()

    provider = GoogleEmbeddingProvider(llm)
    embedding_svc = EmbeddingService(storage, ontology, provider, pinecone_repo)
    search_svc = SearchService(provider, pinecone_repo)

    # -------------------------------------------------------
    # Step 1: Verify embedding produces 768-d vector directly
    # -------------------------------------------------------
    print("\n[STEP 1] Direct API check — model returns 768-d vector")
    test_vec = await provider.embed_batch(["pump P-101 quarterly maintenance"])
    dim = len(test_vec[0])
    assert dim == 768, f"FAIL: Expected 768-d, got {dim}-d"
    print(f"  ✓ Vector dimension: {dim}")

    # -------------------------------------------------------
    # Step 2: Ensure test document exists in Supabase Storage
    # -------------------------------------------------------
    print("\n[STEP 2] Uploading test CanonicalDocument + NKO to Supabase")
    doc = CanonicalDocument(
        document_id=DOC_ID,
        original_filename="test_doc.pdf",
        storage_path=f"processed/{DOC_ID}/canonical.json",
        metadata=DocumentMetadata(file_type="pdf", language="en"),
        sections=[CanonicalSection(
            heading="Test Operations", level=1,
            text=(
                "The Pump P-101 operates well under normal conditions. "
                "We need more than fifty tokens for the chunk strategy filter. "
                "Centrifugal pump maintenance is critical. Check the seal daily. "
                "Bearing clearance must be within manufacturer tolerance for reliable operation."
            ),
            page_number=1
        )],
        tables=[], pages=[],
        full_text="",
        language="en"
    )
    doc_bytes = json.dumps(dataclasses.asdict(doc)).encode("utf-8")
    supabase.client.storage.from_("documents").upload(
        path=doc.storage_path,
        file=doc_bytes,
        file_options={"content-type": "application/json", "upsert": "true"}
    )
    print(f"  ✓ CanonicalDocument uploaded to {doc.storage_path}")

    nko = NormalizedKnowledgeObject(
        document_id=DOC_ID,
        entities=[NormalizedEntity(
            entity_id="asset_p101", entity_type="Asset",
            canonical_name="Pump P-101", aliases=["P-101", "Main Pump"],
            confidence=0.95, metadata={}, source_document_ids=[DOC_ID]
        )],
        relationships=[], discovered_concepts=[], confidence=0.9
    )
    ontology.save_nko(nko)
    print(f"  ✓ NKO saved (1 entity)")

    # -------------------------------------------------------
    # Step 3: First embed — confirm vectors land in Pinecone
    # -------------------------------------------------------
    print("\n[STEP 3] First embed run")
    result1 = await embedding_svc.embed(DOC_ID)
    print(f"  status: {result1.status}")
    print(f"  chunks_generated: {result1.chunks_generated}")
    print(f"  vectors_upserted: {result1.vectors_upserted}")
    assert result1.status == "completed", f"FAIL: {result1.error_message}"
    assert result1.vectors_upserted >= 1, "FAIL: No vectors upserted"

    # Count in Pinecone after first run
    await asyncio.sleep(2)  # brief delay for Pinecone consistency
    count_after_first = get_pinecone_vector_count(pinecone_repo, DOC_ID)
    print(f"  Pinecone vector count after 1st run: {count_after_first}")
    assert count_after_first >= 1, f"FAIL: Vectors not found in Pinecone"
    print(f"  ✓ Vectors confirmed in Pinecone ({count_after_first} vectors)")

    # -------------------------------------------------------
    # Step 4: Semantic search — confirm relevant result
    # -------------------------------------------------------
    print("\n[STEP 4] Semantic search")
    query = SearchQuery(
        query="How does the pump P-101 operate?",
        top_k=5,
        min_score=0.5,
    )
    search_result = await search_svc.search(query)
    print(f"  total_results: {search_result.total_results}")
    assert search_result.total_results >= 1, "FAIL: No search results returned"
    top = search_result.results[0]
    print(f"  Top result score: {top.score:.4f}")
    print(f"  Top result section: {top.section}")
    print(f"  Top result document_id: {top.document_id}")
    print(f"  graph_entities: {top.graph_entities}")
    print(f"  embedding_model in metadata: {top.metadata.get('embedding_model', 'NOT SET')}")
    assert "asset_p101" in top.graph_entities, "FAIL: Entity asset_p101 not in graph_entities"
    print(f"  ✓ Search returned relevant result with correct entity enrichment")

    # -------------------------------------------------------
    # Step 5: Second embed — confirm idempotency
    # -------------------------------------------------------
    print("\n[STEP 5] Second embed run (idempotency check)")
    result2 = await embedding_svc.embed(DOC_ID)
    print(f"  status: {result2.status}")
    print(f"  chunks_generated: {result2.chunks_generated}")
    print(f"  vectors_upserted: {result2.vectors_upserted}")
    print(f"  chunks_skipped: {result2.chunks_skipped}")

    await asyncio.sleep(2)
    count_after_second = get_pinecone_vector_count(pinecone_repo, DOC_ID)
    print(f"  Pinecone vector count after 2nd run: {count_after_second}")
    assert count_after_second == count_after_first, (
        f"FAIL: Idempotency broken — count went from {count_after_first} to {count_after_second}"
    )
    print(f"  ✓ Idempotency confirmed: vector count unchanged ({count_after_first} → {count_after_second})")

    # -------------------------------------------------------
    # Final summary
    # -------------------------------------------------------
    print("\n" + "=" * 60)
    print("LIVE VERIFICATION PASSED ✓")
    print(f"  Model: {settings.EMBEDDING_MODEL}")
    print(f"  Dimension: {dim}d (Pinecone index: 768d)")
    print(f"  Vectors in Pinecone: {count_after_second}")
    print(f"  Search score: {top.score:.4f}")
    print(f"  Idempotency: CONFIRMED")
    print("=" * 60)


asyncio.run(main())
