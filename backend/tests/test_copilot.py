"""
Tests for Epic 8 (AI Copilot)

Covers:
- Conversation memory isolation across sessions
- Follow-up reference resolution (heuristics)
- Response rejection (NO_EVIDENCE_RESPONSE) when context is empty or citations missing
- Confidence score combination logic
"""

import pytest
from typing import Any, Dict, List

from app.copilot.models import (
    ConversationTurn,
    ConversationContext,
    CopilotCitation,
)
from app.search.models import (
    ContextPackage,
    ProcessedQuery,
    ContextChunk,
    Citation,
)
from app.copilot.memory_manager import MemoryManager
from app.copilot.conversation_manager import ConversationManager
from app.copilot.followup_handler import FollowupHandler
from app.copilot.response_validator import ResponseValidator
from app.copilot.citation_builder import CitationBuilder
from app.copilot.constants import NO_EVIDENCE_RESPONSE


# -------------------------------------------------------------------
# Memory & Conversation Tests
# -------------------------------------------------------------------

def test_memory_isolation_across_sessions():
    """Test that memory is strictly scoped by session_id."""
    memory = MemoryManager()
    
    turn1 = ConversationTurn(question="q1", answer="a1")
    turn2 = ConversationTurn(question="q2", answer="a2")
    
    memory.append_turn("session_A", turn1)
    memory.append_turn("session_B", turn2)
    
    hist_a = memory.get_history("session_A")
    hist_b = memory.get_history("session_B")
    
    assert len(hist_a) == 1
    assert hist_a[0].question == "q1"
    
    assert len(hist_b) == 1
    assert hist_b[0].question == "q2"


def test_followup_reference_resolution():
    """Test heuristic reference resolution for follow-up questions."""
    handler = FollowupHandler()
    
    # Context with active asset
    ctx = ConversationContext(
        session_id="test",
        history=[ConversationTurn(question="q", answer="a")],
        active_asset="P-101",
        active_topic="failure",
    )
    
    # 1. Direct replacement
    q1 = "When was it last inspected?"
    res1 = handler.resolve(q1, ctx)
    assert "P-101" in res1
    assert "it" not in res1.split()
    
    # 2. Heuristic appends context if active asset is missing from query
    q2 = "When was P-202 inspected?"
    res2 = handler.resolve(q2, ctx)
    assert res2 == "When was P-202 inspected? (context: P-101 failure)"
    
    # 3. Appending topic context if not directly replacing
    q3 = "What are the related risks?"
    res3 = handler.resolve(q3, ctx)
    # The heuristic might append "(context: P-101 failure)"
    assert "P-101" in res3
    assert "failure" in res3


# -------------------------------------------------------------------
# Response Validator Tests
# -------------------------------------------------------------------

def test_validator_rejects_empty_context():
    """Test that validator overrides answer if context package is empty."""
    validator = ResponseValidator()
    
    raw_response = {
        "answer": "I hallucinated this answer.",
        "citations": [{"chunk_id": "fake"}],
        "confidence": 0.9,
    }
    
    # Empty package
    pkg = ContextPackage(
        query="test",
        processed_query=ProcessedQuery(original_query="t", normalized_query="t", expanded_query="t"),
        chunks=[],
        graph_nodes=[],
    )
    
    validated = validator.validate(raw_response, pkg)
    assert validated["answer"] == NO_EVIDENCE_RESPONSE
    assert validated["confidence"] == 0.0


def test_validator_rejects_no_citations():
    """Test that validator overrides answer if LLM fails to cite."""
    validator = ResponseValidator()
    
    raw_response = {
        "answer": "Valid answer but no citations.",
        "citations": [],
        "confidence": 0.9,
    }
    
    pkg = ContextPackage(
        query="test",
        processed_query=ProcessedQuery(original_query="t", normalized_query="t", expanded_query="t"),
        chunks=[ContextChunk(chunk_id="1", document_id="d1", text="t")],
    )
    
    validated = validator.validate(raw_response, pkg)
    assert validated["answer"] == NO_EVIDENCE_RESPONSE


# -------------------------------------------------------------------
# Citation Builder & Confidence Scoring Tests
# -------------------------------------------------------------------

def test_citation_builder_resolves_and_scores():
    """Test citation linking to ContextPackage and hybrid confidence calculation."""
    builder = CitationBuilder()
    
    # The LLM outputs a raw citation pointing to chunk-1
    raw_response = {
        "answer": "test",
        "citations": [{"chunk_id": "chunk-1"}],
        "confidence": 0.8,
    }
    
    # The trusted ContextPackage has chunk-1 with score 0.9
    trusted_citation = Citation(
        document_id="doc-1",
        chunk_id="chunk-1",
        confidence=0.9,  # Semantic score
    )
    pkg = ContextPackage(
        query="test",
        processed_query=ProcessedQuery(
            original_query="t", normalized_query="t", expanded_query="t",
            detected_entities=[], detected_intent="general"
        ),
        chunks=[ContextChunk(chunk_id="chunk-1", document_id="doc-1", text="t", score=0.9)],
        citations=[trusted_citation],
    )
    
    citations, final_conf = builder.build(raw_response, pkg)
    
    # 1. Citation resolved correctly
    assert len(citations) == 1
    assert citations[0].document_id == "doc-1"
    assert citations[0].confidence == 0.9  # Copied from trusted
    
    # 2. Confidence formula check
    # search_signal = 0.9 (weight 0.40 = 0.36)
    # graph_signal = 0.0 (weight 0.20 = 0.0)
    # meta_signal = 1.0 (intent "general" matches anything, weight 0.20 = 0.20)
    # llm_signal = 0.8 (weight 0.20 = 0.16)
    # Total = 0.36 + 0.0 + 0.20 + 0.16 = 0.72
    assert final_conf == pytest.approx(0.72, 0.01)
