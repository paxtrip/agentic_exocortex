"""
Base models for document connections.

This module defines the core data models used throughout the connection system.
"""

from typing import List

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
