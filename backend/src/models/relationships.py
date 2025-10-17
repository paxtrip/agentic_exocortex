"""
Relationship graph storage model for User Story 3 (Writer workflow).

This module provides storage and retrieval for semantic relationships between documents.
It maintains a graph structure where documents are nodes and semantic relationships
are edges, enabling writers to explore idea connections across their work.

The storage supports bidirectional relationships and provides methods for
graph traversal, visualization data generation, and relationship queries.
"""

import json
import logging
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Import our contract types
from .relationships_base import SemanticRelationship

logger = logging.getLogger(__name__)


class RelationshipGraph:
    """
    In-memory graph representation of document relationships.

    This class provides graph algorithms and visualization data generation.
    """

    def __init__(self):
        """Initialize empty relationship graph."""
        self.nodes: Dict[str, Dict[str, Any]] = {}  # document_id -> node data
        self.edges: List[Dict[str, Any]] = []  # list of edge dictionaries

    def add_node(self, document_id: str, node_data: Dict[str, Any]):
        """Add a document node to the graph."""
        self.nodes[document_id] = node_data

    def add_edge(self, relationship: SemanticRelationship):
        """Add a relationship edge to the graph."""
        edge = {
            "from": relationship.source_id,
            "to": relationship.target_id,
            "relationship_type": relationship.relationship_type,
            "confidence": relationship.confidence,
            "context": relationship.context,
            "label": f"{relationship.relationship_type} ({relationship.confidence:.2f})",
        }
        self.edges.append(edge)

    def get_connected_components(self) -> List[List[str]]:
        """
        Find connected components in the relationship graph.

        Returns:
            List of document ID lists, each representing a connected component
        """
        # Simple DFS-based connected components
        visited = set()
        components = []

        def dfs(node_id: str, component: List[str]):
            """Depth-first search to find connected nodes."""
            visited.add(node_id)
            component.append(node_id)

            # Find all neighbors
            for edge in self.edges:
                neighbor = None
                if edge["from"] == node_id:
                    neighbor = edge["to"]
                elif edge["to"] == node_id:
                    neighbor = edge["from"]

                if neighbor and neighbor not in visited:
                    dfs(neighbor, component)

        for node_id in self.nodes:
            if node_id not in visited:
                component = []
                dfs(node_id, component)
                if len(component) > 1:  # Only include components with relationships
                    components.append(component)

        return components


class RelationshipStorage:
    """
    SQLite-based storage for semantic relationships.

    This class handles persistence of relationship data and provides
    query methods for retrieving relationships and graph data.
    """

    def __init__(self, db_path: str = "relationships.db"):
        """
        Initialize relationship storage.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS relationships (
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    context TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (source_id, target_id, relationship_type)
                )
            """
            )

            # Index for faster queries
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_relationships_source
                ON relationships(source_id)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_relationships_target
                ON relationships(target_id)
            """
            )

            conn.commit()

    def store_relationships(self, relationships: List[SemanticRelationship]) -> bool:
        """
        Store semantic relationships in database.

        Args:
            relationships: List of relationships to store

        Returns:
            True if all relationships stored successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                for rel in relationships:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO relationships
                        (source_id, target_id, relationship_type, confidence, context)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (
                            rel.source_id,
                            rel.target_id,
                            rel.relationship_type,
                            rel.confidence,
                            rel.context,
                        ),
                    )

                    # Store bidirectional relationship
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO relationships
                        (source_id, target_id, relationship_type, confidence, context)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (
                            rel.target_id,  # Swap source and target
                            rel.source_id,
                            rel.relationship_type,
                            rel.confidence,
                            rel.context,
                        ),
                    )

                conn.commit()
                logger.info(f"Stored {len(relationships)} relationships")
                return True

        except Exception as e:
            logger.error(f"Failed to store relationships: {e}")
            return False

    def get_relationships_for_document(
        self, document_id: str
    ) -> List[SemanticRelationship]:
        """
        Retrieve relationships for a specific document.

        Args:
            document_id: Document ID to get relationships for

        Returns:
            List of relationships involving this document
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT source_id, target_id, relationship_type, confidence, context
                    FROM relationships
                    WHERE source_id = ? OR target_id = ?
                    ORDER BY confidence DESC
                """,
                    (document_id, document_id),
                )

                relationships = []
                for row in cursor.fetchall():
                    relationships.append(
                        SemanticRelationship(
                            source_id=row[0],
                            target_id=row[1],
                            relationship_type=row[2],
                            confidence=row[3],
                            context=row[4],
                        )
                    )

                return relationships

        except Exception as e:
            logger.error(f"Failed to get relationships for document {document_id}: {e}")
            return []

    def build_relationship_graph(self) -> RelationshipGraph:
        """
        Build a relationship graph from stored data.

        Returns:
            RelationshipGraph object with nodes and edges
        """
        graph = RelationshipGraph()

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get all relationships
                cursor = conn.execute(
                    """
                    SELECT DISTINCT source_id, target_id, relationship_type, confidence, context
                    FROM relationships
                """
                )

                # Collect all document IDs
                all_docs = set()
                relationships = []

                for row in cursor.fetchall():
                    rel = SemanticRelationship(
                        source_id=row[0],
                        target_id=row[1],
                        relationship_type=row[2],
                        confidence=row[3],
                        context=row[4],
                    )
                    relationships.append(rel)
                    all_docs.add(row[0])
                    all_docs.add(row[1])

                # Add nodes (we'll need document metadata from elsewhere)
                for doc_id in all_docs:
                    graph.add_node(
                        doc_id,
                        {
                            "id": doc_id,
                            "label": doc_id,  # Could be enhanced with title
                            "group": "document",
                        },
                    )

                # Add edges
                for rel in relationships:
                    graph.add_edge(rel)

                logger.info(
                    f"Built graph with {len(all_docs)} nodes and {len(relationships)} edges"
                )
                return graph

        except Exception as e:
            logger.error(f"Failed to build relationship graph: {e}")
            return graph

    def get_visualization_data(self) -> Dict[str, Any]:
        """
        Get data formatted for graph visualization.

        Returns:
            Dictionary with 'nodes' and 'edges' keys for visualization
        """
        graph = self.build_relationship_graph()

        # Format nodes for visualization
        nodes = []
        for node_id, node_data in graph.nodes.items():
            nodes.append(
                {
                    "id": node_id,
                    "label": node_data.get("label", node_id),
                    "group": node_data.get("group", "document"),
                }
            )

        # Format edges for visualization
        edges = []
        for edge in graph.edges:
            edges.append(
                {
                    "from": edge["from"],
                    "to": edge["to"],
                    "label": edge["label"],
                    "strength": edge["confidence"],
                    "type": edge["relationship_type"],
                }
            )

        return {"nodes": nodes, "edges": edges}

    def get_relationship_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored relationships.

        Returns:
            Dictionary with relationship statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Count by relationship type
                cursor = conn.execute(
                    """
                    SELECT relationship_type, COUNT(*) as count,
                           AVG(confidence) as avg_confidence
                    FROM relationships
                    GROUP BY relationship_type
                """
                )

                stats = {
                    "total_relationships": 0,
                    "relationship_types": {},
                    "avg_confidence": 0.0,
                }

                total_count = 0
                total_confidence = 0.0

                for row in cursor.fetchall():
                    rel_type, count, avg_conf = row
                    stats["relationship_types"][rel_type] = {
                        "count": count,
                        "avg_confidence": avg_conf,
                    }
                    total_count += count
                    total_confidence += avg_conf * count

                stats["total_relationships"] = total_count
                if total_count > 0:
                    stats["avg_confidence"] = total_confidence / total_count

                return stats

        except Exception as e:
            logger.error(f"Failed to get relationship stats: {e}")
            return {}

    def clear_all_relationships(self):
        """Clear all stored relationships (for testing/cleanup)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM relationships")
                conn.commit()
                logger.info("Cleared all relationships")
        except Exception as e:
            logger.error(f"Failed to clear relationships: {e}")
