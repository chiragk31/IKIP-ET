"""
Tests for Epic 7 (Hybrid Search)

Covers:
- Query validation (injection rejection, depth limits)
- Query processing and rewriting
- Semantic search delegation
- Metadata filtering correctness
- Graph expansion depth limits
- Reranking order
- Context package shape
"""

import pytest
from typing import List, Dict, Any

from app.search.models import (
    HybridSearchQuery,
    MetadataFilters,
    ProcessedQuery,
    ContextChunk,
    GraphExpansionNode,
    Citation,
)
from app.search.search_validator import SearchValidator
from app.search.query_processor import QueryProcessor
from app.search.query_rewriter import QueryRewriter
from app.search.semantic_search import SemanticSearch
from app.search.metadata_filter import MetadataFilter
from app.search.graph_search import GraphSearch
from app.search.reranker import Reranker
from app.search.context_builder import ContextBuilder
from app.search.search_service import SearchService


# -------------------------------------------------------------------
# Mocks
# -------------------------------------------------------------------

class MockLLMService:
    async def generate(self, *args, **kwargs):
        class MockResponse:
            raw_response = '{"original_question": "test", "search_queries": ["expanded test"]}'
        return MockResponse()


class MockEpic6SearchService:
    async def search(self, query):
        class MockResult:
            chunk_id = "chunk-1"
            document_id = "doc-1"
            score = 0.8
            text = "test text"
            section = "test"
            page_number = 1
            graph_entities = ["P-101"]
            metadata = {"document_type": "maintenance_report"}

        class MockResponse:
            results = [MockResult()]
            total_results = 1

        return MockResponse()


class MockGraphRepository:
    def get_neighbors(self, entity_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        if entity_id == "P-101":
            return [
                {"neighbor_id": "V-201", "neighbor_name": "Valve 201", "neighbor_label": "Asset", "relationship": "CONNECTED_TO"}
            ]
        elif entity_id == "V-201":
            return [
                {"neighbor_id": "T-301", "neighbor_name": "Tank 301", "neighbor_label": "Asset", "relationship": "LOCATED_IN"}
            ]
        return []


# -------------------------------------------------------------------
# Tests
# -------------------------------------------------------------------

@pytest.fixture
def validator():
    return SearchValidator()


@pytest.fixture
def processor():
    return QueryProcessor()


@pytest.fixture
def rewriter():
    return QueryRewriter(llm_service=MockLLMService())


@pytest.fixture
def meta_filter():
    return MetadataFilter()


@pytest.fixture
def graph_search():
    return GraphSearch(graph_repo=MockGraphRepository())


@pytest.fixture
def reranker():
    return Reranker()


def test_validator_rejects_injection(validator):
    """Test that query injection patterns are rejected."""
    query = HybridSearchQuery(query="MATCH (n) RETURN n")
    with pytest.raises(ValueError, match="Raw database query syntax is not permitted"):
        validator.validate(query)


def test_validator_rejects_depth_above_3(validator):
    """Test that graph_depth > 3 is rejected."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        HybridSearchQuery(query="valid query", graph_depth=4)


def test_validator_rejects_filter_injection(validator):
    """Test that filter values are scanned for injection."""
    filters = MetadataFilters(asset_id="P-101; DROP TABLE")
    query = HybridSearchQuery(query="valid query", filters=filters)
    with pytest.raises(ValueError, match="Filter field 'asset_id' contains a disallowed pattern"):
        validator.validate(query)


def test_processor_detects_entities_and_intent(processor):
    """Test query processor extracts P-101 and detects failure intent."""
    query_str = "Why did Pump P-101 fail?"
    processed = processor.process(query_str)
    assert "P-101" in processed.detected_entities
    assert processed.detected_intent == "failure"


@pytest.mark.asyncio
async def test_rewriter_expands_query(rewriter):
    """Test LLM-based query rewriting."""
    processed = ProcessedQuery(
        original_query="P-101 fail",
        normalized_query="P-101 fail",
        expanded_query="P-101 fail",
    )
    result = await rewriter.rewrite(processed)
    assert "expanded test" in result.expanded_query


def test_metadata_filter_correctness(meta_filter):
    """Test in-memory metadata filtering."""
    chunks = [
        ContextChunk(chunk_id="1", document_id="d1", text="a", asset_ids=["P-101"], document_type="maintenance_report"),
        ContextChunk(chunk_id="2", document_id="d2", text="b", asset_ids=["V-201"], document_type="procedure"),
    ]
    filters = MetadataFilters(asset_id="P-101", document_type="maintenance_report")
    filtered = meta_filter.filter_chunks(chunks, filters)
    assert len(filtered) == 1
    assert filtered[0].chunk_id == "1"


def test_graph_expansion_depth(graph_search):
    """Test graph expansion stops at requested depth."""
    # Depth 1: from P-101, we should find V-201 only
    nodes_d1 = graph_search.expand(["P-101"], depth=1)
    assert len(nodes_d1) == 1
    assert nodes_d1[0].node_id == "V-201"
    assert nodes_d1[0].hop == 1

    # Depth 2: from P-101 -> V-201 -> T-301
    nodes_d2 = graph_search.expand(["P-101"], depth=2)
    assert len(nodes_d2) == 2
    ids = {n.node_id for n in nodes_d2}
    assert "V-201" in ids
    assert "T-301" in ids


def test_reranker_order(reranker):
    """Test that graph proximity and metadata matches boost scores."""
    chunks = [
        ContextChunk(chunk_id="1", document_id="d1", text="a", score=0.6, graph_entities=["UNKNOWN"], document_type="other"),
        ContextChunk(chunk_id="2", document_id="d2", text="b", score=0.5, graph_entities=["V-201"], document_type="maintenance_report"),
    ]
    nodes = [GraphExpansionNode(node_id="V-201")]
    query = ProcessedQuery(original_query="fail", normalized_query="fail", expanded_query="fail", detected_intent="failure")

    # Chunk 2 has lower initial score, but overlaps with graph nodes AND matches intent (failure + maintenance)
    reranked = reranker.rerank(chunks, nodes, query)
    assert reranked[0].chunk_id == "2"
    assert reranked[1].chunk_id == "1"
    assert reranked[0].score > reranked[1].score


@pytest.mark.asyncio
async def test_full_search_service_context_package_shape():
    """Test the full orchestrator builds the correct context package."""
    validator = SearchValidator()
    processor = QueryProcessor()
    rewriter = QueryRewriter(llm_service=MockLLMService())
    semantic = SemanticSearch(search_svc=MockEpic6SearchService())
    meta_filter = MetadataFilter()
    graph_search = GraphSearch(graph_repo=MockGraphRepository())
    context_builder = ContextBuilder()
    reranker = Reranker()

    service = SearchService(
        validator, processor, rewriter, semantic,
        meta_filter, graph_search, context_builder, reranker
    )

    query = HybridSearchQuery(query="P-101 failure")
    result = await service.search(query)

    assert result.total_results == 1
    assert len(result.chunks) == 1
    assert len(result.graph_nodes) > 0
    assert len(result.citations) == 1

    # Check ContextPackage shape
    pkg = result.context_package
    assert pkg.query == "P-101 failure"
    assert pkg.processed_query.detected_intent == "failure"
    assert "P-101" in pkg.processed_query.detected_entities
    assert pkg.chunks[0].chunk_id == "chunk-1"
    assert pkg.citations[0].document_id == "doc-1"
