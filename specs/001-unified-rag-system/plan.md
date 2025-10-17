# Implementation Plan: Unified RAG System

**Branch**: `001-unified-rag-system` | **Date**: 2025-10-17 | **Spec**: [link]

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Unified RAG system for personal knowledge base with absolute privacy, supporting 1000-10000 documents from SiYuan notes. Implements graceful degradation across three levels, Russian-first language support, and self-hosted architecture on 4vCPU/8GB VPS.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: FastAPI 0.119.0, Qdrant 1.15.5, SQLite 3.50.4+, Traefik 3.x, SiYuan SDK, ONNX Runtime, NumPy
**Storage**: Qdrant vector database (dense embeddings), SQLite with FTS5 (sparse search), ZRAM compression
**Testing**: pytest for Python components
**Target Platform**: Ubuntu 25.10/24.04 LTS VPS with 4vCPU/8GB RAM
**Project Type**: API backend with SiYuan plugin integration
**Performance Goals**: E2E LLM < 5-7s, cached < 150ms, recall@15 ≥ 90%
**Constraints**: Zero API costs, offline-first, absolute privacy, Russian language priority
**Scale/Scope**: 1000-10000 documents, multi-language support, real-time SiYuan sync

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- ✅ Privacy Without Compromise: Raw data never leaves server, only anonymized summaries to LLM
- ✅ Honesty Over Performance: Confidence scores calibrated, citations precise to character span
- ✅ Graceful Degradation: 3-level system (LLM → QA → Search) useful at every level
- ✅ Search Quality Targets: Recall@15 ≥ 90%, citation precision ≥ 98%, latency targets met
- ✅ Russian as First-Class Language: pymorphy3 lemmatization, 50% Russian test corpus
- ✅ Cost Model: Zero API, self-hosted on $10-20/month VPS
- ✅ Modular Design: Clear API/CLI interfaces, swappable embeddings/LLM providers
- ✅ Testing-First Discipline: TDD mandatory, golden dataset 100+ queries
- ✅ Code Quality: Bilingual comments/docstrings explaining WHY with real-world analogies
- ✅ SiYuan Integration: 30s sync, "Open in SiYuan" links with exact location
- ✅ Localization: UI from locales/ru.json|en.json, Russian default
- ✅ Observability: JSON responses with trace_id, 30s health checks, daily snapshots

## Project Structure

### Documentation (this feature)

```
specs/001-unified-rag-system/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
backend/
├── src/
│   ├── models/          # Data models (Document, Query, Result)
│   ├── services/        # Core services (Search, LLM, Cache)
│   ├── api/             # FastAPI routes and endpoints
│   ├── integrations/    # SiYuan, Qdrant, SQLite adapters
│   └── utils/           # Language detection, chunking, embeddings
├── tests/
│   ├── contract/        # API contract tests
│   ├── integration/     # End-to-end tests
│   └── unit/            # Unit tests for all components
└── scripts/             # Deployment and maintenance scripts

siyuan-plugin/
├── src/
│   ├── widgets/         # Search widget components
│   ├── services/        # API client for backend communication
│   ├── locales/         # ru.json, en.json localization files
│   └── utils/           # Plugin utilities and helpers
├── tests/
└── dist/                # Built plugin distribution

infrastructure/
├── docker/              # Dockerfiles for all services
├── docker-compose.yml   # Production deployment (integrates with existing traefik_network)
└── monitoring/          # Health checks and metrics

shared/
├── types/               # Python shared type definitions
└── constants/           # Shared constants and configuration
```

**Structure Decision**: Web application with separate backend/frontend for scalability, infrastructure-as-code with Docker Compose for easy deployment on target VPS.

## Implementation Phases

### Phase 0: Research & Foundation (1-2 weeks)

**Purpose**: Validate technical approach and establish development environment

- [ ] T001 Research BGE-M3 multilingual embeddings performance on Russian corpus
- [ ] T002 Benchmark Qdrant vs alternatives for 10k document scale
- [ ] T003 Test SiYuan API integration and data extraction patterns
- [ ] T004 Evaluate LLM providers for free-tier availability and Russian support
- [ ] T005 Setup development environment with Docker Compose
- [ ] T006 Create baseline performance benchmarks (empty system)

### Phase 1: Core Infrastructure (2-3 weeks)

**Purpose**: Build the fundamental data pipeline and search infrastructure

- [ ] T007 Implement SiYuan connector with 30s sync capability
- [ ] T008 Build document chunking and deduplication pipeline
- [ ] T009 Setup Qdrant vector database with BGE-M3 collections
- [ ] T010 Implement SQLite FTS5 for sparse search fallback
- [ ] T011 Create embedding service with CPU-optimized ONNX models
- [ ] T012 Build unified search with RRF (Reciprocal Rank Fusion)
- [ ] T013 Implement reranking with bge-reranker-v2.5
- [ ] T014 Create confidence scoring algorithm (0.4*reranker + 0.3*match_count + 0.2*recency + 0.1*quality)
- [ ] T015 Setup semantic cache with hybrid similarity (0.6*cosine + 0.4*jaccard)

### Phase 2: API & Routing (1-2 weeks)

**Purpose**: Create the backend API with graceful degradation routing

- [ ] T016 Build FastAPI application structure with bilingual comments
- [ ] T017 Implement /ask endpoint with streaming responses
- [ ] T018 Create LLM router with free-tier providers (Gemini → Groq → OpenRouter)
- [ ] T019 Implement circuit breaker and retry logic for rate limits
- [ ] T020 Build extractive QA fallback using RoBERTa
- [ ] T021 Add health checks and metrics endpoints
- [ ] T022 Implement trace_id correlation across all services
- [ ] T023 Create API documentation with Russian + English

### Phase 3: SiYuan Plugin & Integration (2 weeks)

**Purpose**: Build SiYuan plugin and complete system integration

- [ ] T024 Research SiYuan plugin development APIs and architecture
- [ ] T025 Create SiYuan plugin structure with search widget
- [ ] T026 Implement search interface within SiYuan UI
- [ ] T027 Build results display with confidence scores and citations
- [ ] T028 Add multi-hop knowledge connections visualization
- [ ] T029 Implement localization (ru.json, en.json) with Russian default
- [ ] T030 Create direct "Open in SiYuan" links to exact locations
- [ ] T031 Add caching indicators and refresh functionality
- [ ] T032 Implement export functionality for results and citations

### Phase 4: Quality Assurance & Polish (1-2 weeks)

**Purpose**: Testing, performance optimization, and production readiness

- [ ] T032 Create golden dataset with 100+ Russian/English queries
- [ ] T033 Implement comprehensive test suite (unit, integration, contract)
- [ ] T034 Performance optimization for latency targets (<5-7s LLM, <150ms cached)
- [ ] T035 Russian language corpus testing (minimum 50% of tests)
- [ ] T036 RAGAS metrics integration for generation quality
- [ ] T037 Setup monitoring and alerting (health checks, metrics)
- [ ] T038 Create deployment scripts and documentation
- [ ] T039 Final security review and privacy validation

### Phase 5: Deployment & Monitoring (1 week)

**Purpose**: Production deployment and ongoing system health

- [ ] T040 Integrate with existing Traefik setup (use traefik_network, add labels for api/qd services)
- [ ] T041 Configure domain routing (api.${DOMAIN_NAME}, qd.${DOMAIN_NAME})
- [ ] T042 Deploy to target VPS (Ubuntu 24.04, 4vCPU/8GB RAM) alongside existing services
- [ ] T043 Setup daily backups (Qdrant snapshots + SQLite dumps)
- [ ] T044 Configure monitoring dashboard and alerts
- [ ] T045 Performance validation on production hardware
- [ ] T046 Documentation completion (README, API docs in RU+EN)

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 0**: No dependencies - research can start immediately
- **Phase 1**: Depends on Phase 0 research validation
- **Phase 2**: Depends on Phase 1 core infrastructure completion
- **Phase 3**: Depends on Phase 2 API availability
- **Phase 4**: Depends on Phase 3 integration completion
- **Phase 5**: Depends on Phase 4 QA sign-off

### Parallel Opportunities

- Research tasks (T001-T006) can run in parallel
- Infrastructure components (T007-T015) have some parallel paths
- API development (T016-T023) can proceed while frontend starts
- Testing (T032-T036) can begin early with mock services
- Documentation (T038, T046) can be created throughout development

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Multi-language support | Constitution requires Russian as first-class language | Single language would violate principle 5 |
| 3-level graceful degradation | Constitution mandates 3 levels of usefulness | 2-level system would violate principle 3 |
| Self-hosted LLM routing | Constitution requires zero API costs | Cloud LLM would violate principle 6 |
| Real-time SiYuan sync | Constitution requires 30s sync intervals | Batch sync would violate principle 10 |
