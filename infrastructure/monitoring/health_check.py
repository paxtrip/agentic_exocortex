#!/usr/bin/env python3
"""
Health check endpoints for RAG system monitoring.

This module provides comprehensive health monitoring:
- Service availability checks
- Performance metrics collection
- Dependency status validation
- Alert generation for critical issues

Endpoints:
- /health/live - Liveness probe
- /health/ready - Readiness probe
- /health/metrics - Detailed metrics
- /health/dependencies - Dependency status
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp
import psutil
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


class HealthStatus(BaseModel):
    """Модель статуса здоровья"""

    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: str
    version: str
    uptime_seconds: float
    checks: Dict[str, Any]


class DependencyStatus(BaseModel):
    """Модель статуса зависимости"""

    name: str
    status: str
    response_time_ms: Optional[float]
    error: Optional[str]
    last_check: str


class MetricsSnapshot(BaseModel):
    """Модель снимка метрик"""

    timestamp: str
    system: Dict[str, Any]
    application: Dict[str, Any]
    dependencies: List[DependencyStatus]


class HealthChecker:
    """
    Проверяльщик здоровья системы RAG.

    Выполняет комплексные проверки всех компонентов системы.
    """

    def __init__(self, version: str = "1.0.0"):
        self.version = version
        self.start_time = time.time()
        self.last_metrics_update = 0
        self.metrics_cache: Optional[MetricsSnapshot] = None
        self.cache_ttl = 30  # seconds

        # Конфигурация зависимостей для проверки
        self.dependencies = {
            "qdrant": {
                "url": "http://qdrant:6333/health",  # Используем имя сервиса из docker-compose
                "timeout": 5.0,
            },
            "sqlite": {
                "path": "/app/data/knowledge.db",  # Путь внутри контейнера API
                "check_function": self._check_sqlite,
            },
            "embeddings": {"check_function": self._check_embeddings_service},
            "siyuan": {
                "url": "http://siyuan:6806/api/system/version",  # Проверка SiYuan API
                "timeout": 5.0,
            },
        }

    async def check_liveness(self) -> HealthStatus:
        """
        Проверка живости приложения (liveness probe).

        Возвращает 200 если приложение живо, 500 если мертво.
        """
        try:
            # Базовые проверки
            uptime = time.time() - self.start_time

            # Проверка что процесс не завис
            if uptime > 0:  # Процесс работает
                status = "healthy"
            else:
                status = "unhealthy"

            return HealthStatus(
                status=status,
                timestamp=datetime.utcnow().isoformat(),
                version=self.version,
                uptime_seconds=uptime,
                checks={
                    "process_alive": True,
                    "memory_usage": self._get_memory_usage(),
                },
            )

        except Exception as e:
            return HealthStatus(
                status="unhealthy",
                timestamp=datetime.utcnow().isoformat(),
                version=self.version,
                uptime_seconds=time.time() - self.start_time,
                checks={"error": str(e)},
            )

    async def check_readiness(self) -> HealthStatus:
        """
        Проверка готовности приложения (readiness probe).

        Возвращает 200 если приложение готово принимать трафик.
        """
        checks = {}
        overall_status = "healthy"

        try:
            # Проверка зависимостей
            dependency_checks = await self._check_all_dependencies()
            checks["dependencies"] = dependency_checks

            # Если критические зависимости не работают
            critical_deps = ["qdrant", "sqlite"]
            for dep_name in critical_deps:
                if (
                    dep_name in dependency_checks
                    and dependency_checks[dep_name]["status"] != "healthy"
                ):
                    overall_status = "unhealthy"
                    break

            # Проверка системных ресурсов
            system_checks = self._check_system_resources()
            checks["system"] = system_checks

            # Если системные ресурсы критически низкие
            if system_checks.get("memory_critical", False) or system_checks.get(
                "cpu_critical", False
            ):
                overall_status = "degraded"

            # Проверка очередей запросов (если есть)
            queue_checks = await self._check_request_queues()
            checks["queues"] = queue_checks

            if queue_checks.get("queue_full", False):
                overall_status = "degraded"

        except Exception as e:
            overall_status = "unhealthy"
            checks["error"] = str(e)

        return HealthStatus(
            status=overall_status,
            timestamp=datetime.utcnow().isoformat(),
            version=self.version,
            uptime_seconds=time.time() - self.start_time,
            checks=checks,
        )

    async def get_detailed_metrics(self) -> MetricsSnapshot:
        """
        Получение детальных метрик системы.

        Кэшируется на 30 секунд для производительности.
        """
        current_time = time.time()

        if (
            self.metrics_cache
            and (current_time - self.last_metrics_update) < self.cache_ttl
        ):
            return self.metrics_cache

        # Сбор метрик
        system_metrics = self._collect_system_metrics()
        app_metrics = await self._collect_application_metrics()
        dependency_status = await self._check_all_dependencies()

        self.metrics_cache = MetricsSnapshot(
            timestamp=datetime.utcnow().isoformat(),
            system=system_metrics,
            application=app_metrics,
            dependencies=[
                DependencyStatus(**dep) for dep in dependency_status.values()
            ],
        )

        self.last_metrics_update = current_time
        return self.metrics_cache

    def _get_memory_usage(self) -> Dict[str, Any]:
        """Получение информации об использовании памяти"""
        process = psutil.Process()
        memory_info = process.memory_info()

        return {
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "percent": process.memory_percent(),
        }

    def _check_system_resources(self) -> Dict[str, Any]:
        """Проверка системных ресурсов"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()

        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_mb": memory.available / 1024 / 1024,
            "cpu_critical": cpu_percent > 95,
            "memory_critical": memory.percent > 95,
        }

    async def _check_all_dependencies(self) -> Dict[str, List[Dict]]:
        """Проверка всех зависимостей"""
        results = {}

        for dep_name, dep_config in self.dependencies.items():
            try:
                if "url" in dep_config:
                    # HTTP зависимость
                    status = await self._check_http_dependency(dep_name, dep_config)
                elif "check_function" in dep_config:
                    # Кастомная функция проверки
                    status = await dep_config["check_function"]()
                else:
                    status = {
                        "name": dep_name,
                        "status": "unknown",
                        "error": "No check method configured",
                    }

                results[dep_name] = status

            except Exception as e:
                results[dep_name] = {
                    "name": dep_name,
                    "status": "error",
                    "error": str(e),
                }

        return results

    async def _check_http_dependency(self, name: str, config: Dict) -> Dict:
        """Проверка HTTP зависимости"""
        start_time = time.time()

        try:
            timeout = aiohttp.ClientTimeout(total=config["timeout"])
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(config["url"]) as response:
                    response_time = (time.time() - start_time) * 1000

                    if response.status == 200:
                        return {
                            "name": name,
                            "status": "healthy",
                            "response_time_ms": response_time,
                            "last_check": datetime.utcnow().isoformat(),
                        }
                    else:
                        return {
                            "name": name,
                            "status": "unhealthy",
                            "response_time_ms": response_time,
                            "error": f"HTTP {response.status}",
                            "last_check": datetime.utcnow().isoformat(),
                        }

        except asyncio.TimeoutError:
            return {
                "name": name,
                "status": "unhealthy",
                "error": "Timeout",
                "last_check": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "name": name,
                "status": "error",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat(),
            }

    async def _check_sqlite(self) -> Dict:
        """Проверка SQLite базы данных"""
        import os
        import sqlite3

        db_path = self.dependencies["sqlite"]["path"]
        start_time = time.time()

        try:
            if not os.path.exists(db_path):
                return {
                    "name": "sqlite",
                    "status": "unhealthy",
                    "error": "Database file not found",
                }

            conn = sqlite3.connect(db_path, timeout=5.0)
            cursor = conn.cursor()

            # Простая проверка
            cursor.execute("SELECT 1")
            result = cursor.fetchone()

            conn.close()

            response_time = (time.time() - start_time) * 1000

            if result and result[0] == 1:
                return {
                    "name": "sqlite",
                    "status": "healthy",
                    "response_time_ms": response_time,
                    "last_check": datetime.utcnow().isoformat(),
                }
            else:
                return {
                    "name": "sqlite",
                    "status": "unhealthy",
                    "error": "Invalid response from database",
                }

        except Exception as e:
            return {"name": "sqlite", "status": "error", "error": str(e)}

    async def _check_embeddings_service(self) -> Dict:
        """Проверка сервиса эмбеддингов"""
        # В реальной системе здесь будет проверка сервиса эмбеддингов
        # Пока возвращаем mock статус
        return {
            "name": "embeddings",
            "status": "healthy",
            "response_time_ms": 50.0,
            "last_check": datetime.utcnow().isoformat(),
        }

    async def _check_request_queues(self) -> Dict[str, Any]:
        """Проверка очередей запросов"""
        # В реальной системе здесь будет проверка очередей
        # Пока возвращаем mock статус
        return {"queue_length": 0, "queue_full": False, "max_queue_size": 100}

    def _collect_system_metrics(self) -> Dict[str, Any]:
        """Сбор системных метрик"""
        return {
            "cpu": {"percent": psutil.cpu_percent(), "count": psutil.cpu_count()},
            "memory": {
                "total_mb": psutil.virtual_memory().total / 1024 / 1024,
                "available_mb": psutil.virtual_memory().available / 1024 / 1024,
                "percent": psutil.virtual_memory().percent,
            },
            "disk": {
                "total_mb": psutil.disk_usage("/").total / 1024 / 1024,
                "free_mb": psutil.disk_usage("/").free / 1024 / 1024,
                "percent": psutil.disk_usage("/").percent,
            },
            "network": {
                "bytes_sent": psutil.net_io_counters().bytes_sent,
                "bytes_recv": psutil.net_io_counters().bytes_recv,
            },
        }

    async def _collect_application_metrics(self) -> Dict[str, Any]:
        """Сбор метрик приложения"""
        # В реальной системе здесь будут метрики из оптимизаторов
        return {
            "requests_total": 0,
            "requests_per_second": 0.0,
            "average_response_time": 0.0,
            "error_rate": 0.0,
            "cache_hit_rate": 0.0,
            "active_connections": 0,
        }


# FastAPI роутер для health check эндпоинтов
health_router = APIRouter()
health_checker = HealthChecker()


@health_router.get("/health/live", response_model=HealthStatus)
async def liveness_probe():
    """Liveness probe endpoint"""
    return await health_checker.check_liveness()


@health_router.get("/health/ready", response_model=HealthStatus)
async def readiness_probe():
    """Readiness probe endpoint"""
    status = await health_checker.check_readiness()
    if status.status == "unhealthy":
        raise HTTPException(status_code=503, detail=status.dict())
    return status


@health_router.get("/health/metrics", response_model=MetricsSnapshot)
async def metrics_endpoint():
    """Detailed metrics endpoint"""
    return await health_checker.get_detailed_metrics()


@health_router.get("/health/dependencies")
async def dependencies_endpoint():
    """Dependencies status endpoint"""
    dependencies = await health_checker._check_all_dependencies()
    return {"dependencies": list(dependencies.values())}


# CLI интерфейс для локального тестирования
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Health Check CLI")
    parser.add_argument(
        "--check", choices=["live", "ready", "metrics"], default="ready"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    async def main():
        if args.check == "live":
            result = await health_checker.check_liveness()
        elif args.check == "ready":
            result = await health_checker.check_readiness()
        elif args.check == "metrics":
            result = await health_checker.get_detailed_metrics()

        if args.json:
            print(json.dumps(result.dict(), indent=2, ensure_ascii=False))
        else:
            print(f"Status: {result.status}")
            print(f"Uptime: {result.uptime_seconds:.1f}s")
            if hasattr(result, "checks"):
                print("Checks:")
                for key, value in result.checks.items():
                    print(f"  {key}: {value}")

    asyncio.run(main())
