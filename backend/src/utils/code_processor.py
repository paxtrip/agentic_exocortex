"""
Code processing utilities for User Story 2.

This module handles detection, extraction, and formatting of code snippets
from markdown documents. It supports multiple programming languages and
provides confidence scoring for detected code blocks.

Key features:
- Markdown code block extraction with language detection
- Automatic language identification for code without explicit language tags
- Code formatting and normalization
- Confidence scoring for detection accuracy
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ProgrammingLanguage(Enum):
    """Supported programming languages."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CSHARP = "csharp"
    CPP = "cpp"
    C = "c"
    GO = "go"
    RUST = "rust"
    PHP = "php"
    RUBY = "ruby"
    SQL = "sql"
    BASH = "bash"
    POWERSHELL = "powershell"
    YAML = "yaml"
    JSON = "json"
    XML = "xml"
    HTML = "html"
    CSS = "css"
    UNKNOWN = "unknown"


@dataclass
class CodeBlock:
    """Represents a detected code block."""

    code: str
    language: ProgrammingLanguage
    confidence: float
    line_start: int
    line_end: int
    has_explicit_lang: bool


class CodeProcessor:
    """
    Processes documents to extract and format code snippets.

    This class handles the detection of code blocks in markdown text,
    language identification, and formatting for storage and search.
    """

    # Language detection patterns
    LANGUAGE_PATTERNS = {
        ProgrammingLanguage.PYTHON: [
            r"\bdef\s+\w+\s*\(",
            r"\bclass\s+\w+",
            r"\bimport\s+\w+",
            r"\bfrom\s+\w+\s+import",
            r'\bif\s+__name__\s*==\s*[\'""]__main__[\'""]',
            r"\bprint\s*\(",
            r"\blet\s+\w+\s*=",
            r"\bfor\s+\w+\s+in\s+range",
            r"\blen\s*\(",
        ],
        ProgrammingLanguage.JAVASCRIPT: [
            r"\bfunction\s+\w+\s*\(",
            r"\bconst\s+\w+\s*=",
            r"\blet\s+\w+\s*=",
            r"\bvar\s+\w+\s*=",
            r"\bconsole\.log\s*\(",
            r"\bdocument\.getElementById\s*\(",
            r"\basync\s+function",
            r"\bawait\s+\w+",
        ],
        ProgrammingLanguage.SQL: [
            r"\bSELECT\s+",
            r"\bINSERT\s+INTO",
            r"\bUPDATE\s+",
            r"\bDELETE\s+FROM",
            r"\bCREATE\s+TABLE",
            r"\bALTER\s+TABLE",
            r"\bDROP\s+TABLE",
            r"\bWHERE\s+",
            r"\bJOIN\s+",
            r"\bGROUP\s+BY",
            r"\bORDER\s+BY",
        ],
        ProgrammingLanguage.BASH: [
            r"\b#!/bin/bash",
            r"\b#!/bin/sh",
            r"\becho\s+",
            r"\bexport\s+\w+=",
            r"\bif\s+\[",
            r"\bfor\s+\w+\s+in",
            r"\bwhile\s+",
        ],
        ProgrammingLanguage.HTML: [
            r"<!DOCTYPE\s+html>",
            r"<html>",
            r"<head>",
            r"<body>",
            r"<div>",
            r"<span>",
            r"<p>",
        ],
        ProgrammingLanguage.CSS: [
            r"\{\s*[\w-]+\s*:",
            r"\.[\w-]+\s*\{",
            r"#[\w-]+\s*\{",
            r"@media",
            r"@import",
        ],
        ProgrammingLanguage.JSON: [
            r'^\s*\{\s*"',
            r"^\s*\[\s*\{",
            r'"\w+"\s*:',
        ],
        ProgrammingLanguage.YAML: [
            r"^\s*[\w-]+\s*:",
            r"^\s*-\s+\w+",
            r'version\s*:\s*[\'"0-9]',
        ],
    }

    # Language aliases for markdown code blocks
    LANGUAGE_ALIASES = {
        "py": ProgrammingLanguage.PYTHON,
        "python": ProgrammingLanguage.PYTHON,
        "js": ProgrammingLanguage.JAVASCRIPT,
        "javascript": ProgrammingLanguage.JAVASCRIPT,
        "ts": ProgrammingLanguage.TYPESCRIPT,
        "typescript": ProgrammingLanguage.TYPESCRIPT,
        "java": ProgrammingLanguage.JAVA,
        "c#": ProgrammingLanguage.CSHARP,
        "csharp": ProgrammingLanguage.CSHARP,
        "cpp": ProgrammingLanguage.CPP,
        "cxx": ProgrammingLanguage.CPP,
        "cc": ProgrammingLanguage.CPP,
        "c": ProgrammingLanguage.C,
        "go": ProgrammingLanguage.GO,
        "golang": ProgrammingLanguage.GO,
        "rs": ProgrammingLanguage.RUST,
        "rust": ProgrammingLanguage.RUST,
        "php": ProgrammingLanguage.PHP,
        "rb": ProgrammingLanguage.RUBY,
        "ruby": ProgrammingLanguage.RUBY,
        "sql": ProgrammingLanguage.SQL,
        "sh": ProgrammingLanguage.BASH,
        "shell": ProgrammingLanguage.BASH,
        "bash": ProgrammingLanguage.BASH,
        "ps1": ProgrammingLanguage.POWERSHELL,
        "powershell": ProgrammingLanguage.POWERSHELL,
        "yml": ProgrammingLanguage.YAML,
        "yaml": ProgrammingLanguage.YAML,
        "xml": ProgrammingLanguage.XML,
        "htm": ProgrammingLanguage.HTML,
        "html": ProgrammingLanguage.HTML,
    }

    @classmethod
    def extract_code_snippets(
        cls, doc_id: str, markdown_text: str
    ) -> List[Dict[str, Any]]:
        """
        Extract code snippets from markdown text.

        Args:
            doc_id: Document identifier
            markdown_text: Markdown content to process

        Returns:
            List of code snippet dictionaries ready for storage
        """
        code_blocks = cls._extract_markdown_code_blocks(markdown_text)

        snippets = []
        for i, block in enumerate(code_blocks):
            # Generate unique ID for this snippet
            snippet_id = f"{doc_id}_code_{i+1}"

            # Extract title from surrounding context
            title = cls._extract_title_near_code(markdown_text, block.line_start)

            # Generate tags based on code content
            tags = cls._generate_tags(block.code, block.language)

            # Calculate confidence
            confidence = cls._calculate_confidence(block)

            snippet = {
                "id": snippet_id,
                "doc_id": doc_id,
                "language": block.language.value,
                "code": block.code.strip(),
                "title": title,
                "tags": tags,
                "confidence": confidence,
                "line_start": block.line_start,
                "line_end": block.line_end,
                "created_at": cls._get_current_timestamp(),
            }
            snippets.append(snippet)

        return snippets

    @classmethod
    def _extract_markdown_code_blocks(cls, text: str) -> List[CodeBlock]:
        """
        Extract code blocks from markdown text.

        Supports both fenced code blocks (```) and indented code blocks.
        """
        blocks = []

        # Split text into lines for line number tracking
        lines = text.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]

            # Check for fenced code blocks
            if line.strip().startswith("```"):
                block = cls._parse_fenced_code_block(lines, i)
                if block:
                    blocks.append(block)
                    i = block.line_end + 1  # Skip the closing fence
                else:
                    i += 1
            else:
                i += 1

        return blocks

    @classmethod
    def _parse_fenced_code_block(
        cls, lines: List[str], start_idx: int
    ) -> Optional[CodeBlock]:
        """Parse a fenced code block starting at the given line."""
        start_line = lines[start_idx]

        # Extract language from opening fence
        lang_match = re.match(r"```\s*(\w+)?", start_line)
        explicit_lang = (
            lang_match.group(1) if lang_match and lang_match.group(1) else None
        )

        # Map language alias to enum
        language = ProgrammingLanguage.UNKNOWN
        has_explicit_lang = False

        if explicit_lang:
            language = cls.LANGUAGE_ALIASES.get(
                explicit_lang.lower(), ProgrammingLanguage.UNKNOWN
            )
            has_explicit_lang = language != ProgrammingLanguage.UNKNOWN

        # Find the closing fence
        code_lines = []
        end_idx = start_idx + 1

        while end_idx < len(lines):
            if lines[end_idx].strip().startswith("```"):
                break
            code_lines.append(lines[end_idx])
            end_idx += 1

        if end_idx >= len(lines):
            # No closing fence found
            return None

        code = "\n".join(code_lines)

        # If no explicit language, try to detect it
        if not has_explicit_lang:
            detected_lang = cls._detect_language(code)
            if detected_lang != ProgrammingLanguage.UNKNOWN:
                language = detected_lang
                has_explicit_lang = False
            else:
                # Fallback to bash for code that looks like shell scripts
                language = ProgrammingLanguage.BASH
                has_explicit_lang = False

        return CodeBlock(
            code=code,
            language=language,
            confidence=(
                0.9 if has_explicit_lang else 0.7
            ),  # Explicit lang is more confident
            line_start=start_idx + 1,  # Code starts on line after opening fence
            line_end=end_idx,
            has_explicit_lang=has_explicit_lang,
        )

    @classmethod
    def _detect_language(cls, code: str) -> ProgrammingLanguage:
        """
        Detect programming language from code content.

        Uses pattern matching to identify the most likely language.
        """
        if not code.strip():
            return ProgrammingLanguage.UNKNOWN

        scores = {}

        for lang, patterns in cls.LANGUAGE_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, code, re.IGNORECASE | re.MULTILINE))
                score += matches

            if score > 0:
                scores[lang] = score

        if not scores:
            return ProgrammingLanguage.UNKNOWN

        # Return language with highest score
        return max(scores, key=scores.get)

    @classmethod
    def _extract_title_near_code(cls, text: str, code_line_start: int) -> str:
        """Extract a title from text near the code block."""
        lines = text.split("\n")

        # Look backwards for headers (but not too far)
        for i in range(code_line_start - 1, max(-1, code_line_start - 3), -1):
            line = lines[i].strip()
            if line.startswith("#"):
                # Remove # symbols and clean up
                title = re.sub(r"^#+\s*", "", line)
                return title.strip()

        # Look for any descriptive text before the code (closer proximity)
        for i in range(code_line_start - 1, max(-1, code_line_start - 2), -1):
            line = lines[i].strip()
            if line and not line.startswith("```") and len(line) > 5:
                # Use first sentence or truncate
                sentence = line.split(".")[0]
                return sentence.strip()[:100]

        return "Code snippet"

    @classmethod
    def _generate_tags(cls, code: str, language: ProgrammingLanguage) -> List[str]:
        """Generate relevant tags for the code snippet."""
        tags = [language.value]

        # Language-specific tag generation
        if language == ProgrammingLanguage.PYTHON:
            if "def " in code:
                tags.append("function")
            if "class " in code:
                tags.append("class")
            if "import " in code or "from " in code:
                tags.append("import")
            if "async def" in code:
                tags.append("async")

        elif language == ProgrammingLanguage.JAVASCRIPT:
            if "function" in code or "=>" in code:
                tags.append("function")
            if "async" in code or "await" in code:
                tags.append("async")
            if "class " in code:
                tags.append("class")
            if "const " in code or "let " in code:
                tags.append("variable")

        elif language == ProgrammingLanguage.SQL:
            if "SELECT" in code.upper():
                tags.append("query")
            if "INSERT" in code.upper():
                tags.append("insert")
            if "UPDATE" in code.upper():
                tags.append("update")
            if "DELETE" in code.upper():
                tags.append("delete")
            if "JOIN" in code.upper():
                tags.append("join")

        # Common programming concepts
        code_lower = code.lower()
        if any(
            keyword in code_lower for keyword in ["sort", "search", "find", "filter"]
        ):
            tags.append("algorithm")
        if any(
            keyword in code_lower for keyword in ["http", "api", "request", "response"]
        ):
            tags.append("api")
        if any(keyword in code_lower for keyword in ["file", "read", "write", "open"]):
            tags.append("file-io")
        if any(keyword in code_lower for keyword in ["test", "assert", "expect"]):
            tags.append("testing")

        return list(set(tags))  # Remove duplicates

    @classmethod
    def _calculate_confidence(cls, block: CodeBlock) -> float:
        """Calculate confidence score for code detection."""
        base_confidence = block.confidence

        # Adjust based on code characteristics
        code = block.code.strip()

        if not code:
            return 0.0

        # Longer code is generally more confident
        length_bonus = min(0.2, len(code) / 1000)  # Up to 0.2 bonus for long code

        # Multiple lines are more confident than single lines
        lines = code.count("\n") + 1
        multiline_bonus = min(0.1, lines / 10)  # Up to 0.1 bonus for many lines

        # Explicit language declaration is very confident
        explicit_bonus = 0.2 if block.has_explicit_lang else 0.0

        confidence = base_confidence + length_bonus + multiline_bonus + explicit_bonus
        return min(1.0, confidence)

    @staticmethod
    def _get_current_timestamp() -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()


# Convenience functions for the API
async def extract_code_snippets(
    doc_id: str, markdown_text: str
) -> List[Dict[str, Any]]:
    """
    Extract code snippets from markdown text.

    This is the main API function for code extraction.
    """
    return CodeProcessor.extract_code_snippets(doc_id, markdown_text)


async def detect_language(code: str) -> str:
    """
    Detect the programming language of a code snippet.

    Returns the language name as a string.
    """
    language = CodeProcessor._detect_language(code)
    return language.value
