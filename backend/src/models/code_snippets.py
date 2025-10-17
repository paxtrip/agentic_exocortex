"""
Code snippet storage and retrieval for User Story 2.

This module handles the storage, indexing, and search of code snippets
extracted from developer notes. It provides efficient search capabilities
with natural language queries and metadata filtering.

Key features:
- In-memory storage with SQLite fallback for persistence
- Natural language search using embeddings
- Tag-based filtering and metadata queries
- Confidence scoring and ranking
"""

import asyncio
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class SearchStrategy(Enum):
    """Search strategies for code snippets."""

    EXACT = "exact"
    FUZZY = "fuzzy"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


@dataclass
class CodeSnippet:
    """Code snippet data model."""

    id: str
    doc_id: str
    language: str
    code: str
    title: str
    tags: List[str]
    confidence: float
    line_start: int
    line_end: int
    created_at: str


@dataclass
class CodeQuery:
    """Query for searching code snippets."""

    query: str = ""
    language: str = ""
    tags: List[str] = None
    limit: int = 10
    strategy: SearchStrategy = SearchStrategy.HYBRID

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class CodeResult:
    """Result of a code search query."""

    snippets: List[Dict[str, Any]]
    total_found: int
    trace_id: str


class CodeSnippetStore:
    """
    Storage and retrieval system for code snippets.

    Provides efficient storage and search capabilities for code snippets
    extracted from developer documentation.
    """

    def __init__(self, db_path: str = ":memory:"):
        """
        Initialize the code snippet store.

        Args:
            db_path: Path to SQLite database file, defaults to in-memory
        """
        self.db_path = db_path
        self._init_db()
        # Ensure tables exist by running init again (idempotent)
        self._ensure_tables_exist()

    def _init_db(self):
        """Initialize the database schema."""
        pass  # Moved to _ensure_tables_exist

    def _ensure_tables_exist(self):
        """Ensure database tables exist."""
        with sqlite3.connect(self.db_path) as conn:
            # Enable WAL mode for better concurrent access
            conn.execute("PRAGMA journal_mode=WAL")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS code_snippets (
                    id TEXT PRIMARY KEY,
                    doc_id TEXT NOT NULL,
                    language TEXT NOT NULL,
                    code TEXT NOT NULL,
                    title TEXT NOT NULL,
                    tags TEXT NOT NULL,  -- JSON array
                    confidence REAL NOT NULL,
                    line_start INTEGER NOT NULL,
                    line_end INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    search_text TEXT NOT NULL  -- For full-text search
                )
            """
            )

            # Create FTS5 virtual table for full-text search
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS code_snippets_fts USING fts5(
                    id, doc_id, language, code, title, tags, search_text,
                    content=code_snippets,
                    content_rowid=rowid
                )
            """
            )

            # Create triggers to keep FTS table in sync
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS code_snippets_fts_insert
                AFTER INSERT ON code_snippets
                BEGIN
                    INSERT INTO code_snippets_fts(rowid, id, doc_id, language, code, title, tags, search_text)
                    VALUES (new.rowid, new.id, new.doc_id, new.language, new.code, new.title, new.tags, new.search_text);
                END
            """
            )

            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS code_snippets_fts_delete
                AFTER DELETE ON code_snippets
                BEGIN
                    DELETE FROM code_snippets_fts WHERE rowid = old.rowid;
                END
            """
            )

            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS code_snippets_fts_update
                AFTER UPDATE ON code_snippets
                BEGIN
                    UPDATE code_snippets_fts SET
                        id = new.id,
                        doc_id = new.doc_id,
                        language = new.language,
                        code = new.code,
                        title = new.title,
                        tags = new.tags,
                        search_text = new.search_text
                    WHERE rowid = new.rowid;
                END
            """
            )

    async def store_snippets(self, snippets: List[Dict[str, Any]]) -> None:
        """
        Store code snippets in the database.

        Args:
            snippets: List of code snippet dictionaries or objects
        """
        self._ensure_tables_exist()
        with sqlite3.connect(self.db_path) as conn:
            for snippet in snippets:
                # Handle both dict and object inputs
                if hasattr(snippet, "__dict__"):
                    # Convert object to dict
                    snippet_dict = {
                        "id": snippet.id,
                        "doc_id": snippet.doc_id,
                        "language": snippet.language,
                        "code": snippet.code,
                        "title": snippet.title,
                        "tags": snippet.tags,
                        "confidence": snippet.confidence,
                        "line_start": snippet.line_start,
                        "line_end": snippet.line_end,
                        "created_at": snippet.created_at,
                    }
                else:
                    snippet_dict = snippet

                # Prepare search text (combine title, code, and tags for search)
                tags_str = " ".join(snippet_dict.get("tags", []))
                search_text = (
                    f"{snippet_dict['title']} {snippet_dict['code']} {tags_str}"
                )

                conn.execute(
                    """
                    INSERT OR REPLACE INTO code_snippets
                    (id, doc_id, language, code, title, tags, confidence, line_start, line_end, created_at, search_text)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        snippet_dict["id"],
                        snippet_dict["doc_id"],
                        snippet_dict["language"],
                        snippet_dict["code"],
                        snippet_dict["title"],
                        json.dumps(snippet_dict.get("tags", [])),
                        snippet_dict["confidence"],
                        snippet_dict["line_start"],
                        snippet_dict["line_end"],
                        snippet_dict["created_at"],
                        search_text,
                    ),
                )

    async def search_snippets(self, query: CodeQuery) -> CodeResult:
        """
        Search for code snippets based on the query.

        Args:
            query: Search query parameters

        Returns:
            CodeResult with matching snippets
        """
        trace_id = self._generate_trace_id()

        # Build the search query
        sql_query, params = self._build_search_query(query)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(sql_query, params)

            rows = cursor.fetchall()
            total_found = len(rows)

            # Convert rows to dictionaries and limit results
            snippets = []
            for row in rows[: query.limit]:
                snippet = dict(row)
                # Parse tags from JSON
                snippet["tags"] = json.loads(snippet["tags"])
                snippets.append(snippet)

        return CodeResult(snippets=snippets, total_found=total_found, trace_id=trace_id)

    def _build_search_query(self, query: CodeQuery) -> Tuple[str, List[Any]]:
        """Build the SQL query for searching snippets."""
        conditions = []
        params = []

        # Language filter
        if query.language:
            conditions.append("language = ?")
            params.append(query.language)

        # Tag filter
        if query.tags:
            tag_conditions = []
            for tag in query.tags:
                tag_conditions.append("tags LIKE ?")
                params.append(f"%{tag}%")
            if tag_conditions:
                conditions.append(f"({' OR '.join(tag_conditions)})")

        # Text search
        if query.query.strip():
            if query.strategy in [SearchStrategy.EXACT, SearchStrategy.FUZZY]:
                # Use FTS for text search
                fts_conditions = ["code_snippets_fts.search_text MATCH ?"]
                fts_params = [f'"{query.query}"*']  # FTS5 prefix search

                # Combine with other conditions
                if conditions:
                    sql = f"""
                        SELECT cs.* FROM code_snippets cs
                        JOIN code_snippets_fts fts ON cs.rowid = fts.rowid
                        WHERE {' AND '.join(conditions)} AND {' AND '.join(fts_conditions)}
                        ORDER BY bm25(code_snippets_fts)  -- FTS ranking
                    """
                    params.extend(fts_params)
                else:
                    sql = f"""
                        SELECT cs.* FROM code_snippets cs
                        JOIN code_snippets_fts fts ON cs.rowid = fts.rowid
                        WHERE {' AND '.join(fts_conditions)}
                        ORDER BY bm25(code_snippets_fts)
                    """
                    params = fts_params
            else:
                # Simple LIKE search for semantic/hybrid
                conditions.append("(title LIKE ? OR code LIKE ? OR search_text LIKE ?)")
                search_param = f"%{query.query}%"
                params.extend([search_param, search_param, search_param])

                sql = f"""
                    SELECT * FROM code_snippets
                    WHERE {' AND '.join(conditions)}
                    ORDER BY confidence DESC, created_at DESC
                """
        else:
            # No text query, just filters
            if conditions:
                sql = f"""
                    SELECT * FROM code_snippets
                    WHERE {' AND '.join(conditions)}
                    ORDER BY confidence DESC, created_at DESC
                """
            else:
                sql = """
                    SELECT * FROM code_snippets
                    ORDER BY confidence DESC, created_at DESC
                """

        return sql, params

    async def get_snippet_by_id(self, snippet_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific code snippet by ID.

        Args:
            snippet_id: Unique identifier of the snippet

        Returns:
            Snippet data or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM code_snippets WHERE id = ?", (snippet_id,)
            )
            row = cursor.fetchone()

            if row:
                snippet = dict(row)
                snippet["tags"] = json.loads(snippet["tags"])
                return snippet

        return None

    async def get_snippets_by_doc(self, doc_id: str) -> List[Dict[str, Any]]:
        """
        Get all code snippets from a specific document.

        Args:
            doc_id: Document identifier

        Returns:
            List of snippets from the document
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM code_snippets WHERE doc_id = ? ORDER BY line_start",
                (doc_id,),
            )

            snippets = []
            for row in cursor:
                snippet = dict(row)
                snippet["tags"] = json.loads(snippet["tags"])
                snippets.append(snippet)

        return snippets

    async def clear_all_snippets(self) -> None:
        """Clear all stored code snippets (for testing)."""
        with sqlite3.connect(self.db_path) as conn:
            # Create table if it doesn't exist
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS code_snippets (
                    id TEXT PRIMARY KEY,
                    doc_id TEXT NOT NULL,
                    language TEXT NOT NULL,
                    code TEXT NOT NULL,
                    title TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    line_start INTEGER NOT NULL,
                    line_end INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    search_text TEXT NOT NULL
                )
            """
            )
            conn.execute("DELETE FROM code_snippets")

    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about stored code snippets."""
        with sqlite3.connect(self.db_path) as conn:
            # Total count
            cursor = conn.execute("SELECT COUNT(*) FROM code_snippets")
            total_count = cursor.fetchone()[0]

            # Language distribution
            cursor = conn.execute(
                """
                SELECT language, COUNT(*) as count
                FROM code_snippets
                GROUP BY language
                ORDER BY count DESC
            """
            )
            languages = {row[0]: row[1] for row in cursor.fetchall()}

            # Average confidence
            cursor = conn.execute("SELECT AVG(confidence) FROM code_snippets")
            avg_confidence = cursor.fetchone()[0] or 0.0

        return {
            "total_snippets": total_count,
            "languages": languages,
            "average_confidence": round(avg_confidence, 3),
        }

    @staticmethod
    def _generate_trace_id() -> str:
        """Generate a unique trace ID for the search operation."""
        import uuid

        return f"code_search_{uuid.uuid4().hex[:8]}"


# Convenience functions for the API
async def store_code_snippets(snippets: List[Dict[str, Any]]) -> None:
    """
    Store code snippets using the default store.

    This is the main API function for storing code snippets.
    """
    store = CodeSnippetStore()
    await store.store_snippets(snippets)


async def search_code_snippets(query: CodeQuery) -> CodeResult:
    """
    Search for code snippets using the default store.

    This is the main API function for searching code snippets.
    """
    store = CodeSnippetStore()
    return await store.search_snippets(query)
