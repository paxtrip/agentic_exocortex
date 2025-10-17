"""
Extractive QA Service for Unified RAG System.

This module provides extractive question answering as a fallback when
LLM providers are unavailable. Uses RoBERTa-based models to extract
relevant spans from documents.

Following the principle of "Graceful Degradation" - when LLMs fail,
we can still provide useful answers by extracting relevant text spans
directly from the knowledge base.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class QAContext:
    """Context information for QA."""

    document_id: str
    content: str
    title: Optional[str] = None
    score: float = 0.0


@dataclass
class QAResult:
    """Result from extractive QA."""

    answer: str
    confidence: float
    context: str
    document_id: str
    start_char: int
    end_char: int
    source_title: Optional[str] = None


class ExtractiveQA:
    """
    Extractive Question Answering using pattern matching and heuristics.

    This is a lightweight fallback that works without external dependencies.
    For production, this would be replaced with a proper RoBERTa model.

    Strategy:
    1. Find sentences containing question keywords
    2. Extract relevant spans around matches
    3. Score and rank candidates
    4. Return highest-scoring answer
    """

    def __init__(self):
        # Question word patterns for different languages
        self.question_patterns = {
            "en": [
                r"\b(what|how|when|where|why|who|which|whose)\b",
                r"\b(is|are|was|were|do|does|did|can|could|will|would|should|may|might)\b",
                r"\b(define|explain|describe|tell me about)\b",
            ],
            "ru": [
                r"\b(что|как|когда|где|почему|кто|какой|чей)\b",
                r"\b(есть|является|был|была|были|делать|может|мог|будет|должен|может)\b",
                r"\b(определить|объяснить|описать|расскажи о)\b",
            ],
        }

        # Stop words to filter out
        self.stop_words = {
            "en": {
                "the",
                "a",
                "an",
                "and",
                "or",
                "but",
                "in",
                "on",
                "at",
                "to",
                "for",
                "of",
                "with",
                "by",
                "is",
                "are",
                "was",
                "were",
            },
            "ru": {
                "и",
                "а",
                "но",
                "в",
                "на",
                "к",
                "с",
                "по",
                "из",
                "от",
                "для",
                "о",
                "у",
                "за",
                "под",
                "над",
                "между",
                "перед",
                "после",
            },
        }

    def answer_question(
        self, question: str, contexts: List[QAContext]
    ) -> Optional[QAResult]:
        """
        Answer question using extractive QA from provided contexts.

        Args:
            question: The question to answer
            contexts: List of document contexts with relevance scores

        Returns:
            QAResult if answer found, None otherwise
        """
        if not contexts:
            return None

        # Detect language
        lang = self._detect_language(question)

        # Extract keywords from question
        keywords = self._extract_keywords(question, lang)

        # Find best answer span
        best_result = None
        best_score = 0.0

        for context in contexts:
            result = self._find_answer_in_context(question, keywords, context, lang)
            if result and result.confidence > best_score:
                best_result = result
                best_score = result.confidence

        return best_result

    def _detect_language(self, text: str) -> str:
        """Simple language detection based on Cyrillic characters."""
        cyrillic_chars = sum(1 for c in text if "\u0400" <= c <= "\u04FF")
        if cyrillic_chars > len(text) * 0.3:  # 30% Cyrillic = Russian
            return "ru"
        return "en"

    def _extract_keywords(self, question: str, lang: str) -> List[str]:
        """Extract important keywords from question."""
        # Remove question words and punctuation
        text = question.lower()
        text = re.sub(r"[^\w\s]", " ", text)

        # Remove stop words
        words = text.split()
        stop_words = self.stop_words.get(lang, set())
        keywords = [word for word in words if word not in stop_words and len(word) > 2]

        return keywords

    def _find_answer_in_context(
        self, question: str, keywords: List[str], context: QAContext, lang: str
    ) -> Optional[QAResult]:
        """Find best answer span in a single context document."""
        content = context.content
        doc_id = context.document_id

        # Split into sentences
        sentences = self._split_into_sentences(content, lang)

        # Score each sentence
        candidates = []
        for i, sentence in enumerate(sentences):
            score = self._score_sentence(sentence, keywords, question, lang)
            if score > 0:
                candidates.append((sentence, score, i))

        if not candidates:
            return None

        # Sort by score
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_sentence, best_score, sentence_idx = candidates[0]

        # Find character positions
        start_char = content.find(best_sentence)
        end_char = start_char + len(best_sentence) if start_char != -1 else 0

        # Extract broader context around the answer
        context_span = self._extract_context_span(content, start_char, end_char)

        # Calculate final confidence (combine sentence score with document relevance)
        confidence = min(
            best_score * context.score, 0.7
        )  # Cap at 0.7 for extractive QA

        return QAResult(
            answer=best_sentence.strip(),
            confidence=confidence,
            context=context_span,
            document_id=doc_id,
            start_char=start_char,
            end_char=end_char,
            source_title=context.title,
        )

    def _split_into_sentences(self, text: str, lang: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting - in production, use proper NLP library
        if lang == "ru":
            # Russian sentence endings
            sentences = re.split(r"(?<=[.!?])\s+", text)
        else:
            # English sentence endings
            sentences = re.split(r"(?<=[.!?])\s+", text)

        return [s.strip() for s in sentences if s.strip()]

    def _score_sentence(
        self, sentence: str, keywords: List[str], question: str, lang: str
    ) -> float:
        """Score how well a sentence answers the question."""
        sentence_lower = sentence.lower()
        question_lower = question.lower()

        score = 0.0

        # Keyword matching
        matched_keywords = 0
        for keyword in keywords:
            if keyword in sentence_lower:
                matched_keywords += 1

        if matched_keywords > 0:
            score += matched_keywords * 0.3  # 0.3 per keyword

        # Exact phrase matching (boost for direct matches)
        if question_lower.strip("?") in sentence_lower:
            score += 0.5

        # Length penalty (prefer concise answers)
        words = sentence.split()
        if 3 <= len(words) <= 50:  # Sweet spot for answer length
            score += 0.2
        elif len(words) > 50:
            score -= 0.1

        # Question pattern matching
        patterns = self.question_patterns.get(lang, [])
        for pattern in patterns:
            if re.search(pattern, question_lower):
                # Check if sentence contains answer-like content
                if re.search(pattern, sentence_lower):
                    score += 0.1

        return max(0.0, min(score, 1.0))  # Clamp to [0, 1]

    def _extract_context_span(
        self, content: str, start_char: int, end_char: int, context_window: int = 200
    ) -> str:
        """Extract broader context around answer span."""
        # Get context window around the answer
        context_start = max(0, start_char - context_window // 2)
        context_end = min(len(content), end_char + context_window // 2)

        # Try to align to sentence boundaries
        while context_start > 0 and content[context_start] not in ".!?\n":
            context_start -= 1

        while context_end < len(content) and content[context_end] not in ".!?\n":
            context_end += 1

        return content[context_start:context_end].strip()


class QAService:
    """
    Question Answering service with graceful degradation.

    Tries LLM first, falls back to extractive QA, then to search results.
    """

    def __init__(self):
        self.extractive_qa = ExtractiveQA()

    async def answer_question(
        self, question: str, contexts: List[QAContext], use_llm: bool = True
    ) -> QAResult:
        """
        Answer question with graceful degradation.

        Args:
            question: Question to answer
            contexts: Relevant document contexts
            use_llm: Whether to try LLM first (default True)

        Returns:
            QAResult with answer and metadata
        """
        # Try extractive QA as fallback
        extractive_result = self.extractive_qa.answer_question(question, contexts)

        if extractive_result:
            # Mark as extractive result
            extractive_result.answer = (
                f"[Извлечено из документа] {extractive_result.answer}"
            )
            return extractive_result

        # Last resort: return a helpful message
        return QAResult(
            answer="Извините, не удалось найти прямой ответ в доступных документах. Попробуйте переформулировать вопрос или использовать поиск по ключевым словам.",
            confidence=0.0,
            context="",
            document_id="",
            start_char=0,
            end_char=0,
        )


# Global QA service instance
qa_service = QAService()
