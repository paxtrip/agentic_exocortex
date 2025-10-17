"""
Contract tests for multi-hop connections in User Story 1.

Tests the contract between components for finding context chains in research notes.
These tests ensure the connection extraction and storage APIs work correctly
before implementing the full timeline functionality.

Following TDD principle: write tests first, ensure they fail, then implement.
"""

from typing import Any, Dict, List

import pytest
from pydantic import BaseModel, Field


class Connection(BaseModel):
    """Connection between documents."""

    source_doc_id: str
    target_doc_id: str
    connection_type: str  # 'reference', 'follow_up', 'related_concept'
    strength: float = Field(ge=0.0, le=1.0)  # 0.0 to 1.0
    context: str  # excerpt showing the connection
    created_at: str  # ISO timestamp


class ConnectionQuery(BaseModel):
    """Query for finding connections."""

    doc_id: str
    max_hops: int = 3
    min_strength: float = 0.1


class ConnectionResult(BaseModel):
    """Result of connection query."""

    connections: List[Connection]
    total_found: int
    trace_id: str


class TestConnectionContract:
    """
    Contract tests for connection functionality.

    These tests define the expected behavior of connection components
    and will fail until the implementation is complete.
    """

    def test_connection_model_validation(self):
        """Test that Connection model validates correctly."""
        # Valid connection
        conn = Connection(
            source_doc_id="doc_001",
            target_doc_id="doc_002",
            connection_type="reference",
            strength=0.8,
            context="See also: evolution of quantum computing ideas",
            created_at="2024-01-01T12:00:00Z",
        )
        assert conn.source_doc_id == "doc_001"
        assert conn.connection_type == "reference"
        assert 0 <= conn.strength <= 1

        # Invalid strength - Pydantic will raise ValidationError, not ValueError
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Connection(
                source_doc_id="doc_001",
                target_doc_id="doc_002",
                connection_type="reference",
                strength=1.5,  # Invalid: > 1.0
                context="test",
                created_at="2024-01-01T12:00:00Z",
            )

    def test_connection_query_model(self):
        """Test ConnectionQuery model validation."""
        query = ConnectionQuery(doc_id="doc_001", max_hops=2, min_strength=0.3)
        assert query.doc_id == "doc_001"
        assert query.max_hops == 2
        assert query.min_strength == 0.3

    def test_connection_result_model(self):
        """Test ConnectionResult model structure."""
        result = ConnectionResult(connections=[], total_found=0, trace_id="trace_123")
        assert len(result.connections) == 0
        assert result.total_found == 0
        assert result.trace_id == "trace_123"

    @pytest.mark.asyncio
    async def test_extract_connections_from_text(self):
        """
        Test contract for extracting connections from document text.

        This test will fail until backend/src/integrations/siyuan_connector.py
        implements the connection extraction logic.
        """
        # This is a contract test - implementation will be in siyuan_connector.py
        from backend.src.integrations.siyuan_connector import extract_connections

        text = """
        My research on quantum computing started in 2023 (see: quantum_basics.md).
        This led to experiments with algorithms (follow_up: q_algorithm_tests.md).
        The key insight was about error correction (related: error_correction_theory.md).
        """

        connections = await extract_connections("doc_001", text)

        # Should find 3 connections
        assert len(connections) == 3

        # Check connection types
        connection_types = {conn.connection_type for conn in connections}
        assert "reference" in connection_types
        assert "follow_up" in connection_types
        assert "related_concept" in connection_types

        # All strengths should be reasonable
        for conn in connections:
            assert 0.1 <= conn.strength <= 1.0
            assert conn.source_doc_id == "doc_001"

    @pytest.mark.asyncio
    async def test_store_and_retrieve_connections(self):
        """
        Test contract for storing and retrieving connections.

        This test will fail until backend/src/models/connections.py
        implements the storage and retrieval logic.
        """
        from backend.src.models.connections import ConnectionStore

        store = ConnectionStore()

        # Clear any existing connections first
        await store.clear_all_connections()

        # Store some test connections
        connections = [
            Connection(
                source_doc_id="doc_001",
                target_doc_id="doc_002",
                connection_type="reference",
                strength=0.9,
                context="See also: quantum basics",
                created_at="2024-01-01T12:00:00Z",
            ),
            Connection(
                source_doc_id="doc_001",
                target_doc_id="doc_003",
                connection_type="follow_up",
                strength=0.7,
                context="Led to experiments in",
                created_at="2024-01-02T12:00:00Z",
            ),
        ]

        # Store connections
        await store.store_connections(connections)

        # Retrieve connections for doc_001
        query = ConnectionQuery(doc_id="doc_001", max_hops=1)  # Only direct connections
        result = await store.get_connections(query)

        assert result.total_found == 2
        assert len(result.connections) == 2
        assert all(conn.source_doc_id == "doc_001" for conn in result.connections)

    @pytest.mark.asyncio
    async def test_multi_hop_connection_traversal(self):
        """
        Test contract for finding multi-hop connections.

        This test ensures we can find chains like:
        doc_A -> doc_B -> doc_C (2 hops)
        """
        from backend.src.models.connections import ConnectionStore

        store = ConnectionStore()

        # Create a chain: doc_001 -> doc_002 -> doc_003
        chain_connections = [
            Connection(
                source_doc_id="doc_001",
                target_doc_id="doc_002",
                connection_type="reference",
                strength=0.8,
                context="See doc_002",
                created_at="2024-01-01T12:00:00Z",
            ),
            Connection(
                source_doc_id="doc_002",
                target_doc_id="doc_003",
                connection_type="follow_up",
                strength=0.6,
                context="Which led to doc_003",
                created_at="2024-01-02T12:00:00Z",
            ),
        ]

        await store.store_connections(chain_connections)

        # Query for 2-hop connections from doc_001
        query = ConnectionQuery(doc_id="doc_001", max_hops=2)
        result = await store.get_connections(query)

        # Should find both direct and indirect connections
        assert result.total_found >= 2  # At least the direct connections

        # Should include doc_003 in the results
        target_docs = {conn.target_doc_id for conn in result.connections}
        assert "doc_003" in target_docs

    @pytest.mark.asyncio
    async def test_connection_strength_filtering(self):
        """
        Test that connections can be filtered by minimum strength.
        """
        from backend.src.models.connections import ConnectionStore

        store = ConnectionStore()

        # Clear any existing connections first
        await store.clear_all_connections()

        connections = [
            Connection(
                source_doc_id="doc_001",
                target_doc_id="doc_weak",
                connection_type="reference",
                strength=0.05,  # Very weak
                context="Weak reference",
                created_at="2024-01-01T12:00:00Z",
            ),
            Connection(
                source_doc_id="doc_001",
                target_doc_id="doc_strong",
                connection_type="reference",
                strength=0.9,  # Strong
                context="Strong reference",
                created_at="2024-01-01T12:00:00Z",
            ),
        ]

        await store.store_connections(connections)

        # Query with high minimum strength
        query = ConnectionQuery(doc_id="doc_001", min_strength=0.5, max_hops=1)
        result = await store.get_connections(query)

        # Should only return the strong connection
        assert result.total_found == 1
        assert result.connections[0].target_doc_id == "doc_strong"
        assert result.connections[0].strength >= 0.5
