"""
Health Check API Tests

Tests for the /api/v1/health endpoint.
These tests verify that the health check endpoint returns correct structure
even when external services are unavailable (graceful degradation).
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch


@pytest.fixture
def client():
    """Create test client with mocked external dependencies."""
    from app.main import app
    return TestClient(app)


def test_health_endpoint_exists(client):
    """Health endpoint should return a response."""
    response = client.get("/api/v1/health")
    assert response.status_code in [200, 503]


def test_health_response_structure(client):
    """Health response should have the expected structure."""
    response = client.get("/api/v1/health")
    data = response.json()

    assert "status" in data
    assert "services" in data
    assert isinstance(data["services"], dict)


def test_health_service_keys(client):
    """Health response should report on all required services."""
    response = client.get("/api/v1/health")
    data = response.json()

    expected_services = {"supabase", "neo4j", "pinecone", "gemini"}
    actual_services = set(data["services"].keys())

    assert expected_services == actual_services
