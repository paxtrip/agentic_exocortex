"""
Performance optimizations for RAG system.

This module contains optimizations to achieve latency targets:
- E2E LLM < 5-7s
- Cached responses < 150ms
- Recall@15 ≥ 90%
"""

from .caching_optimizer import CachingOptimizer
from .latency_optimizer import LatencyOptimizer
from .vector_optimizer import VectorOptimizer

__all__ = ["LatencyOptimizer", "CachingOptimizer", "VectorOptimizer"]
