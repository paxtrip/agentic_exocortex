"""
SiYuan connector for document fetching and relationship extraction.

This module handles:
- Connecting to SiYuan API for document retrieval
- Extracting relationship patterns from document content
- Converting SiYuan documents to our internal format

Following the principle of "graceful degradation" - works even if SiYuan is unavailable.
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

from ..models.connections import Connection

logger = logging.getLogger(__name__)


class SiYuanConnector:
    """
    Connector for SiYuan note-taking application.

    Handles document fetching and relationship extraction for the RAG system.
    Designed to be resilient - continues working even if SiYuan is unavailable.
    """

    def __init__(self, base_url: str = "http://localhost:6806", api_token: str = None):
        """
        Initialize SiYuan connector.

        Args:
            base_url: SiYuan API base URL
            api_token: Optional API token for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _make_request(
        self, endpoint: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Make authenticated request to SiYuan API.

        Args:
            endpoint: API endpoint (e.g., '/api/notebook/lsNotebooks')
            data: Request payload

        Returns:
            API response data

        Raises:
            Exception: If request fails and SiYuan is required
        """
        if not self.session:
            raise RuntimeError("SiYuan connector not properly initialized")

        url = f"{self.base_url}{endpoint}"
        headers = {}

        if self.api_token:
            headers["Authorization"] = f"Token {self.api_token}"

        try:
            async with self.session.post(url, json=data, headers=headers) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.warning(f"SiYuan API request failed: {e}")
            # Return empty result for graceful degradation
            return {"code": -1, "msg": "SiYuan unavailable", "data": []}

    async def get_notebooks(self) -> List[Dict[str, Any]]:
        """
        Get list of available notebooks.

        Returns:
            List of notebook information
        """
        response = await self._make_request("/api/notebook/lsNotebooks", {})
        return response.get("data", [])

    async def get_documents(
        self, notebook_id: str, path: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Get documents from a notebook.

        Args:
            notebook_id: ID of the notebook
            path: Optional path within notebook

        Returns:
            List of document information
        """
        data = {"notebook": notebook_id, "path": path}
        response = await self._make_request("/api/filetree/listDocsByPath", data)
        return response.get("data", [])

    async def get_document_content(self, doc_id: str) -> Optional[str]:
        """
        Get content of a specific document.

        Args:
            doc_id: Document ID

        Returns:
            Document content as markdown string, or None if not found
        """
        data = {"id": doc_id}
        response = await self._make_request("/api/filetree/getDoc", data)

        if response.get("code") == 0:
            return response.get("data", {}).get("content", "")
        else:
            logger.warning(f"Failed to get document {doc_id}: {response.get('msg')}")
            return None

    async def extract_connections(self, doc_id: str, content: str) -> List[Connection]:
        """
        Extract document connections from content.

        Analyzes document text to find references to other documents,
        creating connection objects that represent relationships.

        Args:
            doc_id: ID of the source document
            content: Document content as text

        Returns:
            List of Connection objects representing relationships found in the text
        """
        connections = []

        # Pattern 1: Explicit references like "see: doc_name.md" or "See also: doc_name.md"
        reference_patterns = [
            r"see\s*:\s*([^\s]+\.md)",  # "see: filename.md"
            r"See also\s*:\s*([^\s]+\.md)",  # "See also: filename.md"
            r"reference\s*:\s*([^\s]+\.md)",  # "reference: filename.md"
            r"cf\.\s*([^\s]+\.md)",  # "cf. filename.md"
        ]

        for pattern in reference_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                target_doc = match.group(1).strip()
                # Extract context around the reference
                start = max(0, match.start() - 50)
                end = min(len(content), match.end() + 50)
                context = content[start:end].strip()

                connections.append(
                    Connection(
                        source_doc_id=doc_id,
                        target_doc_id=target_doc,
                        connection_type="reference",
                        strength=0.8,  # High confidence for explicit references
                        context=context,
                        created_at=datetime.utcnow().isoformat() + "Z",
                    )
                )

        # Pattern 2: Follow-up references like "follow_up: experiment_results.md"
        followup_pattern = r"follow_up\s*:\s*([^\s]+\.md)"
        matches = re.finditer(followup_pattern, content, re.IGNORECASE)
        for match in matches:
            target_doc = match.group(1).strip()
            start = max(0, match.start() - 50)
            end = min(len(content), match.end() + 50)
            context = content[start:end].strip()

            connections.append(
                Connection(
                    source_doc_id=doc_id,
                    target_doc_id=target_doc,
                    connection_type="follow_up",
                    strength=0.9,  # Very high confidence for explicit follow-ups
                    context=context,
                    created_at=datetime.utcnow().isoformat() + "Z",
                )
            )

        # Pattern 3: Related concept references like "related: quantum_theory.md"
        related_pattern = r"related\s*:\s*([^\s]+\.md)"
        matches = re.finditer(related_pattern, content, re.IGNORECASE)
        for match in matches:
            target_doc = match.group(1).strip()
            start = max(0, match.start() - 50)
            end = min(len(content), match.end() + 50)
            context = content[start:end].strip()

            connections.append(
                Connection(
                    source_doc_id=doc_id,
                    target_doc_id=target_doc,
                    connection_type="related_concept",
                    strength=0.6,  # Medium confidence for related concepts
                    context=context,
                    created_at=datetime.utcnow().isoformat() + "Z",
                )
            )

        # Pattern 4: Implicit references in sentences
        # Look for document names mentioned in context of relationships
        implicit_patterns = [
            r"(?:building on|based on|following|continuing|extending)\s+[^.]*(?:in|from)\s+([^\s]+\.md)",
            r"(?:led to|resulted in|produced|created)\s+[^.]*(?:in|from)\s+([^\s]+\.md)",
            r"(?:connects to|links to|relates to)\s+[^.]*(?:in|from)\s+([^\s]+\.md)",
        ]

        for pattern in implicit_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                target_doc = match.group(1).strip()
                start = max(0, match.start() - 50)
                end = min(len(content), match.end() + 50)
                context = content[start:end].strip()

                # Determine connection type based on context
                lower_context = context.lower()
                if "follow" in lower_context or "continu" in lower_context:
                    conn_type = "follow_up"
                    strength = 0.7
                elif "build" in lower_context or "base" in lower_context:
                    conn_type = "reference"
                    strength = 0.6
                else:
                    conn_type = "related_concept"
                    strength = 0.5

                connections.append(
                    Connection(
                        source_doc_id=doc_id,
                        target_doc_id=target_doc,
                        connection_type=conn_type,
                        strength=strength,
                        context=context,
                        created_at=datetime.utcnow().isoformat() + "Z",
                    )
                )

        logger.info(f"Extracted {len(connections)} connections from document {doc_id}")
        return connections

    async def sync_documents(self, notebook_id: str) -> List[Dict[str, Any]]:
        """
        Sync documents from SiYuan notebook.

        Retrieves all documents and their connections, storing them
        in the connection database.

        Args:
            notebook_id: ID of notebook to sync

        Returns:
            List of processed documents with their metadata
        """
        documents = []
        docs_list = await self.get_documents(notebook_id)

        for doc_info in docs_list:
            doc_id = doc_info.get("id")
            if not doc_id:
                continue

            content = await self.get_document_content(doc_id)
            if content:
                # Extract connections from content
                connections = await self.extract_connections(doc_id, content)

                documents.append(
                    {
                        "id": doc_id,
                        "title": doc_info.get("title", ""),
                        "content": content,
                        "path": doc_info.get("path", ""),
                        "updated": doc_info.get("updated", ""),
                        "connections": connections,
                    }
                )

        logger.info(f"Synced {len(documents)} documents from notebook {notebook_id}")
        return documents


# Convenience function for backward compatibility
async def extract_connections(doc_id: str, content: str) -> List[Connection]:
    """
    Extract connections from document content.

    This is a convenience function that creates a temporary connector
    to extract connections without needing to manage the connector lifecycle.

    Args:
        doc_id: Source document ID
        content: Document content

    Returns:
        List of extracted connections
    """
    async with SiYuanConnector() as connector:
        return await connector.extract_connections(doc_id, content)
