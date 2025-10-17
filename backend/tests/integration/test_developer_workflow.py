"""
Integration tests for developer workflow in User Story 2.

Tests the end-to-end developer workflow: storing code snippets from documents,
searching for code by natural language, and retrieving relevant examples.

Following TDD principle: write tests first, ensure they fail, then implement.
"""

from typing import Any, Dict, List

import pytest
from pydantic import BaseModel


class Document(BaseModel):
    """Mock document for testing."""

    id: str
    title: str
    content: str
    created_at: str


class TestDeveloperWorkflowIntegration:
    """
    Integration tests for the complete developer workflow.

    These tests will fail until the full implementation is complete,
    testing the integration between code extraction, storage, and search.
    """

    @pytest.mark.asyncio
    async def test_store_code_from_developer_notes(self):
        """
        Test storing code snippets extracted from developer notes.

        This simulates a developer writing notes with code examples
        and having them automatically indexed for later retrieval.
        """
        # Mock developer notes with various code examples
        developer_notes = [
            Document(
                id="doc_001",
                title="Python Data Structures",
                content="""
                # Python Data Structures

                Here's a binary search implementation:

                ```python
                def binary_search(arr, target):
                    left, right = 0, len(arr) - 1
                    while left <= right:
                        mid = (left + right) // 2
                        if arr[mid] == target:
                            return mid
                        elif arr[mid] < target:
                            left = mid + 1
                        else:
                            right = mid - 1
                    return -1
                ```

                And a quicksort:

                ```python
                def quicksort(arr):
                    if len(arr) <= 1:
                        return arr
                    pivot = arr[len(arr) // 2]
                    left = [x for x in arr if x < pivot]
                    middle = [x for x in arr if x == pivot]
                    right = [x for x in arr if x > pivot]
                    return quicksort(left) + middle + quicksort(right)
                ```
                """,
                created_at="2024-01-01T12:00:00Z",
            ),
            Document(
                id="doc_002",
                title="JavaScript Async Patterns",
                content="""
                # JavaScript Async Patterns

                Promise-based API call:

                ```javascript
                async function fetchUserData(userId) {
                    try {
                        const response = await fetch(`/api/users/${userId}`);
                        const data = await response.json();
                        return data;
                    } catch (error) {
                        console.error('Failed to fetch user:', error);
                        throw error;
                    }
                }
                ```

                Using callbacks (old style):

                ```javascript
                function loadData(callback) {
                    const xhr = new XMLHttpRequest();
                    xhr.onload = () => callback(null, xhr.responseText);
                    xhr.onerror = () => callback(xhr.statusText);
                    xhr.open('GET', '/api/data');
                    xhr.send();
                }
                ```
                """,
                created_at="2024-01-02T12:00:00Z",
            ),
        ]

        # This will fail until implementation is complete
        from backend.src.integrations.siyuan_connector import process_document_for_code
        from backend.src.models.code_snippets import CodeSnippetStore

        store = CodeSnippetStore()

        # Process each document and extract/store code
        total_snippets = 0
        for doc in developer_notes:
            snippets = await process_document_for_code(doc.id, doc.content)
            await store.store_snippets(snippets)
            total_snippets += len(snippets)

        # Should have extracted multiple code snippets
        assert total_snippets >= 4  # At least 4 snippets from the mock docs

        # Verify snippets are stored and retrievable
        from backend.src.models.code_snippets import CodeQuery, CodeResult

        query = CodeQuery(query="", limit=10)
        result = await store.search_snippets(query)

        assert result.total_found >= 4
        assert len(result.snippets) >= 4

    @pytest.mark.asyncio
    async def test_search_code_by_functionality(self):
        """
        Test searching for code by describing what it should do.

        This tests the natural language search capability that developers
        would use when they need code for a specific task.
        """
        from backend.src.models.code_snippets import CodeQuery, CodeSnippetStore

        store = CodeSnippetStore()

        # Assume some code snippets are already stored from previous test
        # Search for "sorting algorithm"
        query = CodeQuery(query="sorting algorithm", limit=5)
        result = await store.search_snippets(query)

        # Should find sorting-related code
        assert result.total_found > 0
        found_languages = {s.language for s in result.snippets}
        assert "python" in found_languages

        # Check that snippets contain sorting-related keywords
        sorting_found = any(
            "sort" in snippet.code.lower() or "sort" in snippet.title.lower()
            for snippet in result.snippets
        )
        assert sorting_found

    @pytest.mark.asyncio
    async def test_search_code_by_language_and_concept(self):
        """
        Test filtering code search by programming language and concepts.
        """
        from backend.src.models.code_snippets import CodeQuery, CodeSnippetStore

        store = CodeSnippetStore()

        # Search for JavaScript async code
        query = CodeQuery(
            query="async data fetching",
            language="javascript",
            tags=["async", "api"],
            limit=5,
        )
        result = await store.search_snippets(query)

        # Should find JavaScript snippets
        assert result.total_found > 0
        for snippet in result.snippets:
            assert snippet.language == "javascript"
            # Should contain async-related keywords
            assert any(
                keyword in snippet.code.lower()
                for keyword in ["async", "await", "promise", "fetch"]
            )

    @pytest.mark.asyncio
    async def test_code_search_api_integration(self):
        """
        Test the complete API integration for code search.

        This tests the FastAPI endpoint that developers would call
        from the SiYuan plugin to search for code.
        """
        from backend.src.api.search import search_code
        from backend.src.models.code_snippets import CodeQuery

        # Create a search query
        query = CodeQuery(query="binary search algorithm", language="python", limit=3)

        # This will fail until the API endpoint is implemented
        result = await search_code(query)

        # Should return a proper result structure
        assert hasattr(result, "snippets")
        assert hasattr(result, "total_found")
        assert hasattr(result, "trace_id")
        assert isinstance(result.snippets, list)
        assert result.total_found >= 0
        assert isinstance(result.trace_id, str)

        # If snippets are found, they should be properly formatted
        if result.total_found > 0:
            for snippet in result.snippets:
                assert hasattr(snippet, "id")
                assert hasattr(snippet, "language")
                assert hasattr(snippet, "code")
                assert snippet.language == "python"

    @pytest.mark.asyncio
    async def test_developer_workflow_end_to_end(self):
        """
        Complete end-to-end test of the developer workflow.

        1. Process developer notes with code
        2. Search for specific functionality
        3. Verify results are relevant and properly formatted
        """
        from backend.src.api.search import search_code
        from backend.src.integrations.siyuan_connector import process_document_for_code
        from backend.src.models.code_snippets import CodeQuery, CodeSnippetStore

        # Step 1: Process a comprehensive developer note
        comprehensive_note = Document(
            id="comprehensive_doc",
            title="Developer Toolbox",
            content="""
            # Developer Toolbox

            ## Python Utilities

            ### File Operations
            ```python
            import os
            from pathlib import Path

            def find_files_by_extension(directory, extension):
                \"\"\"Find all files with given extension in directory.\"\"\"
                path = Path(directory)
                return list(path.rglob(f"*.{extension}"))

            def read_file_safe(filepath):
                \"\"\"Safely read file with error handling.\"\"\"
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        return f.read()
                except (IOError, OSError) as e:
                    print(f"Error reading file {filepath}: {e}")
                    return None
            ```

            ## JavaScript Helpers

            ### DOM Manipulation
            ```javascript
            function createElement(tag, props = {}, children = []) {
                const element = document.createElement(tag);

                // Set properties
                Object.entries(props).forEach(([key, value]) => {
                    if (key === 'className') {
                        element.className = value;
                    } else if (key.startsWith('on') && typeof value === 'function') {
                        element.addEventListener(key.slice(2).toLowerCase(), value);
                    } else {
                        element.setAttribute(key, value);
                    }
                });

                // Add children
                children.forEach(child => {
                    if (typeof child === 'string') {
                        element.appendChild(document.createTextNode(child));
                    } else {
                        element.appendChild(child);
                    }
                });

                return element;
            }
            ```

            ## SQL Queries

            ### User Management
            ```sql
            -- Get active users with their roles
            SELECT u.id, u.username, u.email, r.name as role_name
            FROM users u
            LEFT JOIN user_roles ur ON u.id = ur.user_id
            LEFT JOIN roles r ON ur.role_id = r.id
            WHERE u.active = 1
            ORDER BY u.created_at DESC;

            -- Update user status
            UPDATE users
            SET active = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
            ```
            """,
            created_at="2024-01-03T12:00:00Z",
        )

        # Process the document
        snippets = await process_document_for_code(
            comprehensive_note.id, comprehensive_note.content
        )

        # Store the snippets
        store = CodeSnippetStore()
        await store.store_snippets(snippets)

        # Step 2: Search for different types of code
        search_queries = [
            ("file operations", "python"),
            ("dom manipulation", "javascript"),
            ("user queries", "sql"),
        ]

        for search_term, expected_language in search_queries:
            query = CodeQuery(query=search_term, language=expected_language, limit=2)
            result = await search_code(query)

            # Should find relevant snippets
            assert result.total_found > 0
            assert all(s.language == expected_language for s in result.snippets)

            # Snippets should be properly formatted
            for snippet in result.snippets:
                assert len(snippet.code.strip()) > 0
                assert snippet.confidence > 0
                assert snippet.line_start >= 0
                assert snippet.line_end > snippet.line_start
