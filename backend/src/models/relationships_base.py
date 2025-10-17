"""
Base models for semantic relationships in User Story 3.

This module defines the core data models for semantic relationships
between documents, used by the semantic analyzer and relationship storage.
"""

from pydantic import BaseModel, Field, validator


class SemanticRelationship(BaseModel):
    """Semantic relationship between two documents."""

    source_id: str
    target_id: str
    relationship_type: str  # 'similar', 'contrasts', 'builds_on', 'related'
    confidence: float = Field(ge=0.0, le=1.0)  # 0.0 to 1.0
    context: str  # Why this relationship exists

    @validator("confidence")
    def confidence_must_be_valid(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v

    class Config:
        """Pydantic configuration."""

        validate_assignment = True
