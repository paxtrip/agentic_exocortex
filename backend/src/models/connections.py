"""
Connection models and storage for document relationships.

This module provides:
- Data models for document connections
- Storage and retrieval of connection data
- Multi-hop connection traversal algorithms

Uses SQLite for persistence with FTS5 for efficient querying.
"""

import asyncio
import json
import logging
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .connections_base import Connection, ConnectionQuery, ConnectionResult

logger = logging.getLogger(__name__)


class ConnectionStore:
    """
    Storage layer for document connections.

    Provides efficient storage and retrieval of document relationships,
    with support for multi-hop traversal and strength-based filtering.
    """

    def __init__(self, db_path: str = "data/connections.db"):
        """
        Initialize connection store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS connections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_doc_id TEXT NOT NULL,
                    target_doc_id TEXT NOT NULL,
                    connection_type TEXT NOT NULL,
                    strength REAL NOT NULL,
                    context TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(source_doc_id, target_doc_id, connection_type)
                )
            """
            )

            # Create indexes for efficient querying
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_source_doc ON connections(source_doc_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_target_doc ON connections(target_doc_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_connection_type ON connections(connection_type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_strength ON connections(strength)"
            )

            # FTS5 virtual table for full-text search on context
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS connections_fts USING fts5(
                    context, content=connections, content_rowid=id
                )
            """
            )

            # Triggers to keep FTS table in sync
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS connections_fts_insert AFTER INSERT ON connections
                BEGIN
                    INSERT INTO connections_fts(rowid, context) VALUES (new.id, new.context);
                END
            """
            )

            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS connections_fts_delete AFTER DELETE ON connections
                BEGIN
                    DELETE FROM connections_fts WHERE rowid = old.id;
                END
            """
            )

            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS connections_fts_update AFTER UPDATE ON connections
                BEGIN
                    UPDATE connections_fts SET context = new.context WHERE rowid = new.id;
                END
            """
            )

    async def store_connections(self, connections: List[Connection]) -> None:
        """
        Store multiple connections in the database.

        Args:
            connections: List of Connection objects to store
        """

        def _store():
            with sqlite3.connect(self.db_path) as conn:
                conn.executemany(
                    """
                    INSERT OR REPLACE INTO connections
                    (source_doc_id, target_doc_id, connection_type, strength, context, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    [
                        (
                            conn.source_doc_id,
                            conn.target_doc_id,
                            conn.connection_type,
                            conn.strength,
                            conn.context,
                            conn.created_at,
                        )
                        for conn in connections
                    ],
                )
                conn.commit()

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self._executor, _store)

        logger.info(f"Stored {len(connections)} connections")

    async def get_connections(self, query: ConnectionQuery) -> ConnectionResult:
        """
        Retrieve connections matching the query.

        Supports multi-hop traversal and strength filtering.

        Args:
            query: ConnectionQuery specifying search parameters

        Returns:
            ConnectionResult with matching connections and metadata
        """

        def _query():
            with sqlite3.connect(self.db_path) as conn:
                # Build base query
                sql = """
                    SELECT id, source_doc_id, target_doc_id, connection_type, strength, context, created_at
                    FROM connections
                    WHERE source_doc_id = ?
                """
                params = [query.doc_id]

                # Add strength filter if specified
                if query.min_strength > 0:
                    sql += " AND strength >= ?"
                    params.append(query.min_strength)

                sql += " ORDER BY strength DESC"

                cursor = conn.execute(sql, params)
                direct_connections = []
                for row in cursor:
                    direct_connections.append(
                        Connection(
                            source_doc_id=row[1],
                            target_doc_id=row[2],
                            connection_type=row[3],
                            strength=row[4],
                            context=row[5] or "",
                            created_at=row[6],
                        )
                    )

                # If multi-hop requested, find indirect connections
                if query.max_hops > 1:
                    indirect_connections = self._find_multi_hop_connections(
                        conn, query.doc_id, query.max_hops, query.min_strength
                    )
                    all_connections = direct_connections + indirect_connections
                else:
                    all_connections = direct_connections

                return ConnectionResult(
                    connections=all_connections,
                    total_found=len(all_connections),
                    trace_id=f"trace_{datetime.utcnow().timestamp()}",
                )

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(self._executor, _query)
        return result

    def _find_multi_hop_connections(
        self,
        conn: sqlite3.Connection,
        start_doc: str,
        max_hops: int,
        min_strength: float,
    ) -> List[Connection]:
        """
        Find multi-hop connections using breadth-first search.

        Args:
            conn: Database connection
            start_doc: Starting document ID
            max_hops: Maximum number of hops to traverse
            min_strength: Minimum connection strength

        Returns:
            List of indirect connections
        """
        visited: Set[str] = {start_doc}
        current_level: Set[str] = {start_doc}
        indirect_connections: List[Connection] = []

        for hop in range(1, max_hops):
            next_level: Set[str] = set()

            for current_doc in current_level:
                # Find documents connected to current document
                cursor = conn.execute(
                    """
                    SELECT DISTINCT target_doc_id
                    FROM connections
                    WHERE source_doc_id = ? AND strength >= ?
                """,
                    (current_doc, min_strength),
                )

                for row in cursor:
                    target_doc = row[0]
                    if target_doc not in visited:
                        next_level.add(target_doc)

                        # Find the actual connection path
                        path_cursor = conn.execute(
                            """
                            SELECT source_doc_id, target_doc_id, connection_type, strength, context, created_at
                            FROM connections
                            WHERE source_doc_id = ? AND target_doc_id = ? AND strength >= ?
                            ORDER BY strength DESC
                            LIMIT 1
                        """,
                            (current_doc, target_doc, min_strength),
                        )

                        for path_row in path_cursor:
                            indirect_connections.append(
                                Connection(
                                    source_doc_id=path_row[0],
                                    target_doc_id=path_row[1],
                                    connection_type=path_row[2],
                                    strength=path_row[3]
                                    * (0.8**hop),  # Reduce strength for each hop
                                    context=path_row[4] or "",
                                    created_at=path_row[5],
                                )
                            )

            # Move to next level
            visited.update(next_level)
            current_level = next_level

            if not current_level:
                break  # No more documents to explore

        return indirect_connections

    async def search_connections_by_context(
        self, search_term: str, min_strength: float = 0.0
    ) -> List[Connection]:
        """
        Search connections by context content using full-text search.

        Args:
            search_term: Term to search for in connection contexts
            min_strength: Minimum connection strength

        Returns:
            List of connections matching the search
        """

        def _search():
            with sqlite3.connect(self.db_path) as conn:
                # Use FTS5 to find matching contexts
                fts_cursor = conn.execute(
                    """
                    SELECT rowid FROM connections_fts
                    WHERE connections_fts MATCH ?
                """,
                    (search_term,),
                )

                matching_ids = [row[0] for row in fts_cursor]

                if not matching_ids:
                    return []

                # Get the actual connection data
                placeholders = ",".join("?" * len(matching_ids))
                cursor = conn.execute(
                    f"""
                    SELECT source_doc_id, target_doc_id, connection_type, strength, context, created_at
                    FROM connections
                    WHERE id IN ({placeholders}) AND strength >= ?
                """,
                    matching_ids + [min_strength],
                )

                connections = []
                for row in cursor:
                    connections.append(
                        Connection(
                            source_doc_id=row[0],
                            target_doc_id=row[1],
                            connection_type=row[2],
                            strength=row[3],
                            context=row[4] or "",
                            created_at=row[5],
                        )
                    )

                return connections

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(self._executor, _search)
        return result

    async def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored connections.

        Returns:
            Dictionary with connection statistics
        """

        def _stats():
            with sqlite3.connect(self.db_path) as conn:
                # Count total connections
                cursor = conn.execute("SELECT COUNT(*) FROM connections")
                total_connections = cursor.fetchone()[0]

                # Count by connection type
                cursor = conn.execute(
                    """
                    SELECT connection_type, COUNT(*)
                    FROM connections
                    GROUP BY connection_type
                """
                )
                type_counts = dict(cursor.fetchall())

                # Average strength by type
                cursor = conn.execute(
                    """
                    SELECT connection_type, AVG(strength), MIN(strength), MAX(strength)
                    FROM connections
                    GROUP BY connection_type
                """
                )
                type_stats = {}
                for row in cursor:
                    type_stats[row[0]] = {
                        "avg_strength": row[1],
                        "min_strength": row[2],
                        "max_strength": row[3],
                    }

                # Count unique documents
                cursor = conn.execute(
                    """
                    SELECT COUNT(DISTINCT source_doc_id) + COUNT(DISTINCT target_doc_id)
                    FROM connections
                """
                )
                unique_docs = cursor.fetchone()[0]

                return {
                    "total_connections": total_connections,
                    "connections_by_type": type_counts,
                    "type_statistics": type_stats,
                    "unique_documents": unique_docs,
                }

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(self._executor, _stats)
        return result

    async def clear_all_connections(self) -> None:
        """Clear all stored connections (for testing)."""

        def _clear():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM connections")
                conn.commit()

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self._executor, _clear)

    def __del__(self):
        """Cleanup executor on destruction."""
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=False)
