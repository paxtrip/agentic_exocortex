"""
Caching optimization for RAG system.

This module implements intelligent caching to achieve < 150ms latency for cached responses.
Uses hybrid similarity caching with semantic and exact matching.

Key features:
- Semantic cache with embeddings similarity
- Exact match cache for identical queries
- TTL-based cache invalidation
- Memory-efficient storage with LRU eviction
"""

import asyncio
import hashlib
import json
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class CacheEntry:
    """Запись кэша с метаданными"""

    query: str
    answer: str
    contexts: List[Dict]
    embedding: Optional[List[float]] = None
    timestamp: float = field(default_factory=time.time)
    access_count: int = 0
    ttl: Optional[float] = None  # Time to live in seconds

    def is_expired(self) -> bool:
        """Проверка истечения срока действия"""
        if self.ttl is None:
            return False
        return time.time() - self.timestamp > self.ttl

    def update_access(self):
        """Обновление статистики доступа"""
        self.access_count += 1


class SemanticCache:
    """
    Семантический кэш с поддержкой similarity search.

    Использует гибридный подход: точное совпадение + семантическая близость.
    """

    def __init__(
        self,
        max_size: int = 1000,
        similarity_threshold: float = 0.85,
        default_ttl: float = 3600,  # 1 hour
        embedding_func: Optional[callable] = None,
    ):
        """
        Инициализация семантического кэша.

        Args:
            max_size: Максимальный размер кэша
            similarity_threshold: Порог similarity для семантического поиска
            default_ttl: Время жизни по умолчанию (секунды)
            embedding_func: Функция для создания эмбеддингов
        """
        self.max_size = max_size
        self.similarity_threshold = similarity_threshold
        self.default_ttl = default_ttl
        self.embedding_func = embedding_func

        # Основной кэш: query_hash -> CacheEntry
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.RLock()

        # Индекс для семантического поиска: embedding -> query_hash
        self.semantic_index: List[Tuple[List[float], str]] = []

        # Статистика
        self.hits = 0
        self.misses = 0
        self.semantic_hits = 0

    def _get_query_hash(self, query: str) -> str:
        """Получение хэша запроса для точного совпадения"""
        return hashlib.md5(query.encode("utf-8")).hexdigest()

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Расчет косинусного сходства"""
        import math

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def _jaccard_similarity(self, a: str, b: str) -> float:
        """Расчет Jaccard similarity для текстов"""
        set_a = set(a.lower().split())
        set_b = set(b.lower().split())

        intersection = len(set_a & set_b)
        union = len(set_a | set_b)

        return intersection / union if union > 0 else 0.0

    async def get(
        self, query: str, query_embedding: Optional[List[float]] = None
    ) -> Optional[CacheEntry]:
        """
        Получение из кэша с поддержкой семантического поиска.

        Args:
            query: Запрос
            query_embedding: Эмбеддинг запроса

        Returns:
            CacheEntry или None
        """
        with self.lock:
            # Сначала проверяем точное совпадение
            query_hash = self._get_query_hash(query)

            if query_hash in self.cache:
                entry = self.cache[query_hash]
                if not entry.is_expired():
                    entry.update_access()
                    self.cache.move_to_end(query_hash)  # LRU
                    self.hits += 1
                    return entry

            # Если точного совпадения нет, ищем семантически похожие
            if query_embedding and self.semantic_index:
                best_match = None
                best_similarity = 0.0

                for embedding, hash_key in self.semantic_index:
                    if len(embedding) == len(query_embedding):
                        similarity = self._cosine_similarity(query_embedding, embedding)
                        if (
                            similarity > best_similarity
                            and similarity >= self.similarity_threshold
                        ):
                            best_similarity = similarity
                            best_match = hash_key

                if best_match and best_match in self.cache:
                    entry = self.cache[best_match]
                    if not entry.is_expired():
                        entry.update_access()
                        self.cache.move_to_end(best_match)
                        self.semantic_hits += 1
                        self.hits += 1
                        return entry

            self.misses += 1
            return None

    async def put(
        self,
        query: str,
        answer: str,
        contexts: List[Dict],
        query_embedding: Optional[List[float]] = None,
        ttl: Optional[float] = None,
    ):
        """
        Сохранение в кэш.

        Args:
            query: Запрос
            answer: Ответ
            contexts: Контексты
            query_embedding: Эмбеддинг запроса
            ttl: Время жизни
        """
        with self.lock:
            query_hash = self._get_query_hash(query)
            ttl = ttl or self.default_ttl

            entry = CacheEntry(
                query=query,
                answer=answer,
                contexts=contexts,
                embedding=query_embedding,
                ttl=ttl,
            )

            # Добавление в основной кэш
            self.cache[query_hash] = entry
            self.cache.move_to_end(query_hash)

            # Добавление в семантический индекс
            if query_embedding:
                self.semantic_index.append((query_embedding, query_hash))

            # Очистка устаревших записей
            self._cleanup()

    def _cleanup(self):
        """Очистка устаревших и лишних записей"""
        # Удаление истекших записей
        expired_keys = [k for k, v in self.cache.items() if v.is_expired()]
        for key in expired_keys:
            del self.cache[key]
            # Удаление из семантического индекса
            self.semantic_index = [
                (emb, h) for emb, h in self.semantic_index if h != key
            ]

        # LRU eviction если превышен размер
        while len(self.cache) > self.max_size:
            oldest_key, _ = self.cache.popitem(last=False)
            # Удаление из семантического индекса
            self.semantic_index = [
                (emb, h) for emb, h in self.semantic_index if h != oldest_key
            ]

    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики кэша"""
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0.0
            semantic_hit_rate = (
                self.semantic_hits / total_requests if total_requests > 0 else 0.0
            )

            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hit_rate": hit_rate,
                "semantic_hit_rate": semantic_hit_rate,
                "total_requests": total_requests,
                "hits": self.hits,
                "misses": self.misses,
                "semantic_hits": self.semantic_hits,
            }

    def clear(self):
        """Очистка кэша"""
        with self.lock:
            self.cache.clear()
            self.semantic_index.clear()
            self.hits = 0
            self.misses = 0
            self.semantic_hits = 0


class CachingOptimizer:
    """
    Оптимизатор кэширования для RAG системы.

    Управляет многоуровневым кэшированием для достижения < 150ms latency.
    """

    def __init__(
        self,
        cache_size: int = 1000,
        similarity_threshold: float = 0.85,
        default_ttl: float = 3600,
    ):
        """
        Инициализация оптимизатора кэширования.

        Args:
            cache_size: Размер кэша
            similarity_threshold: Порог similarity
            default_ttl: TTL по умолчанию
        """
        self.cache = SemanticCache(
            max_size=cache_size,
            similarity_threshold=similarity_threshold,
            default_ttl=default_ttl,
        )

    async def get_cached_response(
        self, query: str, query_embedding: Optional[List[float]] = None
    ) -> Optional[Tuple[str, List[Dict]]]:
        """
        Получение кэшированного ответа.

        Args:
            query: Запрос
            query_embedding: Эмбеддинг запроса

        Returns:
            Кортеж (ответ, контексты) или None
        """
        entry = await self.cache.get(query, query_embedding)
        if entry:
            return entry.answer, entry.contexts
        return None

    async def cache_response(
        self,
        query: str,
        answer: str,
        contexts: List[Dict],
        query_embedding: Optional[List[float]] = None,
        ttl: Optional[float] = None,
    ):
        """
        Кэширование ответа.

        Args:
            query: Запрос
            answer: Ответ
            contexts: Контексты
            query_embedding: Эмбеддинг запроса
            ttl: Время жизни
        """
        await self.cache.put(query, answer, contexts, query_embedding, ttl)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Получение статистики кэша"""
        return self.cache.get_stats()

    def check_cache_performance(self) -> Dict[str, bool]:
        """
        Проверка достижения целей производительности кэша.

        Returns:
            Dict с результатами проверки
        """
        stats = self.get_cache_stats()

        return {
            "hit_rate_target_met": stats.get("hit_rate", 0.0) >= 0.7,  # 70% hit rate
            "size_efficient": stats.get("size", 0) <= stats.get("max_size", 1000),
            "semantic_cache_active": stats.get("semantic_hits", 0) > 0,
        }
