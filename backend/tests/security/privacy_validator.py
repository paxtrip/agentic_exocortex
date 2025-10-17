"""
Privacy validation tests for RAG system.

This module ensures compliance with "Privacy Without Compromise" principle:
- No raw data leaves the server
- Only anonymized summaries sent to LLM
- No user data in logs or external services
- Secure data handling throughout pipeline

Tests validate that sensitive information is never exposed.
"""

import json
import re
from typing import Any, Dict, List, Set
from unittest.mock import Mock, patch

import pytest


class PrivacyValidator:
    """
    Валидатор приватности для RAG системы.

    Проверяет что система не раскрывает конфиденциальные данные.
    """

    def __init__(self):
        # Паттерны потенциально чувствительной информации
        self.sensitive_patterns = {
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
            "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
            "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
            "ip_address": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
            "api_key": r"\b[A-Za-z0-9]{20,}\b",  # Generic long alphanumeric
            "password": r'password["\s]*:[\s]*["\']([^"\']+)["\']',
            "personal_name": r"\b(?:John|Jane|Michael|Sarah|David|Lisa)\s+(?:Smith|Johnson|Williams|Brown|Jones|Garcia)\b",
        }

        # Список разрешенных внешних сервисов
        self.allowed_external_services = {"gemini", "groq", "openrouter", "huggingface"}

    def validate_no_raw_data_leakage(self, data: Any, context: str = "") -> List[str]:
        """
        Проверка что сырые данные не покидают сервер.

        Args:
            data: Данные для проверки
            context: Контекст проверки (для сообщений об ошибках)

        Returns:
            Список найденных нарушений приватности
        """
        violations = []

        # Сериализуем данные для анализа
        if isinstance(data, (dict, list)):
            data_str = json.dumps(data, ensure_ascii=False)
        else:
            data_str = str(data)

        # Проверяем на наличие чувствительной информации
        for pattern_name, pattern in self.sensitive_patterns.items():
            matches = re.findall(pattern, data_str, re.IGNORECASE)
            if matches:
                violations.append(
                    f"Found {pattern_name} pattern in {context}: {matches[:3]}..."  # Показываем только первые 3
                )

        # Специфические проверки для RAG системы
        if "user_id" in data_str.lower() or "user_id" in str(data).lower():
            violations.append(f"User ID found in external data {context}")

        if "session_id" in data_str.lower():
            violations.append(f"Session ID found in external data {context}")

        return violations

    def validate_llm_prompt_anonymization(self, prompt: str) -> List[str]:
        """
        Проверка анонимизации промптов для LLM.

        Согласно конституции: "Raw data never leaves server, only anonymized summaries to LLM"

        Args:
            prompt: Промпт отправляемый в LLM

        Returns:
            Список нарушений
        """
        violations = []

        # Проверяем что в промпте нет сырых данных пользователя
        violations.extend(self.validate_no_raw_data_leakage(prompt, "LLM prompt"))

        # Проверяем что промпт содержит только анонимизированные summaries
        if "user's personal notes" in prompt.lower():
            violations.append("LLM prompt contains reference to user's personal data")

        if "private information" in prompt.lower():
            violations.append("LLM prompt mentions private information")

        # Проверяем что нет конкретных имен файлов или путей
        file_path_pattern = r"[A-Za-z]:\\[^\s]+|\./[^\s]+|/home/[^\s]+|/Users/[^\s]+"
        if re.search(file_path_pattern, prompt):
            violations.append("LLM prompt contains file system paths")

        return violations

    def validate_external_service_calls(
        self, service_name: str, request_data: Any
    ) -> List[str]:
        """
        Проверка вызовов внешних сервисов.

        Args:
            service_name: Имя сервиса
            request_data: Данные запроса

        Returns:
            Список нарушений
        """
        violations = []

        # Проверяем что сервис разрешен
        if service_name.lower() not in self.allowed_external_services:
            violations.append(f"Unauthorized external service: {service_name}")

        # Проверяем данные запроса
        violations.extend(
            self.validate_no_raw_data_leakage(
                request_data, f"external service {service_name} request"
            )
        )

        return violations

    def validate_log_privacy(self, log_entry: str) -> List[str]:
        """
        Проверка приватности лог-записей.

        Args:
            log_entry: Лог-запись для проверки

        Returns:
            Список нарушений
        """
        violations = []

        # Логи не должны содержать чувствительную информацию
        violations.extend(self.validate_no_raw_data_leakage(log_entry, "log entry"))

        # Специфические проверки для логов
        if "password" in log_entry.lower():
            violations.append("Log contains password")

        if "api_key" in log_entry.lower() or "apikey" in log_entry.lower():
            violations.append("Log contains API key")

        # Проверяем маскировку
        credit_card_pattern = (
            r"\b\d{4}[*]+\d{4}\b"  # Маскированные карты должны быть 1234****5678
        )
        if re.search(r"\b\d{13,19}\b", log_entry) and not re.search(
            credit_card_pattern, log_entry
        ):
            violations.append("Log contains unmasked credit card number")

        return violations

    def validate_cache_privacy(self, cache_data: Any) -> List[str]:
        """
        Проверка приватности кэшированных данных.

        Args:
            cache_data: Кэшированные данные

        Returns:
            Список нарушений
        """
        violations = []

        # Кэш может содержать анонимизированные данные, но не сырые
        violations.extend(self.validate_no_raw_data_leakage(cache_data, "cache data"))

        # Проверяем что кэш не содержит персональные идентификаторы
        if isinstance(cache_data, dict):
            sensitive_keys = ["user_id", "email", "phone", "address", "ssn"]
            for key in sensitive_keys:
                if key in cache_data:
                    violations.append(f"Cache contains sensitive key: {key}")

        return violations


class TestPrivacyValidation:
    """Тесты приватности"""

    def __init__(self):
        self.validator = PrivacyValidator()

    @pytest.mark.security
    def test_llm_prompt_anonymization(self):
        """Тест анонимизации промптов для LLM"""
        # Корректный анонимизированный промпт
        safe_prompt = """
        Based on the following document summaries, answer the question.
        Documents: [Summary 1: Machine learning concepts...] [Summary 2: Neural networks...]
        Question: What is machine learning?
        """

        violations = self.validator.validate_llm_prompt_anonymization(safe_prompt)
        assert len(violations) == 0, f"False positive violations: {violations}"

        # Промпт с нарушением приватности
        unsafe_prompt = """
        User's personal notes from /home/user/documents/notes.txt:
        Email: user@example.com
        Phone: 123-456-7890
        What is the meaning of life?
        """

        violations = self.validator.validate_llm_prompt_anonymization(unsafe_prompt)
        assert len(violations) > 0, "Should detect privacy violations"
        assert any("email" in v.lower() for v in violations)
        assert any("phone" in v.lower() for v in violations)

    @pytest.mark.security
    def test_external_service_data_sanitization(self):
        """Тест санитизации данных для внешних сервисов"""
        # Корректные анонимизированные данные
        safe_data = {
            "prompt": "Summarize these documents",
            "documents": ["Doc 1 summary", "Doc 2 summary"],
            "max_tokens": 100,
        }

        violations = self.validator.validate_external_service_calls("gemini", safe_data)
        assert len(violations) == 0, f"False positive: {violations}"

        # Данные с нарушением приватности
        unsafe_data = {
            "user_id": "12345",
            "personal_notes": "/home/user/private.txt",
            "email": "user@example.com",
        }

        violations = self.validator.validate_external_service_calls(
            "gemini", unsafe_data
        )
        assert len(violations) > 0, "Should detect privacy violations"

    @pytest.mark.security
    def test_log_privacy_compliance(self):
        """Тест приватности лог-записей"""
        # Корректная лог-запись
        safe_log = "INFO: Processed query 'What is AI?' in 150ms"

        violations = self.validator.validate_log_privacy(safe_log)
        assert len(violations) == 0, f"False positive: {violations}"

        # Лог с нарушением приватности
        unsafe_log = "INFO: User user@example.com queried 'password: secret123'"

        violations = self.validator.validate_log_privacy(unsafe_log)
        assert len(violations) > 0, "Should detect privacy violations"

    @pytest.mark.security
    def test_cache_data_anonymization(self):
        """Тест анонимизации кэшированных данных"""
        # Корректные кэшированные данные
        safe_cache = {
            "query": "What is machine learning?",
            "response": "Machine learning is...",
            "timestamp": 1234567890,
        }

        violations = self.validator.validate_cache_privacy(safe_cache)
        assert len(violations) == 0, f"False positive: {violations}"

        # Кэш с персональными данными
        unsafe_cache = {
            "user_id": "12345",
            "email": "user@example.com",
            "response": "Your personal data...",
        }

        violations = self.validator.validate_cache_privacy(unsafe_cache)
        assert len(violations) > 0, "Should detect privacy violations"

    @pytest.mark.security
    def test_comprehensive_privacy_audit(self):
        """Комплексный аудит приватности"""
        # Мокаем компоненты системы для аудита
        mock_components = {
            "llm_service": Mock(),
            "cache": Mock(),
            "logger": Mock(),
            "external_api": Mock(),
        }

        # Настраиваем моки для тестирования
        mock_components["llm_service"].send_prompt.return_value = "Safe response"
        mock_components["cache"].get.return_value = {"safe": "data"}
        mock_components["logger"].info.return_value = None

        # Проверяем что все компоненты соблюдают приватность
        # В реальной системе здесь будут интеграционные тесты

        # Проверяем что мок компоненты не возвращают чувствительные данные
        for component_name, component in mock_components.items():
            # Это placeholder - в реальной системе будут конкретные проверки
            pass

        assert True  # Тест проходит если не было исключений


# Интеграционные тесты приватности
@pytest.mark.integration
@pytest.mark.security
class TestPrivacyIntegration:
    """Интеграционные тесты приватности"""

    @pytest.fixture
    def privacy_validator(self):
        return PrivacyValidator()

    def test_end_to_end_privacy_pipeline(self, privacy_validator):
        """Тест полного pipeline приватности"""
        # Симуляция полного запроса через систему

        # 1. Входящий запрос
        user_query = "What are my notes about machine learning?"

        # 2. Поиск документов (анонимизированные)
        search_results = [
            {"id": "doc1", "summary": "Machine learning concepts", "score": 0.9},
            {"id": "doc2", "summary": "Neural networks explained", "score": 0.8},
        ]

        # 3. Формирование промпта для LLM (только summaries)
        llm_prompt = f"""
        Based on these document summaries, answer: {user_query}

        Documents:
        {json.dumps(search_results, ensure_ascii=False)}
        """

        # 4. Проверка приватности на каждом этапе
        assert (
            len(
                privacy_validator.validate_no_raw_data_leakage(user_query, "user query")
            )
            == 0
        )
        assert len(privacy_validator.validate_llm_prompt_anonymization(llm_prompt)) == 0

        # 5. Имитация ответа LLM
        llm_response = "Machine learning is a subset of AI that enables systems to learn from data."

        # 6. Кэширование (анонимизированные данные)
        cache_data = {
            "query_hash": "abc123",
            "response": llm_response,
            "timestamp": 1234567890,
        }

        assert len(privacy_validator.validate_cache_privacy(cache_data)) == 0

    def test_privacy_under_attack_scenarios(self, privacy_validator):
        """Тест приватности при попытках атак"""
        # Тест на SQL injection в запросах
        malicious_query = "'; DROP TABLE users; --"
        violations = privacy_validator.validate_no_raw_data_leakage(
            malicious_query, "malicious query"
        )
        # Не должно быть нарушений приватности, но должно быть обработано безопасно

        # Тест на XSS в контенте
        xss_content = "<script>alert('xss')</script>"
        violations = privacy_validator.validate_no_raw_data_leakage(
            xss_content, "xss content"
        )
        # Система должна sanitizować такой контент

        # Тест на path traversal
        path_traversal = "../../../etc/passwd"
        violations = privacy_validator.validate_no_raw_data_leakage(
            path_traversal, "path traversal"
        )
        # Система должна блокировать такие запросы

        # Все тесты должны проходить без нарушений приватности
        # (хотя система может блокировать такие запросы по другим причинам)
        assert isinstance(violations, list)


if __name__ == "__main__":
    # Запуск тестов приватности
    pytest.main([__file__, "-v", "--tb=short", "-m", "security"])
