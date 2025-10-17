"""
LLM Router Service for Unified RAG System.

This module provides intelligent routing between multiple LLM providers
to ensure zero-cost operation while maintaining quality. Implements
graceful fallback from advanced models to simpler ones.

Following the principle of "Honesty Over Performance" - we route to
the best available model but clearly indicate when we're using fallbacks.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ProviderStatus(Enum):
    """Status of an LLM provider."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""

    name: str
    api_key_env: str
    base_url: str
    model: str
    priority: int  # Lower number = higher priority
    rate_limit_per_minute: int
    timeout_seconds: int
    cost_per_token: float = 0.0  # For future paid providers


@dataclass
class ProviderState:
    """Runtime state of a provider."""

    config: ProviderConfig
    status: ProviderStatus
    last_used: Optional[datetime]
    request_count: int
    error_count: int
    consecutive_failures: int


class LLMResponse:
    """Response from LLM provider."""

    def __init__(
        self, content: str, provider: str, confidence: float, tokens_used: int = 0
    ):
        self.content = content
        self.provider = provider
        self.confidence = confidence
        self.tokens_used = tokens_used
        self.generated_at = datetime.utcnow()


class LLMRouter:
    """
    Intelligent router for LLM providers with zero-cost guarantee.

    Routes requests through free-tier providers in priority order:
    1. Gemini (Google) - Best quality, generous free tier
    2. Groq - Fast inference, good free tier
    3. OpenRouter - Access to multiple models, some free

    Implements circuit breaker pattern and automatic failover.
    """

    # Provider configurations (all free-tier)
    PROVIDERS = [
        ProviderConfig(
            name="gemini",
            api_key_env="GEMINI_API_KEY",
            base_url="https://generativelanguage.googleapis.com/v1beta",
            model="gemini-1.5-flash",
            priority=1,
            rate_limit_per_minute=15,
            timeout_seconds=30,
        ),
        ProviderConfig(
            name="groq",
            api_key_env="GROQ_API_KEY",
            base_url="https://api.groq.com/openai/v1",
            model="llama3-8b-8192",
            priority=2,
            rate_limit_per_minute=30,
            timeout_seconds=20,
        ),
        ProviderConfig(
            name="openrouter",
            api_key_env="OPENROUTER_API_KEY",
            base_url="https://openrouter.ai/api/v1",
            model="meta-llama/llama-3.1-8b-instruct:free",
            priority=3,
            rate_limit_per_minute=20,
            timeout_seconds=25,
        ),
    ]

    def __init__(self):
        self.providers: Dict[str, ProviderState] = {}
        self._initialize_providers()

        # Circuit breaker settings
        self.failure_threshold = 3
        self.recovery_timeout = timedelta(minutes=5)
        self.max_consecutive_failures = 5

    def _initialize_providers(self):
        """Initialize provider states."""
        for config in self.PROVIDERS:
            self.providers[config.name] = ProviderState(
                config=config,
                status=ProviderStatus.HEALTHY,
                last_used=None,
                request_count=0,
                error_count=0,
                consecutive_failures=0,
            )

    async def generate_response(
        self, prompt: str, context: Optional[List[str]] = None
    ) -> LLMResponse:
        """
        Generate response using best available provider.

        Args:
            prompt: The question or prompt to answer
            context: Optional context documents/snippets

        Returns:
            LLMResponse with content and metadata
        """
        # Build full prompt with context
        full_prompt = self._build_prompt(prompt, context)

        # Try providers in priority order
        for provider_name in self._get_provider_priority():
            provider = self.providers[provider_name]

            if provider.status == ProviderStatus.FAILED:
                # Check if we should attempt recovery
                if not self._should_attempt_recovery(provider):
                    continue

            try:
                response = await self._call_provider(provider, full_prompt)

                # Success - update state
                self._record_success(provider)
                return response

            except Exception as e:
                logger.warning(f"Provider {provider_name} failed: {e}")
                self._record_failure(provider)

                # Continue to next provider
                continue

        # All providers failed - return minimal response
        return LLMResponse(
            content="Извините, все LLM провайдеры временно недоступны. Попробуйте позже или используйте поиск без генерации ответа.",
            provider="fallback",
            confidence=0.0,
        )

    def _get_provider_priority(self) -> List[str]:
        """Get providers sorted by priority (healthy first, then by config priority)."""
        healthy_providers = [
            name
            for name, state in self.providers.items()
            if state.status in [ProviderStatus.HEALTHY, ProviderStatus.DEGRADED]
        ]

        # Sort by priority (lower number = higher priority)
        return sorted(
            healthy_providers, key=lambda x: self.providers[x].config.priority
        )

    def _build_prompt(self, prompt: str, context: Optional[List[str]]) -> str:
        """Build the full prompt with context."""
        if not context:
            return prompt

        # Limit context to prevent token overflow
        context_text = "\n\n".join(context[:5])  # Max 5 context items

        return f"""Используйте предоставленный контекст для ответа на вопрос. Если контекст не релевантен, ответьте на основе ваших знаний.

Контекст:
{context_text}

Вопрос: {prompt}

Ответ:"""

    async def _call_provider(self, provider: ProviderState, prompt: str) -> LLMResponse:
        """Call a specific provider (placeholder implementation)."""
        # This is a placeholder - in real implementation, this would make actual API calls
        # For now, simulate different response qualities based on provider

        await asyncio.sleep(0.1)  # Simulate network delay

        if provider.config.name == "gemini":
            content = f"Ответ от Gemini: {prompt[:50]}..."
            confidence = 0.9
        elif provider.config.name == "groq":
            content = f"Ответ от Groq: {prompt[:50]}..."
            confidence = 0.8
        else:  # openrouter
            content = f"Ответ от OpenRouter: {prompt[:50]}..."
            confidence = 0.7

        return LLMResponse(
            content=content,
            provider=provider.config.name,
            confidence=confidence,
            tokens_used=len(prompt.split()) * 2,  # Rough estimate
        )

    def _record_success(self, provider: ProviderState):
        """Record successful provider call."""
        provider.status = ProviderStatus.HEALTHY
        provider.last_used = datetime.utcnow()
        provider.request_count += 1
        provider.consecutive_failures = 0

    def _record_failure(self, provider: ProviderState):
        """Record failed provider call."""
        provider.error_count += 1
        provider.consecutive_failures += 1

        if provider.consecutive_failures >= self.max_consecutive_failures:
            provider.status = ProviderStatus.FAILED
            logger.error(
                f"Provider {provider.config.name} marked as FAILED after {provider.consecutive_failures} failures"
            )
        elif provider.consecutive_failures >= self.failure_threshold:
            provider.status = ProviderStatus.DEGRADED
            logger.warning(f"Provider {provider.config.name} marked as DEGRADED")

    def _should_attempt_recovery(self, provider: ProviderState) -> bool:
        """Check if we should attempt to recover a failed provider."""
        if provider.status != ProviderStatus.FAILED:
            return True

        if not provider.last_used:
            return True

        time_since_last_use = datetime.utcnow() - provider.last_used
        return time_since_last_use > self.recovery_timeout

    def get_provider_stats(self) -> Dict[str, Any]:
        """Get statistics about provider performance."""
        return {
            provider_name: {
                "status": state.status.value,
                "request_count": state.request_count,
                "error_count": state.error_count,
                "success_rate": (
                    (state.request_count - state.error_count) / state.request_count
                    if state.request_count > 0
                    else 0
                ),
                "last_used": state.last_used.isoformat() if state.last_used else None,
            }
            for provider_name, state in self.providers.items()
        }


# Global router instance
llm_router = LLMRouter()
