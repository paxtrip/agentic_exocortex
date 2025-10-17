"""
Circuit Breaker Pattern Implementation for Unified RAG System.

This module provides circuit breaker functionality to handle failures
gracefully in external service calls (LLM providers, databases, etc.).

Following the principle of "Graceful Degradation" - when services fail,
we isolate them temporarily to prevent cascading failures while allowing
automatic recovery when services become healthy again.
"""

import asyncio
import functools
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """States of the circuit breaker."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 5  # Failures before opening
    recovery_timeout: float = 60.0  # Seconds to wait before trying recovery
    success_threshold: int = 3  # Successes needed to close circuit
    timeout: float = 30.0  # Request timeout in seconds
    name: str = "default"  # Identifier for logging


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker performance."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state_changes: int = 0


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""

    pass


class CircuitBreaker:
    """
    Circuit breaker implementation with configurable thresholds.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failing service isolated, requests fail fast
    - HALF_OPEN: Testing if service recovered, limited requests allowed

    Automatic recovery: After timeout, allows limited test requests.
    """

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.

        Args:
            func: Async function to call
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenException: If circuit is open
        """
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if not self._should_attempt_recovery():
                    raise CircuitBreakerOpenException(
                        f"Circuit breaker '{self.config.name}' is OPEN"
                    )
                # Transition to half-open for testing
                self._change_state(CircuitState.HALF_OPEN)

            if self.state == CircuitState.HALF_OPEN:
                # In half-open, we allow the call but watch closely
                pass

        # Execute the call with timeout
        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs), timeout=self.config.timeout
            )
            await self._record_success()
            return result

        except asyncio.TimeoutError:
            await self._record_failure()
            raise
        except Exception as e:
            await self._record_failure()
            raise

    async def _record_success(self):
        """Record successful call."""
        async with self._lock:
            self.stats.total_requests += 1
            self.stats.successful_requests += 1
            self.stats.consecutive_successes += 1
            self.stats.consecutive_failures = 0
            self.stats.last_success_time = datetime.utcnow()

            if self.state == CircuitState.HALF_OPEN:
                if self.stats.consecutive_successes >= self.config.success_threshold:
                    self._change_state(CircuitState.CLOSED)
                    logger.info(
                        f"Circuit breaker '{self.config.name}' recovered and CLOSED"
                    )

    async def _record_failure(self):
        """Record failed call."""
        async with self._lock:
            self.stats.total_requests += 1
            self.stats.failed_requests += 1
            self.stats.consecutive_failures += 1
            self.stats.consecutive_successes = 0
            self.stats.last_failure_time = datetime.utcnow()

            if self.state == CircuitState.CLOSED:
                if self.stats.consecutive_failures >= self.config.failure_threshold:
                    self._change_state(CircuitState.OPEN)
                    logger.warning(
                        f"Circuit breaker '{self.config.name}' OPENED after "
                        f"{self.stats.consecutive_failures} consecutive failures"
                    )
            elif self.state == CircuitState.HALF_OPEN:
                # Any failure in half-open immediately opens circuit
                self._change_state(CircuitState.OPEN)
                logger.warning(
                    f"Circuit breaker '{self.config.name}' failed recovery test, OPEN"
                )

    def _should_attempt_recovery(self) -> bool:
        """Check if we should attempt recovery from open state."""
        if self.state != CircuitState.OPEN:
            return False

        if not self.stats.last_failure_time:
            return True

        time_since_failure = datetime.utcnow() - self.stats.last_failure_time
        return time_since_failure.total_seconds() >= self.config.recovery_timeout

    def _change_state(self, new_state: CircuitState):
        """Change circuit breaker state."""
        old_state = self.state
        self.state = new_state
        self.stats.state_changes += 1

        if old_state != new_state:
            logger.info(
                f"Circuit breaker '{self.config.name}' state: {old_state.value} -> {new_state.value}"
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        success_rate = (
            self.stats.successful_requests / self.stats.total_requests
            if self.stats.total_requests > 0
            else 0
        )

        return {
            "name": self.config.name,
            "state": self.state.value,
            "total_requests": self.stats.total_requests,
            "successful_requests": self.stats.successful_requests,
            "failed_requests": self.stats.failed_requests,
            "success_rate": round(success_rate, 3),
            "consecutive_failures": self.stats.consecutive_failures,
            "consecutive_successes": self.stats.consecutive_successes,
            "last_failure_time": (
                self.stats.last_failure_time.isoformat()
                if self.stats.last_failure_time
                else None
            ),
            "last_success_time": (
                self.stats.last_success_time.isoformat()
                if self.stats.last_success_time
                else None
            ),
            "state_changes": self.stats.state_changes,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout,
            },
        }

    def reset(self):
        """Reset circuit breaker to initial state."""
        async with self._lock:
            self.state = CircuitState.CLOSED
            self.stats = CircuitBreakerStats()
            logger.info(f"Circuit breaker '{self.config.name}' reset")


def circuit_breaker(config: CircuitBreakerConfig):
    """
    Decorator to apply circuit breaker to async functions.

    Usage:
        @circuit_breaker(CircuitBreakerConfig(name="llm_api", failure_threshold=3))
        async def call_llm_api(prompt: str) -> str:
            # API call implementation
            pass
    """

    def decorator(func: Callable) -> Callable:
        breaker = CircuitBreaker(config)

        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            return await breaker.call(func, *args, **kwargs)

        # Attach breaker to function for inspection
        wrapper.circuit_breaker = breaker
        return wrapper

    return decorator


# Pre-configured circuit breakers for common services
llm_circuit_breaker = CircuitBreaker(
    CircuitBreakerConfig(
        name="llm_providers",
        failure_threshold=3,
        recovery_timeout=300.0,  # 5 minutes
        success_threshold=2,
        timeout=30.0,
    )
)

qdrant_circuit_breaker = CircuitBreaker(
    CircuitBreakerConfig(
        name="qdrant_db",
        failure_threshold=5,
        recovery_timeout=60.0,  # 1 minute
        success_threshold=3,
        timeout=10.0,
    )
)

siyuan_circuit_breaker = CircuitBreaker(
    CircuitBreakerConfig(
        name="siyuan_api",
        failure_threshold=3,
        recovery_timeout=120.0,  # 2 minutes
        success_threshold=2,
        timeout=15.0,
    )
)
