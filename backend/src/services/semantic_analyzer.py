"""
Semantic analyzer service for User Story 3 (Writer workflow).

This service extracts semantic relationships between documents to help writers
discover idea connections across their writing. It analyzes document content
to find meaningful relationships like "similar", "contrasts", "builds_on", etc.

The analyzer uses semantic similarity and concept extraction to identify
connections that might not be obvious to the writer, enabling serendipitous
discovery of idea relationships.
"""

import logging
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

# Import our contract types
from ..models.relationships import SemanticRelationship

logger = logging.getLogger(__name__)


class SemanticAnalyzer:
    """
    Service for extracting semantic relationships between documents.

    This analyzer identifies various types of relationships:
    - 'similar': Documents with overlapping concepts/themes
    - 'contrasts': Documents with opposing viewpoints
    - 'builds_on': Documents that extend or develop ideas from others
    - 'related': Documents with tangential connections
    """

    def __init__(self):
        """Initialize the semantic analyzer."""
        # Keywords that indicate different relationship types
        self.relationship_indicators = {
            "similar": [
                "similar",
                "like",
                "alike",
                "same",
                "comparable",
                "parallel",
                "analogous",
                "equivalent",
                "corresponding",
                "matching",
            ],
            "contrasts": [
                "contrast",
                "opposite",
                "different",
                "versus",
                "vs",
                "unlike",
                "conflicting",
                "contradictory",
                "opposing",
                "divergent",
            ],
            "builds_on": [
                "builds on",
                "extends",
                "develops",
                "advances",
                "improves",
                "enhances",
                "refines",
                "elaborates",
                "expands",
                "deepens",
            ],
            "related": [
                "related",
                "connected",
                "linked",
                "associated",
                "tied",
                "interconnected",
                "interrelated",
                "correlated",
                "bound",
            ],
        }

        # Concept categories for clustering
        self.concept_categories = {
            "consciousness": [
                "consciousness",
                "awareness",
                "self-reflection",
                "meta-consciousness",
            ],
            "networks": ["neural networks", "networks", "connections", "web"],
            "evolution": ["evolution", "development", "progression", "stages"],
            "creativity": ["creative", "creativity", "writing", "stories", "ideas"],
            "philosophy": ["philosophy", "mind", "thought", "reasoning"],
        }

    def extract_relationships(
        self, documents: List[Dict[str, Any]]
    ) -> List[SemanticRelationship]:
        """
        Extract semantic relationships between documents.

        Args:
            documents: List of document dictionaries with 'id', 'content', 'title'

        Returns:
            List of semantic relationships found
        """
        if len(documents) < 2:
            return []

        relationships = []

        # Compare each pair of documents
        for i, doc1 in enumerate(documents):
            for j, doc2 in enumerate(documents[i + 1 :], i + 1):
                relationship = self._analyze_document_pair(doc1, doc2)
                if relationship:
                    relationships.append(relationship)

        logger.info(
            f"Extracted {len(relationships)} semantic relationships from {len(documents)} documents"
        )
        return relationships

    def _analyze_document_pair(
        self, doc1: Dict[str, Any], doc2: Dict[str, Any]
    ) -> Optional[SemanticRelationship]:
        """
        Analyze a pair of documents to find semantic relationships.

        Args:
            doc1, doc2: Document dictionaries

        Returns:
            SemanticRelationship if one is found, None otherwise
        """
        # Extract concepts from both documents
        concepts1 = self._extract_concepts_from_text(doc1["content"])
        concepts2 = self._extract_concepts_from_text(doc2["content"])

        # Calculate semantic similarity
        similarity_score = self._calculate_semantic_similarity(concepts1, concepts2)

        # Determine relationship type and confidence
        relationship_type, confidence = self._determine_relationship_type(
            doc1, doc2, concepts1, concepts2, similarity_score
        )

        if confidence > 0.3:  # Minimum threshold for meaningful relationships
            # Determine which document is source vs target (arbitrary but consistent)
            source_id = doc1["id"] if doc1["id"] < doc2["id"] else doc2["id"]
            target_id = doc2["id"] if doc1["id"] < doc2["id"] else doc1["id"]

            context = self._generate_relationship_context(
                doc1 if source_id == doc1["id"] else doc2,
                doc2 if target_id == doc2["id"] else doc1,
                relationship_type,
                concepts1,
                concepts2,
            )

            return SemanticRelationship(
                source_id=source_id,
                target_id=target_id,
                relationship_type=relationship_type,
                confidence=confidence,
                context=context,
            )

        return None

    def _extract_concepts_from_text(self, text: str) -> List[str]:
        """
        Extract key concepts from document text.

        Args:
            text: Document content

        Returns:
            List of extracted concepts
        """
        concepts = []

        # Convert to lowercase for matching
        text_lower = text.lower()

        # Extract concepts from predefined categories
        for category, keywords in self.concept_categories.items():
            for keyword in keywords:
                if keyword in text_lower:
                    concepts.append(keyword)
                    break  # Only add category once

        # Extract individual words that appear frequently or are important
        words = re.findall(r"\b\w+\b", text_lower)
        word_freq = defaultdict(int)

        for word in words:
            if len(word) > 3:  # Skip short words
                word_freq[word] += 1

        # Add frequent words as concepts (appearing more than once)
        for word, freq in word_freq.items():
            if freq > 1 and word not in [
                "that",
                "this",
                "with",
                "from",
                "they",
                "have",
                "been",
            ]:
                concepts.append(word)

        return list(set(concepts))  # Remove duplicates

    def _calculate_semantic_similarity(
        self, concepts1: List[str], concepts2: List[str]
    ) -> float:
        """
        Calculate semantic similarity between two concept sets.

        Args:
            concepts1, concepts2: Lists of concepts

        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not concepts1 or not concepts2:
            return 0.0

        # Jaccard similarity
        set1 = set(concepts1)
        set2 = set(concepts2)

        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        if union == 0:
            return 0.0

        return intersection / union

    def _determine_relationship_type(
        self,
        doc1: Dict[str, Any],
        doc2: Dict[str, Any],
        concepts1: List[str],
        concepts2: List[str],
        similarity_score: float,
    ) -> Tuple[str, float]:
        """
        Determine the type and confidence of relationship between documents.

        Args:
            doc1, doc2: Document dictionaries
            concepts1, concepts2: Extracted concepts
            similarity_score: Semantic similarity score

        Returns:
            Tuple of (relationship_type, confidence)
        """
        # Check for explicit relationship indicators in text
        combined_text = (doc1["content"] + " " + doc2["content"]).lower()

        for rel_type, indicators in self.relationship_indicators.items():
            for indicator in indicators:
                if indicator in combined_text:
                    return rel_type, min(
                        0.9, similarity_score + 0.3
                    )  # Boost confidence

        # Determine based on similarity score and concept overlap
        if similarity_score > 0.7:
            return "similar", similarity_score
        elif similarity_score > 0.4:
            return "related", similarity_score
        elif self._have_contrasting_concepts(concepts1, concepts2):
            return "contrasts", max(0.4, similarity_score)
        elif self._builds_on_relationship(doc1, doc2):
            return "builds_on", max(0.5, similarity_score)
        else:
            return (
                "related",
                similarity_score * 0.8,
            )  # Reduce confidence for weak relationships

    def _have_contrasting_concepts(
        self, concepts1: List[str], concepts2: List[str]
    ) -> bool:
        """
        Check if documents have contrasting concepts.

        Args:
            concepts1, concepts2: Concept lists

        Returns:
            True if contrasting concepts found
        """
        # Simple heuristic: look for opposite concepts
        opposites = [
            ("consciousness", "unconsciousness"),
            ("evolution", "stagnation"),
            ("creative", "mechanical"),
            ("networks", "isolation"),
        ]

        set1 = set(concepts1)
        set2 = set(concepts2)

        for opp1, opp2 in opposites:
            if (opp1 in set1 and opp2 in set2) or (opp2 in set1 and opp1 in set2):
                return True

        return False

    def _builds_on_relationship(
        self, doc1: Dict[str, Any], doc2: Dict[str, Any]
    ) -> bool:
        """
        Check if one document builds on concepts from another.

        Args:
            doc1, doc2: Document dictionaries

        Returns:
            True if build-on relationship detected
        """
        # Simple heuristic: check if titles suggest progression
        title1 = doc1["title"].lower()
        title2 = doc2["title"].lower()

        progression_words = [
            "evolution",
            "development",
            "advancement",
            "progression",
            "extension",
            "expansion",
            "deepening",
            "refinement",
        ]

        return any(word in title1 or word in title2 for word in progression_words)

    def _generate_relationship_context(
        self,
        source_doc: Dict[str, Any],
        target_doc: Dict[str, Any],
        relationship_type: str,
        concepts1: List[str],
        concepts2: List[str],
    ) -> str:
        """
        Generate human-readable context for the relationship.

        Args:
            source_doc, target_doc: Document dictionaries
            relationship_type: Type of relationship
            concepts1, concepts2: Concept lists

        Returns:
            Descriptive context string
        """
        shared_concepts = set(concepts1).intersection(set(concepts2))

        if relationship_type == "similar":
            if shared_concepts:
                return f"Both discuss {', '.join(list(shared_concepts)[:2])}"
            else:
                return "Share similar themes and concepts"
        elif relationship_type == "contrasts":
            return "Present contrasting viewpoints on related topics"
        elif relationship_type == "builds_on":
            return f"'{target_doc['title']}' extends ideas from '{source_doc['title']}'"
        elif relationship_type == "related":
            if shared_concepts:
                return f"Connected through {', '.join(list(shared_concepts)[:2])}"
            else:
                return "Tangentially related concepts"
        else:
            return "Semantic connection detected"

    def extract_concepts(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract concepts from a collection of documents.

        Args:
            documents: List of document dictionaries

        Returns:
            List of concept dictionaries with metadata
        """
        all_concepts = []

        for doc in documents:
            concepts = self._extract_concepts_from_text(doc["content"])
            for concept in concepts:
                all_concepts.append(
                    {
                        "name": concept,
                        "document_id": doc["id"],
                        "document_title": doc["title"],
                        "frequency": doc["content"].lower().count(concept.lower()),
                    }
                )

        return all_concepts

    def cluster_concepts(
        self, concepts: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """
        Cluster concepts by semantic similarity.

        Args:
            concepts: List of concept dictionaries

        Returns:
            List of concept clusters
        """
        # Simple clustering based on concept names
        clusters = defaultdict(list)

        for concept in concepts:
            # Group by first letter or category
            name = concept["name"]
            if name in self.concept_categories["consciousness"]:
                clusters["consciousness"].append(concept)
            elif name in self.concept_categories["networks"]:
                clusters["networks"].append(concept)
            elif name in self.concept_categories["evolution"]:
                clusters["evolution"].append(concept)
            elif name in self.concept_categories["creativity"]:
                clusters["creativity"].append(concept)
            elif name in self.concept_categories["philosophy"]:
                clusters["philosophy"].append(concept)
            else:
                # Group by first letter
                clusters[name[0].upper()].append(concept)

        # Return non-empty clusters
        return [cluster for cluster in clusters.values() if cluster]
