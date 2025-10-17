"""
Integration tests for writer workflow (User Story 3).

Tests the complete end-to-end flow for writers discovering idea connections:
1. Store interconnected writing documents
2. Extract semantic relationships between them
3. Query and retrieve relationship graphs
4. Verify relationships are meaningful and accurate

These tests ensure the writer workflow works from document storage
through relationship extraction to graph visualization.
"""

from typing import Any, Dict, List
from unittest.mock import Mock, patch

import pytest


class TestWriterWorkflowIntegration:
    """Integration tests for the complete writer workflow."""

    @pytest.fixture
    def sample_writing_documents(self) -> List[Dict[str, Any]]:
        """Sample interconnected writing documents for testing."""
        return [
            {
                "id": "writing_001",
                "title": "The Evolution of Consciousness",
                "content": """
                Consciousness has evolved through several stages. First came basic awareness,
                then self-reflection, and finally meta-consciousness. Each stage builds upon
                the previous one, creating a foundation for more complex thought patterns.
                """,
                "tags": ["philosophy", "consciousness", "evolution"],
            },
            {
                "id": "writing_002",
                "title": "Neural Networks and Thought",
                "content": """
                Neural networks in the brain create complex patterns of thought. These networks
                are not static but evolve over time, much like consciousness itself. The connections
                between neurons mirror the connections between ideas in our thinking.
                """,
                "tags": ["neuroscience", "networks", "thought"],
            },
            {
                "id": "writing_003",
                "title": "Creative Writing Techniques",
                "content": """
                Creative writing requires building connections between seemingly unrelated ideas.
                The best stories emerge when concepts from different domains collide and create
                new meanings. This process mirrors how consciousness evolves through unexpected
                associations.
                """,
                "tags": ["writing", "creativity", "technique"],
            },
            {
                "id": "writing_004",
                "title": "Philosophy of Mind",
                "content": """
                The philosophy of mind explores how consciousness arises from physical processes.
                Neural networks provide the substrate, but consciousness adds something more -
                the ability to reflect upon itself, creating meta-consciousness.
                """,
                "tags": ["philosophy", "mind", "consciousness"],
            },
        ]

    def test_document_storage_integration(self, sample_writing_documents):
        """Test that writing documents can be stored successfully."""
        # This test will fail until document storage is implemented
        from src.models.documents import DocumentStorage

        storage = DocumentStorage()

        # Store all sample documents
        for doc in sample_writing_documents:
            result = storage.store_document(doc)
            assert result is True, f"Failed to store document {doc['id']}"

        # Verify documents were stored
        stored_docs = storage.get_all_documents()
        assert len(stored_docs) >= len(sample_writing_documents)

        # Verify specific documents
        for doc in sample_writing_documents:
            stored = storage.get_document(doc["id"])
            assert stored is not None
            assert stored["title"] == doc["title"]
            assert stored["content"] == doc["content"]

    def test_semantic_relationship_extraction(self, sample_writing_documents):
        """Test that semantic relationships are extracted from writing documents."""
        from src.models.relationships import RelationshipStorage
        from src.services.semantic_analyzer import SemanticAnalyzer

        analyzer = SemanticAnalyzer()
        storage = RelationshipStorage()

        # Extract relationships
        relationships = analyzer.extract_relationships(sample_writing_documents)

        # Should find relationships between documents
        assert (
            len(relationships) > 0
        ), "No relationships found between writing documents"

        # Store relationships
        result = storage.store_relationships(relationships)
        assert result is True

        # Verify relationships are stored and retrievable
        for doc in sample_writing_documents:
            doc_relationships = storage.get_relationships_for_document(doc["id"])
            assert isinstance(doc_relationships, list)

    def test_relationship_graph_formation(self, sample_writing_documents):
        """Test that a coherent relationship graph forms from writing documents."""
        from src.models.relationships import RelationshipStorage
        from src.services.semantic_analyzer import SemanticAnalyzer

        analyzer = SemanticAnalyzer()
        storage = RelationshipStorage()

        # Extract and store relationships
        relationships = analyzer.extract_relationships(sample_writing_documents)
        storage.store_relationships(relationships)

        # Build relationship graph
        graph = storage.build_relationship_graph()

        # Graph should have nodes for all documents
        assert len(graph.nodes) >= len(sample_writing_documents)

        # Graph should have edges representing relationships
        assert len(graph.edges) >= len(relationships)

        # Verify graph connectivity
        # At least some documents should be connected
        connected_components = graph.get_connected_components()
        assert len(connected_components) < len(
            sample_writing_documents
        ), "Documents should form connected components"

    def test_writer_query_workflow(self, sample_writing_documents):
        """Test the complete query workflow for writers."""
        from src.api.search import SearchAPI
        from src.models.relationships import RelationshipStorage
        from src.services.semantic_analyzer import SemanticAnalyzer

        # Setup data
        analyzer = SemanticAnalyzer()
        storage = RelationshipStorage()
        api = SearchAPI()

        relationships = analyzer.extract_relationships(sample_writing_documents)
        storage.store_relationships(relationships)

        # Test relationship query
        query_result = api.get_relationships_for_document("writing_001")

        assert "relationships" in query_result
        assert isinstance(query_result["relationships"], list)

        # Should find relationships with other consciousness-related documents
        consciousness_docs = [
            "writing_001",
            "writing_004",
        ]  # Both mention consciousness
        found_relationships = [
            r
            for r in query_result["relationships"]
            if r["target_id"] in consciousness_docs
        ]
        assert (
            len(found_relationships) > 0
        ), "Should find consciousness-related connections"

    def test_concept_clustering(self, sample_writing_documents):
        """Test that related concepts are properly clustered."""
        from src.services.semantic_analyzer import SemanticAnalyzer

        analyzer = SemanticAnalyzer()

        # Extract concepts from documents
        concepts = analyzer.extract_concepts(sample_writing_documents)

        # Should identify key concepts
        concept_names = [c["name"] for c in concepts]
        assert "consciousness" in concept_names
        assert "networks" in concept_names or "neural networks" in concept_names

        # Concepts should be clustered by similarity
        clusters = analyzer.cluster_concepts(concepts)

        # Should have multiple clusters
        assert len(clusters) > 1

        # Consciousness-related concepts should be in same cluster
        consciousness_cluster = None
        for cluster in clusters:
            if any(c["name"] == "consciousness" for c in cluster):
                consciousness_cluster = cluster
                break

        assert consciousness_cluster is not None
        assert (
            len(consciousness_cluster) > 1
        ), "Consciousness should connect to other concepts"

    def test_relationship_strength_calculation(self, sample_writing_documents):
        """Test that relationship strengths are calculated appropriately."""
        from src.services.semantic_analyzer import SemanticAnalyzer

        analyzer = SemanticAnalyzer()

        relationships = analyzer.extract_relationships(sample_writing_documents)

        # All relationships should have valid confidence scores
        for rel in relationships:
            assert 0.0 <= rel.confidence <= 1.0

        # Strong relationships should exist between closely related documents
        strong_relationships = [r for r in relationships if r.confidence > 0.7]

        # Should have at least some strong relationships
        assert len(strong_relationships) > 0, "Should find strongly related documents"

    def test_bidirectional_relationships(self, sample_writing_documents):
        """Test that relationships are stored bidirectionally."""
        from src.models.relationships import RelationshipStorage
        from src.services.semantic_analyzer import SemanticAnalyzer

        analyzer = SemanticAnalyzer()
        storage = RelationshipStorage()

        relationships = analyzer.extract_relationships(sample_writing_documents)
        storage.store_relationships(relationships)

        # Pick a relationship and verify it's bidirectional
        if relationships:
            rel = relationships[0]

            # Get relationships for source
            source_rels = storage.get_relationships_for_document(rel.source_id)
            source_to_target = [r for r in source_rels if r.target_id == rel.target_id]

            # Get relationships for target
            target_rels = storage.get_relationships_for_document(rel.target_id)
            target_to_source = [r for r in target_rels if r.target_id == rel.source_id]

            # Should have bidirectional relationships
            assert len(source_to_target) > 0, "Source should relate to target"
            assert len(target_to_source) > 0, "Target should relate back to source"

    def test_graph_visualization_data(self, sample_writing_documents):
        """Test that graph data is properly formatted for visualization."""
        from src.models.relationships import RelationshipStorage
        from src.services.semantic_analyzer import SemanticAnalyzer

        analyzer = SemanticAnalyzer()
        storage = RelationshipStorage()

        relationships = analyzer.extract_relationships(sample_writing_documents)
        storage.store_relationships(relationships)

        # Get visualization data
        viz_data = storage.get_visualization_data()

        # Should have nodes and edges
        assert "nodes" in viz_data
        assert "edges" in viz_data

        assert len(viz_data["nodes"]) >= len(sample_writing_documents)
        assert len(viz_data["edges"]) >= len(relationships)

        # Nodes should have required fields
        for node in viz_data["nodes"]:
            assert "id" in node
            assert "label" in node
            assert "group" in node

        # Edges should have required fields
        for edge in viz_data["edges"]:
            assert "from" in edge
            assert "to" in edge
            assert "label" in edge
            assert "strength" in edge

    def test_performance_under_load(self, sample_writing_documents):
        """Test that the system performs adequately with writing documents."""
        import time

        from models.relationships import RelationshipStorage
        from services.semantic_analyzer import SemanticAnalyzer

        analyzer = SemanticAnalyzer()
        storage = RelationshipStorage()

        # Measure relationship extraction time
        start_time = time.time()
        relationships = analyzer.extract_relationships(sample_writing_documents)
        extraction_time = time.time() - start_time

        # Should complete within reasonable time (adjust threshold as needed)
        assert extraction_time < 5.0, f"Extraction took too long: {extraction_time}s"

        # Measure storage time
        start_time = time.time()
        storage.store_relationships(relationships)
        storage_time = time.time() - start_time

        assert storage_time < 1.0, f"Storage took too long: {storage_time}s"

        # Measure query time
        start_time = time.time()
        for doc in sample_writing_documents:
            storage.get_relationships_for_document(doc["id"])
        query_time = time.time() - start_time

        avg_query_time = query_time / len(sample_writing_documents)
        assert avg_query_time < 0.1, f"Queries too slow: {avg_query_time}s average"
