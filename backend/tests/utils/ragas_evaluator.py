"""
RAGAS metrics integration for evaluating RAG system quality.

This module provides comprehensive evaluation using RAGAS (Retrieval-Augmented Generation Assessment)
framework to measure retrieval quality, generation quality, and overall RAG performance.

Key metrics:
- Context Relevance: How relevant retrieved contexts are to the query
- Answer Faithfulness: How faithful the answer is to the retrieved contexts
- Answer Relevance: How relevant the answer is to the query
- Context Precision: Precision of retrieved contexts
- Context Recall: Recall of retrieved contexts
"""

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import (
        answer_relevancy,
        context_precision,
        context_recall,
        context_relevancy,
        faithfulness,
    )

    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False
    print("Warning: RAGAS not available. Install with: pip install ragas datasets")


@dataclass
class EvaluationResult:
    """Результаты оценки RAG системы"""

    query_id: str
    context_relevancy: float
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
    overall_score: float
    metadata: Dict[str, Any]


class RagasEvaluator:
    """
    Оценщик качества RAG системы с использованием RAGAS метрик.

    Предоставляет комплексную оценку retrieval и generation компонентов,
    включая метрики релевантности, точности и полноты.
    """

    def __init__(
        self, golden_dataset_path: str = "backend/tests/data/golden_dataset.json"
    ):
        """
        Инициализация оценщика.

        Args:
            golden_dataset_path: Путь к golden dataset с тестовыми запросами
        """
        self.golden_dataset_path = Path(golden_dataset_path)
        self.metrics = (
            [
                context_relevancy,
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall,
            ]
            if RAGAS_AVAILABLE
            else []
        )

    async def evaluate_query(
        self,
        query: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None,
    ) -> EvaluationResult:
        """
        Оценка одного запроса с использованием RAGAS метрик.

        Args:
            query: Исходный запрос пользователя
            answer: Сгенерированный ответ
            contexts: Список извлеченных контекстов
            ground_truth: Эталонный ответ (опционально)

        Returns:
            EvaluationResult: Результаты оценки
        """
        if not RAGAS_AVAILABLE:
            raise ImportError(
                "RAGAS не установлен. Установите: pip install ragas datasets"
            )

        # Подготовка данных для RAGAS
        data = {"question": [query], "answer": [answer], "contexts": [contexts]}

        if ground_truth:
            data["ground_truth"] = [ground_truth]

        dataset = Dataset.from_dict(data)

        # Запуск оценки
        results = evaluate(dataset, metrics=self.metrics)

        # Извлечение результатов
        scores = results.scores[0]  # Первый (и единственный) результат

        context_relevancy_score = scores.get("context_relevancy", 0.0)
        faithfulness_score = scores.get("faithfulness", 0.0)
        answer_relevancy_score = scores.get("answer_relevancy", 0.0)
        context_precision_score = scores.get("context_precision", 0.0)
        context_recall_score = scores.get("context_recall", 0.0)

        # Расчет общего скора (взвешенное среднее)
        weights = {
            "context_relevancy": 0.2,
            "faithfulness": 0.3,
            "answer_relevancy": 0.3,
            "context_precision": 0.1,
            "context_recall": 0.1,
        }

        overall_score = (
            context_relevancy_score * weights["context_relevancy"]
            + faithfulness_score * weights["faithfulness"]
            + answer_relevancy_score * weights["answer_relevancy"]
            + context_precision_score * weights["context_precision"]
            + context_recall_score * weights["context_recall"]
        )

        return EvaluationResult(
            query_id=f"eval_{hash(query) % 10000}",
            context_relevancy=context_relevancy_score,
            faithfulness=faithfulness_score,
            answer_relevancy=answer_relevancy_score,
            context_precision=context_precision_score,
            context_recall=context_recall_score,
            overall_score=overall_score,
            metadata={
                "query_length": len(query),
                "answer_length": len(answer),
                "contexts_count": len(contexts),
                "has_ground_truth": ground_truth is not None,
            },
        )

    async def evaluate_golden_dataset(
        self, rag_system_callable: callable, sample_size: Optional[int] = None
    ) -> List[EvaluationResult]:
        """
        Оценка системы на golden dataset.

        Args:
            rag_system_callable: Функция, принимающая query и возвращающая (answer, contexts)
            sample_size: Количество запросов для оценки (None = все)

        Returns:
            List[EvaluationResult]: Результаты оценки для каждого запроса
        """
        if not self.golden_dataset_path.exists():
            raise FileNotFoundError(
                f"Golden dataset не найден: {self.golden_dataset_path}"
            )

        with open(self.golden_dataset_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)

        queries = dataset["queries"]
        if sample_size:
            queries = queries[:sample_size]

        results = []

        for query_data in queries:
            query = query_data["query"]

            try:
                # Вызов RAG системы
                answer, contexts = await rag_system_callable(query)

                # Оценка
                result = await self.evaluate_query(
                    query=query,
                    answer=answer,
                    contexts=contexts,
                    ground_truth=query_data.get("expected_answer"),
                )

                # Добавление метаданных из dataset
                result.metadata.update(
                    {
                        "query_id": query_data["id"],
                        "language": query_data["language"],
                        "category": query_data["category"],
                        "difficulty": query_data["difficulty"],
                    }
                )

                results.append(result)

            except Exception as e:
                print(f"Ошибка оценки запроса {query_data['id']}: {e}")
                continue

        return results

    def generate_report(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """
        Генерация отчета по результатам оценки.

        Args:
            results: Результаты оценки

        Returns:
            Dict с статистикой и анализом
        """
        if not results:
            return {"error": "Нет результатов для анализа"}

        # Базовая статистика
        scores = {
            "context_relevancy": [r.context_relevancy for r in results],
            "faithfulness": [r.faithfulness for r in results],
            "answer_relevancy": [r.answer_relevancy for r in results],
            "context_precision": [r.context_precision for r in results],
            "context_recall": [r.context_recall for r in results],
            "overall_score": [r.overall_score for r in results],
        }

        report = {
            "summary": {
                "total_queries": len(results),
                "average_scores": {
                    metric: sum(values) / len(values) if values else 0.0
                    for metric, values in scores.items()
                },
                "min_scores": {
                    metric: min(values) if values else 0.0
                    for metric, values in scores.items()
                },
                "max_scores": {
                    metric: max(values) if values else 0.0
                    for metric, values in scores.items()
                },
            },
            "breakdown_by_language": {},
            "breakdown_by_category": {},
            "breakdown_by_difficulty": {},
        }

        # Анализ по языкам
        languages = set(r.metadata.get("language", "unknown") for r in results)
        for lang in languages:
            lang_results = [r for r in results if r.metadata.get("language") == lang]
            if lang_results:
                report["breakdown_by_language"][lang] = {
                    "count": len(lang_results),
                    "average_overall": sum(r.overall_score for r in lang_results)
                    / len(lang_results),
                }

        # Анализ по категориям
        categories = set(r.metadata.get("category", "unknown") for r in results)
        for cat in categories:
            cat_results = [r for r in results if r.metadata.get("category") == cat]
            if cat_results:
                report["breakdown_by_category"][cat] = {
                    "count": len(cat_results),
                    "average_overall": sum(r.overall_score for r in cat_results)
                    / len(cat_results),
                }

        # Анализ по сложности
        difficulties = set(r.metadata.get("difficulty", "unknown") for r in results)
        for diff in difficulties:
            diff_results = [r for r in results if r.metadata.get("difficulty") == diff]
            if diff_results:
                report["breakdown_by_difficulty"][diff] = {
                    "count": len(diff_results),
                    "average_overall": sum(r.overall_score for r in diff_results)
                    / len(diff_results),
                }

        return report

    async def run_evaluation_pipeline(
        self,
        rag_system_callable: callable,
        output_path: str = "evaluation_report.json",
        sample_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Полный pipeline оценки: запуск оценки и генерация отчета.

        Args:
            rag_system_callable: Функция RAG системы
            output_path: Путь для сохранения отчета
            sample_size: Размер выборки

        Returns:
            Dict с отчетом
        """
        print("Запуск оценки на golden dataset...")
        results = await self.evaluate_golden_dataset(rag_system_callable, sample_size)

        print(f"Оценено {len(results)} запросов")
        report = self.generate_report(results)

        # Сохранение отчета
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "timestamp": "2025-10-17T19:37:00Z",
                    "evaluator_version": "1.0.0",
                    "results": [vars(r) for r in results],
                    "report": report,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        print(f"Отчет сохранен в {output_path}")
        return report


# Пример использования
async def example_usage():
    """Пример использования оценщика"""

    def mock_rag_system(query: str) -> tuple[str, List[str]]:
        """Мок RAG системы для тестирования"""
        return (
            f"Ответ на запрос: {query}",
            [f"Контекст 1 для {query}", f"Контекст 2 для {query}"],
        )

    evaluator = RagasEvaluator()

    try:
        report = await evaluator.run_evaluation_pipeline(
            rag_system_callable=mock_rag_system,
            sample_size=5,  # Для быстрого тестирования
        )

        print("Отчет по оценке:")
        print(json.dumps(report, ensure_ascii=False, indent=2))

    except ImportError as e:
        print(f"Ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(example_usage())
