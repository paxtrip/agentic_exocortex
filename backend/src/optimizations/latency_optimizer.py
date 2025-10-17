"""
Latency optimization for RAG system.

This module implements optimizations to achieve target latencies:
- E2E LLM responses: < 5-7 seconds
- Cached responses: < 150ms

Key optimizations:
- Async processing pipelines
- Connection pooling
- Request batching
- Memory-efficient processing
"""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class LatencyMetrics:
    """Метрики задержки для мониторинга производительности"""

    total_time: float
    embedding_time: float
    search_time: float
    reranking_time: float
    llm_time: float
    cache_hit: bool
    timestamp: float


class LatencyOptimizer:
    """
    Оптимизатор задержек для RAG системы.

    Управляет асинхронной обработкой, пулами соединений и оптимизациями
    для достижения целевых показателей производительности.
    """

    def __init__(
        self,
        max_concurrent_requests: int = 10,
        embedding_batch_size: int = 32,
        search_timeout: float = 2.0,
        llm_timeout: float = 30.0,
    ):
        """
        Инициализация оптимизатора задержек.

        Args:
            max_concurrent_requests: Максимальное количество одновременных запросов
            embedding_batch_size: Размер батча для эмбеддингов
            search_timeout: Таймаут для поиска (секунды)
            llm_timeout: Таймаут для LLM (секунды)
        """
        self.max_concurrent_requests = max_concurrent_requests
        self.embedding_batch_size = embedding_batch_size
        self.search_timeout = search_timeout
        self.llm_timeout = llm_timeout

        # Семафор для ограничения одновременных запросов
        self.request_semaphore = asyncio.Semaphore(max_concurrent_requests)

        # Thread pool для CPU-bound операций
        self.executor = ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="latency_opt"
        )

        # Метрики производительности
        self.metrics: List[LatencyMetrics] = []
        self.metrics_lock = threading.Lock()

    async def optimize_pipeline(
        self,
        query: str,
        embedding_func: Callable[[str], Any],
        search_func: Callable[[Any], List[Dict]],
        rerank_func: Optional[Callable[[List[Dict], str], List[Dict]]] = None,
        llm_func: Optional[Callable[[str, List[Dict]], str]] = None,
        use_cache: bool = True,
    ) -> tuple[str, List[Dict], LatencyMetrics]:
        """
        Оптимизированный pipeline обработки запроса.

        Args:
            query: Запрос пользователя
            embedding_func: Функция создания эмбеддингов
            search_func: Функция поиска
            rerank_func: Функция переранжирования (опционально)
            llm_func: Функция LLM (опционально)
            use_cache: Использовать кэширование

        Returns:
            Кортеж (ответ, контексты, метрики)
        """
        start_time = time.time()

        async with self.request_semaphore:
            # Этап 1: Создание эмбеддингов (асинхронно)
            embedding_start = time.time()
            embedding = await self._async_embedding(embedding_func, query)
            embedding_time = time.time() - embedding_start

            # Этап 2: Поиск (с таймаутом)
            search_start = time.time()
            try:
                contexts = await asyncio.wait_for(
                    self._async_search(search_func, embedding),
                    timeout=self.search_timeout,
                )
            except asyncio.TimeoutError:
                # Fallback на базовый поиск без оптимизаций
                contexts = await self._async_search(search_func, embedding)
            search_time = time.time() - search_start

            # Этап 3: Переранжирование (опционально, параллельно)
            reranking_time = 0.0
            if rerank_func and contexts:
                rerank_start = time.time()
                contexts = await self._async_rerank(rerank_func, contexts, query)
                reranking_time = time.time() - rerank_start

            # Этап 4: LLM генерация (опционально)
            llm_time = 0.0
            answer = ""

            if llm_func:
                llm_start = time.time()
                try:
                    answer = await asyncio.wait_for(
                        self._async_llm(llm_func, query, contexts),
                        timeout=self.llm_timeout,
                    )
                except asyncio.TimeoutError:
                    answer = "Извините, ответ не может быть сгенерирован в установленный лимит времени."
                llm_time = time.time() - llm_start

            total_time = time.time() - start_time

            # Формирование метрик
            metrics = LatencyMetrics(
                total_time=total_time,
                embedding_time=embedding_time,
                search_time=search_time,
                reranking_time=reranking_time,
                llm_time=llm_time,
                cache_hit=False,  # TODO: интегрировать с кэшем
                timestamp=start_time,
            )

            # Сохранение метрик
            with self.metrics_lock:
                self.metrics.append(metrics)
                # Ограничение размера истории метрик
                if len(self.metrics) > 1000:
                    self.metrics = self.metrics[-1000:]

            return answer, contexts, metrics

    async def _async_embedding(self, embedding_func: Callable, query: str) -> Any:
        """Асинхронное создание эмбеддингов"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, embedding_func, query)

    async def _async_search(self, search_func: Callable, embedding: Any) -> List[Dict]:
        """Асинхронный поиск"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, search_func, embedding)

    async def _async_rerank(
        self, rerank_func: Callable, contexts: List[Dict], query: str
    ) -> List[Dict]:
        """Асинхронное переранжирование"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, rerank_func, contexts, query)

    async def _async_llm(
        self, llm_func: Callable, query: str, contexts: List[Dict]
    ) -> str:
        """Асинхронная генерация LLM"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, llm_func, query, contexts)

    def get_performance_stats(self) -> Dict[str, float]:
        """
        Получение статистики производительности.

        Returns:
            Dict с метриками производительности
        """
        with self.metrics_lock:
            if not self.metrics:
                return {}

            recent_metrics = self.metrics[-100:]  # Последние 100 запросов

            return {
                "avg_total_time": sum(m.total_time for m in recent_metrics)
                / len(recent_metrics),
                "avg_embedding_time": sum(m.embedding_time for m in recent_metrics)
                / len(recent_metrics),
                "avg_search_time": sum(m.search_time for m in recent_metrics)
                / len(recent_metrics),
                "avg_reranking_time": sum(m.reranking_time for m in recent_metrics)
                / len(recent_metrics),
                "avg_llm_time": sum(m.llm_time for m in recent_metrics)
                / len(recent_metrics),
                "cache_hit_rate": sum(1 for m in recent_metrics if m.cache_hit)
                / len(recent_metrics),
                "p95_total_time": sorted([m.total_time for m in recent_metrics])[
                    int(len(recent_metrics) * 0.95)
                ],
                "p99_total_time": sorted([m.total_time for m in recent_metrics])[
                    int(len(recent_metrics) * 0.99)
                ],
            }

    def check_latency_targets(self) -> Dict[str, bool]:
        """
        Проверка достижения целевых показателей задержки.

        Returns:
            Dict с результатами проверки целей
        """
        stats = self.get_performance_stats()

        if not stats:
            return {}

        return {
            "llm_target_met": stats.get("avg_total_time", float("inf")) < 7.0,  # < 5-7s
            "cache_target_met": stats.get("p95_total_time", float("inf"))
            < 0.150,  # < 150ms для кэшированных
            "search_target_met": stats.get("avg_search_time", float("inf"))
            < 1.0,  # < 1s для поиска
            "embedding_target_met": stats.get("avg_embedding_time", float("inf"))
            < 0.5,  # < 500ms для эмбеддингов
        }

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        self.executor.shutdown(wait=True)
