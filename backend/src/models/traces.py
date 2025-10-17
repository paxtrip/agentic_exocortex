"""
Thinking Traces Model for Unified RAG System.

This module provides structured storage and retrieval of thinking traces
for high-confidence answers. Traces help users understand the reasoning
process and build trust in the system's responses.

Following the principle of "Honesty Over Performance" - we show our work
so users can understand how answers were derived.
"""

import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TraceType(Enum):
    """Types of thinking traces."""

    LLM_GENERATION = "llm_generation"
    EXTRACTIVE_QA = "extractive_qa"
    VECTOR_SEARCH = "vector_search"
    FTS_SEARCH = "fts_search"
    RERANKING = "reranking"
    CONNECTION_DISCOVERY = "connection_discovery"
    SEMANTIC_ANALYSIS = "semantic_analysis"


class ConfidenceLevel(Enum):
    """Confidence levels for traces."""

    HIGH = "high"  # > 0.8
    MEDIUM = "medium"  # 0.5-0.8
    LOW = "low"  # < 0.5


@dataclass
class TraceStep:
    """Individual step in the thinking process."""

    step_type: TraceType
    description: str
    confidence: float
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    duration_ms: int
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["step_type"] = self.step_type.value
        return data


@dataclass
class ThinkingTrace:
    """Complete thinking trace for a query."""

    trace_id: str
    query: str
    final_answer: str
    overall_confidence: float
    confidence_level: ConfidenceLevel
    steps: List[TraceStep]
    total_duration_ms: int
    created_at: str
    provider_used: Optional[str] = None
    degradation_level: Optional[str] = None  # "llm", "qa", "search"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["confidence_level"] = self.confidence_level.value
        data["steps"] = [step.to_dict() for step in self.steps]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ThinkingTrace":
        """Create from dictionary."""
        data_copy = data.copy()
        data_copy["confidence_level"] = ConfidenceLevel(data["confidence_level"])
        data_copy["steps"] = [TraceStep(**step_data) for step_data in data["steps"]]
        return cls(**data_copy)


class TraceStore:
    """
    Storage for thinking traces.

    Provides efficient storage and retrieval of traces for analysis
    and user transparency.
    """

    def __init__(self):
        # In-memory storage - in production, this would be a database
        self.traces: Dict[str, ThinkingTrace] = {}
        self.max_traces = 1000  # Limit memory usage

    def store_trace(self, trace: ThinkingTrace) -> bool:
        """
        Store a thinking trace.

        Args:
            trace: The trace to store

        Returns:
            True if stored successfully
        """
        try:
            self.traces[trace.trace_id] = trace

            # Simple LRU eviction
            if len(self.traces) > self.max_traces:
                oldest_key = min(
                    self.traces.keys(), key=lambda k: self.traces[k].created_at
                )
                del self.traces[oldest_key]

            logger.debug(f"Stored trace {trace.trace_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store trace {trace.trace_id}: {e}")
            return False

    def get_trace(self, trace_id: str) -> Optional[ThinkingTrace]:
        """
        Retrieve a trace by ID.

        Args:
            trace_id: The trace identifier

        Returns:
            ThinkingTrace if found, None otherwise
        """
        return self.traces.get(trace_id)

    def get_recent_traces(self, limit: int = 50) -> List[ThinkingTrace]:
        """
        Get recent traces ordered by creation time.

        Args:
            limit: Maximum number of traces to return

        Returns:
            List of recent traces
        """
        traces = list(self.traces.values())
        traces.sort(key=lambda t: t.created_at, reverse=True)
        return traces[:limit]

    def get_traces_by_confidence(
        self, min_confidence: float, limit: int = 50
    ) -> List[ThinkingTrace]:
        """
        Get traces with confidence above threshold.

        Args:
            min_confidence: Minimum confidence level
            limit: Maximum number of traces to return

        Returns:
            List of high-confidence traces
        """
        matching_traces = [
            trace
            for trace in self.traces.values()
            if trace.overall_confidence >= min_confidence
        ]
        matching_traces.sort(key=lambda t: t.overall_confidence, reverse=True)
        return matching_traces[:limit]

    def get_trace_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored traces.

        Returns:
            Dictionary with trace statistics
        """
        if not self.traces:
            return {
                "total_traces": 0,
                "avg_confidence": 0.0,
                "high_confidence_count": 0,
                "degradation_levels": {},
                "step_types": {},
            }

        confidences = [t.overall_confidence for t in self.traces.values()]
        high_confidence = sum(1 for c in confidences if c > 0.8)

        degradation_counts = {}
        step_type_counts = {}

        for trace in self.traces.values():
            # Count degradation levels
            level = trace.degradation_level or "unknown"
            degradation_counts[level] = degradation_counts.get(level, 0) + 1

            # Count step types
            for step in trace.steps:
                step_type = step.step_type.value
                step_type_counts[step_type] = step_type_counts.get(step_type, 0) + 1

        return {
            "total_traces": len(self.traces),
            "avg_confidence": sum(confidences) / len(confidences),
            "high_confidence_count": high_confidence,
            "degradation_levels": degradation_counts,
            "step_types": step_type_counts,
        }


class TraceBuilder:
    """
    Builder for creating thinking traces step by step.

    Helps construct detailed traces during query processing.
    """

    def __init__(self, query: str):
        self.query = query
        self.steps: List[TraceStep] = []
        self.start_time = datetime.utcnow()
        self.trace_id = f"trace_{self.start_time.timestamp()}"

    def add_step(
        self,
        step_type: TraceType,
        description: str,
        confidence: float,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "TraceBuilder":
        """
        Add a step to the trace.

        Args:
            step_type: Type of the step
            description: Human-readable description
            confidence: Confidence score for this step
            input_data: What went into this step
            output_data: What came out of this step
            metadata: Additional metadata

        Returns:
            Self for chaining
        """
        step_start = datetime.utcnow()
        duration = int((step_start - self.start_time).total_seconds() * 1000)

        step = TraceStep(
            step_type=step_type,
            description=description,
            confidence=confidence,
            input_data=input_data,
            output_data=output_data,
            duration_ms=duration,
            timestamp=step_start.isoformat() + "Z",
            metadata=metadata,
        )

        self.steps.append(step)
        return self

    def build(
        self,
        final_answer: str,
        provider_used: Optional[str] = None,
        degradation_level: Optional[str] = None,
    ) -> ThinkingTrace:
        """
        Build the complete thinking trace.

        Args:
            final_answer: The final answer provided
            provider_used: Which LLM provider was used
            degradation_level: Which degradation level was used

        Returns:
            Complete ThinkingTrace
        """
        total_duration = int(
            (datetime.utcnow() - self.start_time).total_seconds() * 1000
        )

        # Calculate overall confidence as weighted average of step confidences
        if self.steps:
            overall_confidence = sum(step.confidence for step in self.steps) / len(
                self.steps
            )
        else:
            overall_confidence = 0.0

        # Determine confidence level
        if overall_confidence > 0.8:
            confidence_level = ConfidenceLevel.HIGH
        elif overall_confidence > 0.5:
            confidence_level = ConfidenceLevel.MEDIUM
        else:
            confidence_level = ConfidenceLevel.LOW

        return ThinkingTrace(
            trace_id=self.trace_id,
            query=self.query,
            final_answer=final_answer,
            overall_confidence=overall_confidence,
            confidence_level=confidence_level,
            steps=self.steps,
            total_duration_ms=total_duration,
            created_at=self.start_time.isoformat() + "Z",
            provider_used=provider_used,
            degradation_level=degradation_level,
        )


# Global trace store instance
trace_store = TraceStore()
