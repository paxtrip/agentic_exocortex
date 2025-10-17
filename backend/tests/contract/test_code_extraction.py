"""
Contract tests for code snippet extraction in User Story 2.

Tests the contract between components for extracting and formatting code snippets
from developer notes. These tests ensure the code detection and storage APIs work
correctly before implementing the full code search functionality.

Following TDD principle: write tests first, ensure they fail, then implement.
"""

from typing import Any, Dict, List

import pytest
from pydantic import BaseModel, Field


class CodeSnippet(BaseModel):
    """Extracted code snippet with metadata."""

    id: str
    doc_id: str
    language: str  # 'python', 'javascript', 'sql', etc.
    code: str  # The actual code content
    title: str  # Optional title or description
    tags: List[str] = []  # Programming concepts, frameworks, etc.
    confidence: float = Field(ge=0.0, le=1.0)  # Detection confidence
    line_start: int  # Starting line number in original document
    line_end: int  # Ending line number in original document
    created_at: str  # ISO timestamp


class CodeQuery(BaseModel):
    """Query for finding code snippets."""

    query: str  # Search term or natural language description
    language: str = ""  # Filter by programming language
    tags: List[str] = []  # Filter by tags
    limit: int = 10


class CodeResult(BaseModel):
    """Result of code search query."""

    snippets: List[CodeSnippet]
    total_found: int
    trace_id: str


class TestCodeExtractionContract:
    """
    Contract tests for code extraction functionality.

    These tests define the expected behavior of code processing components
    and will fail until the implementation is complete.
    """

    def test_code_snippet_model_validation(self):
        """Test that CodeSnippet model validates correctly."""
        # Valid snippet
        snippet = CodeSnippet(
            id="snippet_001",
            doc_id="doc_001",
            language="python",
            code="def hello():\n    return 'world'",
            title="Simple greeting function",
            tags=["function", "string"],
            confidence=0.95,
            line_start=10,
            line_end=12,
            created_at="2024-01-01T12:00:00Z",
        )
        assert snippet.language == "python"
        assert snippet.confidence <= 1.0
        assert snippet.line_start < snippet.line_end

        # Invalid confidence
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CodeSnippet(
                id="snippet_001",
                doc_id="doc_001",
                language="python",
                code="test",
                title="test",
                confidence=1.5,  # Invalid: > 1.0
                line_start=1,
                line_end=2,
                created_at="2024-01-01T12:00:00Z",
            )

    def test_code_query_model(self):
        """Test CodeQuery model validation."""
        query = CodeQuery(
            query="sorting algorithm",
            language="python",
            tags=["algorithm", "data-structure"],
            limit=5,
        )
        assert query.query == "sorting algorithm"
        assert query.language == "python"
        assert "algorithm" in query.tags
        assert query.limit == 5

    def test_code_result_model(self):
        """Test CodeResult model structure."""
        result = CodeResult(snippets=[], total_found=0, trace_id="trace_123")
        assert len(result.snippets) == 0
        assert result.total_found == 0
        assert result.trace_id == "trace_123"

    @pytest.mark.asyncio
    async def test_extract_code_from_markdown(self):
        """
        Test contract for extracting code from markdown text.

        This test will fail until backend/src/utils/code_processor.py
        implements the code detection logic.
        """
        from backend.src.utils.code_processor import extract_code_snippets

        markdown_text = """
        # Python Examples

        Here's a simple function:

        ```python
        def bubble_sort(arr):
            n = len(arr)
            for i in range(n):
                for j in range(0, n-i-1):
                    if arr[j] > arr[j+1]:
                        arr[j], arr[j+1] = arr[j+1], arr[j]
            return arr
        ```

        And here's some SQL:

        ```sql
        SELECT * FROM users
        WHERE active = 1
        ORDER BY created_at DESC;
        ```

        This is not code, just regular text.
        """

        snippets = await extract_code_snippets("doc_001", markdown_text)

        # Should find 2 code snippets
        assert len(snippets) == 2

        # Check first snippet (Python)
        python_snippet = next(s for s in snippets if s["language"] == "python")
        assert "bubble_sort" in python_snippet["code"]
        assert python_snippet["line_start"] >= 0
        assert python_snippet["line_end"] > python_snippet["line_start"]
        assert python_snippet["confidence"] > 0.5  # Should be confident detection

        # Check second snippet (SQL)
        sql_snippet = next(s for s in snippets if s["language"] == "sql")
        assert "SELECT" in sql_snippet["code"]
        assert sql_snippet["language"] == "sql"

    @pytest.mark.asyncio
    async def test_detect_code_language(self):
        """
        Test contract for automatic language detection.
        """
        from backend.src.utils.code_processor import detect_language

        # Python code
        python_code = """
        import os
        def get_files(path):
            return [f for f in os.listdir(path) if f.endswith('.py')]
        """
        assert await detect_language(python_code) == "python"

        # JavaScript code
        js_code = """
        function fetchData(url) {
            return fetch(url)
                .then(response => response.json())
                .catch(error => console.error(error));
        }
        """
        assert await detect_language(js_code) == "javascript"

        # SQL code
        sql_code = "SELECT id, name FROM users WHERE status = 'active';"
        assert await detect_language(sql_code) == "sql"

    @pytest.mark.asyncio
    async def test_store_and_retrieve_code_snippets(self):
        """
        Test contract for storing and retrieving code snippets.

        This test will fail until backend/src/models/code_snippets.py
        implements the storage and retrieval logic.
        """
        from backend.src.models.code_snippets import CodeSnippetStore

        store = CodeSnippetStore()

        # Clear any existing snippets first
        await store.clear_all_snippets()

        # Store some test snippets
        snippets = [
            CodeSnippet(
                id="snippet_001",
                doc_id="doc_001",
                language="python",
                code="def quicksort(arr): return sorted(arr)",
                title="Quick sort implementation",
                tags=["algorithm", "sorting"],
                confidence=0.9,
                line_start=5,
                line_end=7,
                created_at="2024-01-01T12:00:00Z",
            ),
            CodeSnippet(
                id="snippet_002",
                doc_id="doc_002",
                language="javascript",
                code="const sum = (a, b) => a + b;",
                title="Arrow function sum",
                tags=["function", "es6"],
                confidence=0.95,
                line_start=10,
                line_end=10,
                created_at="2024-01-02T12:00:00Z",
            ),
        ]

        # Store snippets
        await store.store_snippets(snippets)

        # Retrieve snippets by language
        query = CodeQuery(query="", language="python", limit=10)
        result = await store.search_snippets(query)

        assert result.total_found == 1
        assert len(result.snippets) == 1
        assert result.snippets[0].language == "python"
        assert "quicksort" in result.snippets[0].code

    @pytest.mark.asyncio
    async def test_search_code_by_natural_language(self):
        """
        Test contract for searching code using natural language descriptions.
        """
        from backend.src.models.code_snippets import CodeSnippetStore

        store = CodeSnippetStore()

        # Store test snippets with semantic content
        snippets = [
            CodeSnippet(
                id="sort_001",
                doc_id="doc_001",
                language="python",
                code="def merge_sort(arr): ...",
                title="Efficient sorting algorithm",
                tags=["sorting", "algorithm", "divide-conquer"],
                confidence=0.9,
                line_start=1,
                line_end=20,
                created_at="2024-01-01T12:00:00Z",
            ),
            CodeSnippet(
                id="api_001",
                doc_id="doc_002",
                language="javascript",
                code="app.get('/api/data', handler)",
                title="REST API endpoint",
                tags=["api", "rest", "express"],
                confidence=0.85,
                line_start=5,
                line_end=5,
                created_at="2024-01-02T12:00:00Z",
            ),
        ]

        await store.store_snippets(snippets)

        # Search for "sorting algorithm"
        query = CodeQuery(query="sorting algorithm", limit=5)
        result = await store.search_snippets(query)

        # Should find the sorting-related snippet
        assert result.total_found >= 1
        found_languages = {s.language for s in result.snippets}
        assert "python" in found_languages

    @pytest.mark.asyncio
    async def test_code_snippet_tags_filtering(self):
        """
        Test that code snippets can be filtered by tags.
        """
        from backend.src.models.code_snippets import CodeSnippetStore

        store = CodeSnippetStore()

        # Clear existing snippets
        await store.clear_all_snippets()

        snippets = [
            CodeSnippet(
                id="tagged_001",
                doc_id="doc_001",
                language="python",
                code="def func(): pass",
                title="Tagged function",
                tags=["web", "api", "flask"],
                confidence=0.9,
                line_start=1,
                line_end=2,
                created_at="2024-01-01T12:00:00Z",
            ),
            CodeSnippet(
                id="untagged_001",
                doc_id="doc_002",
                language="python",
                code="x = 1",
                title="Untagged code",
                tags=[],
                confidence=0.8,
                line_start=1,
                line_end=1,
                created_at="2024-01-01T12:00:00Z",
            ),
        ]

        await store.store_snippets(snippets)

        # Query with tag filter
        query = CodeQuery(query="", tags=["api"], limit=10)
        result = await store.search_snippets(query)

        # Should only return the tagged snippet
        assert result.total_found == 1
        assert result.snippets[0].id == "tagged_001"
        assert "api" in result.snippets[0].tags
