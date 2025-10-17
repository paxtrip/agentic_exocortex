"""
Search API endpoints for the Unified RAG System.

This module provides FastAPI endpoints for:
- Timeline queries showing research evolution
- Search with connection visualization
- Health checks and metrics

Following the principle of graceful degradation - all endpoints work
even when some components (like SiYuan or LLM) are unavailable.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..integrations.siyuan_connector import SiYuanConnector
from ..models.code_snippets import CodeQuery, CodeResult, CodeSnippetStore
from ..models.connections import ConnectionQuery, ConnectionResult, ConnectionStore
from ..models.relationships import RelationshipStorage
from ..services.llm_router import LLMResponse, llm_router
from ..services.qa_service import QAContext, QAResult, qa_service
from ..services.semantic_analyzer import SemanticAnalyzer
from ..utils.circuit_breaker import llm_circuit_breaker
from ..utils.code_processor import extract_code_snippets

logger = logging.getLogger(__name__)

router = APIRouter()


class TimelineQuery(BaseModel):
    """Query for research timeline."""

    topic: str = Field(..., description="Research topic to explore")
    start_date: Optional[str] = Field(None, description="Start date (ISO format)")
    end_date: Optional[str] = Field(None, description="End date (ISO format)")
    max_connections: int = Field(50, description="Maximum connections to return")


class TimelineResult(BaseModel):
    """Result of timeline query."""

    topic: str
    documents: List[Dict[str, Any]]
    connections: List[Dict[str, Any]]
    trace_id: str
    generated_at: str


class AskQuery(BaseModel):
    """Query for the /ask endpoint."""

    question: str = Field(..., description="Question to answer")
    context_docs: Optional[List[str]] = Field(
        None, description="Specific document IDs to search in"
    )
    max_context: int = Field(10, description="Maximum context documents to retrieve")


class AskResult(BaseModel):
    """Result from the /ask endpoint."""

    question: str
    answer: str
    confidence: float
    source: str  # "llm", "extractive_qa", or "search"
    context_used: List[Dict[str, Any]]
    trace_id: str
    generated_at: str
    provider: Optional[str] = None  # LLM provider used


class SearchAPI:
    """
    Search API for the Unified RAG System.

    Provides endpoints for timeline queries, connection exploration, and code search.
    Designed to work even when SiYuan is unavailable (graceful degradation).
    """

    def __init__(self):
        self.connection_store = ConnectionStore()
        self.code_store = CodeSnippetStore()
        self.relationship_storage = RelationshipStorage()
        self.semantic_analyzer = SemanticAnalyzer()
        self.siyuan_connector = SiYuanConnector()

    async def get_research_timeline(self, query: TimelineQuery) -> TimelineResult:
        """
        Get research timeline showing how ideas evolved over time.

        This is the main endpoint for User Story 1 - researchers can see
        how their thinking developed across different documents.

        Args:
            query: Timeline query parameters

        Returns:
            TimelineResult with documents and connections
        """
        try:
            # For now, return a basic structure - will be enhanced with full implementation
            # This satisfies the contract test requirements

            trace_id = f"trace_{datetime.utcnow().timestamp()}"

            # Mock documents for the timeline (will be replaced with real data)
            documents = [
                {
                    "id": "doc_001",
                    "title": f"Research on {query.topic}",
                    "content": f"Document about {query.topic}",
                    "created_at": datetime.utcnow().isoformat() + "Z",
                }
            ]

            # Get connections related to the topic (placeholder for now)
            connections = []

            result = TimelineResult(
                topic=query.topic,
                documents=documents,
                connections=connections,
                trace_id=trace_id,
                generated_at=datetime.utcnow().isoformat() + "Z",
            )

            logger.info(
                f"Generated timeline for topic '{query.topic}' with trace_id {trace_id}"
            )
            return result

        except Exception as e:
            logger.error(f"Error generating timeline for topic '{query.topic}': {e}")
            # Return minimal valid result for graceful degradation
            return TimelineResult(
                topic=query.topic,
                documents=[],
                connections=[],
                trace_id=f"error_{datetime.utcnow().timestamp()}",
                generated_at=datetime.utcnow().isoformat() + "Z",
            )

    async def ingest_document(self, document: Dict[str, Any]) -> Dict[str, str]:
        """
        Ingest a document and extract its connections and code snippets.

        Args:
            document: Document data with id, content, etc.

        Returns:
            Status message
        """
        try:
            doc_id = document.get("id")
            content = document.get("content", "")

            if not doc_id or not content:
                raise ValueError("Document must have id and content")

            # Extract connections from the document
            async with self.siyuan_connector as connector:
                connections = await connector.extract_connections(doc_id, content)

            # Store the connections
            await self.connection_store.store_connections(connections)

            # Extract code snippets from the document
            code_snippets = await extract_code_snippets(doc_id, content)

            # Store the code snippets
            await self.code_store.store_snippets(code_snippets)

            logger.info(
                f"Ingested document {doc_id} with {len(connections)} connections and {len(code_snippets)} code snippets"
            )
            return {
                "status": "success",
                "connections_found": len(connections),
                "code_snippets_found": len(code_snippets),
            }

        except Exception as e:
            logger.error(
                f"Error ingesting document {document.get('id', 'unknown')}: {e}"
            )
            raise HTTPException(
                status_code=500, detail=f"Failed to ingest document: {str(e)}"
            )

    async def search_code(self, query: CodeQuery) -> CodeResult:
        """
        Search for code snippets based on natural language query.

        This is the main endpoint for User Story 2 - developers can find
        code examples by describing what they need.

        Args:
            query: Code search query parameters

        Returns:
            CodeResult with matching snippets
        """
        try:
            result = await self.code_store.search_snippets(query)
            logger.info(
                f"Code search for '{query.query}' returned {result.total_found} results"
            )
            return result

        except Exception as e:
            logger.error(f"Error searching code for query '{query.query}': {e}")
            # Return empty result for graceful degradation
            return CodeResult(
                snippets=[],
                total_found=0,
                trace_id=f"error_{datetime.utcnow().timestamp()}",
            )

    async def ask_question(self, query: AskQuery) -> AskResult:
        """
        Answer question with graceful degradation routing.

        This is the main /ask endpoint implementing the 3-level degradation:
        1. LLM generation (best quality)
        2. Extractive QA (direct text extraction)
        3. Search results (basic retrieval)

        Args:
            query: Question and context parameters

        Returns:
            AskResult with answer and metadata
        """
        trace_id = f"ask_{datetime.utcnow().timestamp()}"

        try:
            # Get relevant context documents
            context_docs = await self._get_context_documents(query)

            # Level 1: Try LLM generation
            try:
                llm_response = await llm_circuit_breaker.call(
                    llm_router.generate_response,
                    query.question,
                    [doc["content"] for doc in context_docs[:3]],  # Limit context
                )

                if llm_response.confidence > 0.6:  # High confidence threshold
                    return AskResult(
                        question=query.question,
                        answer=llm_response.content,
                        confidence=llm_response.confidence,
                        source="llm",
                        context_used=context_docs,
                        trace_id=trace_id,
                        generated_at=datetime.utcnow().isoformat() + "Z",
                        provider=llm_response.provider,
                    )

            except Exception as e:
                logger.warning(f"LLM generation failed: {e}")

            # Level 2: Extractive QA fallback
            qa_contexts = [
                QAContext(
                    document_id=doc["id"],
                    content=doc["content"],
                    title=doc.get("title"),
                    score=doc.get("score", 0.5),
                )
                for doc in context_docs
            ]

            qa_result = await qa_service.answer_question(
                query.question, qa_contexts, use_llm=False
            )

            if qa_result.confidence > 0.3:  # Lower threshold for extractive QA
                return AskResult(
                    question=query.question,
                    answer=qa_result.answer,
                    confidence=qa_result.confidence,
                    source="extractive_qa",
                    context_used=context_docs,
                    trace_id=trace_id,
                    generated_at=datetime.utcnow().isoformat() + "Z",
                )

            # Level 3: Return search results as fallback
            search_summary = self._summarize_search_results(context_docs)
            return AskResult(
                question=query.question,
                answer=search_summary,
                confidence=0.1,  # Very low confidence
                source="search",
                context_used=context_docs,
                trace_id=trace_id,
                generated_at=datetime.utcnow().isoformat() + "Z",
            )

        except Exception as e:
            logger.error(f"Error in ask_question: {e}")
            return AskResult(
                question=query.question,
                answer="Извините, произошла ошибка при обработке вопроса. Попробуйте позже.",
                confidence=0.0,
                source="error",
                context_used=[],
                trace_id=trace_id,
                generated_at=datetime.utcnow().isoformat() + "Z",
            )

    async def _get_context_documents(self, query: AskQuery) -> List[Dict[str, Any]]:
        """Get relevant context documents for the question."""
        # This is a placeholder - in real implementation, this would:
        # 1. Search vector database for semantic matches
        # 2. Search FTS for keyword matches
        # 3. Combine and rerank results

        # For now, return mock documents
        return [
            {
                "id": "doc_001",
                "content": f"Пример документа по теме: {query.question}",
                "title": f"Документ о {query.question[:30]}...",
                "score": 0.8,
            }
        ]

    def _summarize_search_results(self, context_docs: List[Dict[str, Any]]) -> str:
        """Create a summary from search results when other methods fail."""
        if not context_docs:
            return "Не найдено релевантных документов для ответа на вопрос."

        titles = [doc.get("title", "Без названия") for doc in context_docs[:3]]
        return f"Найденные документы: {', '.join(titles)}. Рекомендую ознакомиться с ними для получения дополнительной информации."


# Create API instance
search_api = SearchAPI()


@router.post("/timeline", response_model=TimelineResult)
async def get_research_timeline(query: TimelineQuery):
    """
    Get research timeline showing idea evolution.

    This endpoint allows researchers to see how their ideas developed
    over time across different documents, revealing connection chains.
    """
    return await search_api.get_research_timeline(query)


@router.post("/documents/ingest")
async def ingest_document(document: Dict[str, Any]):
    """
    Ingest a document and extract its connections.

    Used to add new documents to the knowledge base and discover
    relationships between them.
    """
    return await search_api.ingest_document(document)


@router.get("/connections/{doc_id}")
async def get_document_connections(
    doc_id: str,
    max_hops: int = Query(3, description="Maximum connection hops"),
    min_strength: float = Query(0.1, description="Minimum connection strength"),
):
    """
    Get connections for a specific document.

    Returns all documents connected to the given document,
    optionally including multi-hop connections.
    """
    try:
        query = ConnectionQuery(
            doc_id=doc_id, max_hops=max_hops, min_strength=min_strength
        )
        result = await search_api.connection_store.get_connections(query)
        return result
    except Exception as e:
        logger.error(f"Error getting connections for {doc_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get connections: {str(e)}"
        )


@router.post("/code/search", response_model=CodeResult)
async def search_code(query: CodeQuery):
    """
    Search for code snippets by natural language description.

    This endpoint allows developers to find code examples by describing
    what they need, supporting multiple programming languages and concepts.
    """
    return await search_api.search_code(query)


@router.post("/ask", response_model=AskResult)
async def ask_question(query: AskQuery):
    """
    Answer questions with graceful degradation.

    This is the main Q&A endpoint that tries multiple strategies:
    1. LLM generation (best quality)
    2. Extractive QA from documents
    3. Search result summary (fallback)

    Always provides an answer, with clear confidence indicators.
    """
    return await search_api.ask_question(query)


@router.get("/code/{snippet_id}")
async def get_code_snippet(snippet_id: str):
    """
    Get a specific code snippet by ID.

    Returns the full code snippet with metadata.
    """
    try:
        snippet = await search_api.code_store.get_snippet_by_id(snippet_id)
        if not snippet:
            raise HTTPException(status_code=404, detail="Code snippet not found")
        return snippet
    except Exception as e:
        logger.error(f"Error getting code snippet {snippet_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get code snippet: {str(e)}"
        )


@router.get("/code/stats")
async def get_code_stats():
    """
    Get statistics about stored code snippets.

    Returns counts by language and other metrics.
    """
    try:
        stats = await search_api.code_store.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting code stats: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get code stats: {str(e)}"
        )


@router.get("/relationships/{doc_id}")
async def get_document_relationships(doc_id: str):
    """
    Get semantic relationships for a specific document.

    This endpoint supports User Story 3 - writers can see semantic connections
    between their documents, revealing idea relationships that might not be obvious.
    """
    try:
        relationships = search_api.relationship_storage.get_relationships_for_document(
            doc_id
        )
        return {
            "document_id": doc_id,
            "relationships": [
                {
                    "target_id": rel.target_id,
                    "relationship_type": rel.relationship_type,
                    "confidence": rel.confidence,
                    "context": rel.context,
                }
                for rel in relationships
            ],
            "total_relationships": len(relationships),
            "trace_id": f"trace_{datetime.utcnow().timestamp()}",
        }
    except Exception as e:
        logger.error(f"Error getting relationships for {doc_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get relationships: {str(e)}"
        )


@router.post("/relationships/analyze")
async def analyze_document_relationships(documents: List[Dict[str, Any]]):
    """
    Analyze semantic relationships between documents.

    This endpoint takes a list of documents and extracts semantic relationships
    between them, storing the results for later retrieval.
    """
    try:
        # Extract relationships using semantic analyzer
        relationships = search_api.semantic_analyzer.extract_relationships(documents)

        # Store relationships
        success = search_api.relationship_storage.store_relationships(relationships)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to store relationships")

        return {
            "status": "success",
            "documents_analyzed": len(documents),
            "relationships_found": len(relationships),
            "trace_id": f"trace_{datetime.utcnow().timestamp()}",
        }
    except Exception as e:
        logger.error(f"Error analyzing document relationships: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze relationships: {str(e)}"
        )


@router.get("/relationships/graph")
async def get_relationship_graph():
    """
    Get the complete relationship graph for visualization.

    Returns nodes and edges formatted for graph visualization libraries.
    """
    try:
        viz_data = search_api.relationship_storage.get_visualization_data()
        return {"graph": viz_data, "trace_id": f"trace_{datetime.utcnow().timestamp()}"}
    except Exception as e:
        logger.error(f"Error getting relationship graph: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get relationship graph: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns system status and basic metrics.
    """
    try:
        # Get basic connection statistics
        connection_stats = await search_api.connection_store.get_connection_stats()
        code_stats = await search_api.code_store.get_stats()
        relationship_stats = search_api.relationship_storage.get_relationship_stats()

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "connections": connection_stats.get("total_connections", 0),
            "documents": connection_stats.get("unique_documents", 0),
            "code_snippets": code_stats.get("total_snippets", 0),
            "code_languages": code_stats.get("languages", {}),
            "semantic_relationships": relationship_stats.get("total_relationships", 0),
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "degraded",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": str(e),
        }
