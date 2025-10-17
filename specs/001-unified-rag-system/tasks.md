---
description: "Task list for Unified RAG System implementation"
---

# Tasks: Unified RAG System

**Input**: Design documents from `/specs/001-unified-rag-system/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The examples below include test tasks. Tests are MANDATORY - include them for every user story as per constitution principle 8 (Testing-First Discipline).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- **Backend**: `backend/src/`, `backend/tests/`
- **SiYuan Plugin**: `siyuan-plugin/src/`, `siyuan-plugin/tests/`
- **Infrastructure**: `infrastructure/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per implementation plan
- [ ] T002 Initialize Python project with FastAPI and dependencies
- [ ] T003 [P] Setup Python optimization libraries (NumPy, ONNX Runtime for performance)
- [ ] T004 [P] Configure Docker Compose with all services
- [ ] T005 [P] Setup development environment and pre-commit hooks

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 Setup SiYuan API integration and document fetching
- [ ] T007 Implement document chunking and deduplication pipeline
- [ ] T008 Setup Qdrant vector database with BGE-M3 collections
- [ ] T009 Implement SQLite FTS5 for sparse search fallback
- [ ] T010 Create embedding service with CPU-optimized models
- [ ] T011 Build unified search with RRF (Reciprocal Rank Fusion)
- [ ] T012 Implement reranking with bge-reranker-v2.5
- [ ] T013 Create confidence scoring algorithm
- [ ] T014 Setup semantic cache with hybrid similarity
- [ ] T015 Build FastAPI application structure with bilingual comments

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Researcher Finding Context Chains (Priority: P1) 🎯 MVP

**Goal**: Enable researchers to instantly see how their ideas evolved and connect across different documents

**Independent Test**: Can be fully tested by querying historical research notes and verifying linked documents appear correctly

### Tests for User Story 1 (MANDATORY - constitution principle 8) ⚠️

**NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T016 [P] [US1] Contract test for multi-hop connections in backend/tests/contract/test_connections.py
- [ ] T017 [P] [US1] Integration test for timeline queries in backend/tests/integration/test_research_workflow.py

### Implementation for User Story 1

- [ ] T018 [P] [US1] Implement document relationship extraction in backend/src/integrations/siyuan_connector.py
- [ ] T019 [P] [US1] Create connection storage and retrieval in backend/src/models/connections.py
- [ ] T020 [US1] Build timeline API endpoint in backend/src/api/search.py (depends on T018, T019)
- [ ] T021 [US1] Add connection visualization in SiYuan plugin in siyuan-plugin/src/widgets/connections.js
- [ ] T022 [US1] Implement connection strength indicators in siyuan-plugin/src/utils/connections.js

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Developer Getting Code Examples (Priority: P1)

**Goal**: Deliver working code snippets from personal notes instantly

**Independent Test**: Can be fully tested by storing code examples and verifying they appear in search results

### Tests for User Story 2 (MANDATORY - constitution principle 8) ⚠️

- [ ] T023 [P] [US2] Contract test for code snippet extraction in backend/tests/contract/test_code_extraction.py
- [ ] T024 [P] [US2] Integration test for developer workflow in backend/tests/integration/test_developer_workflow.py

### Implementation for User Story 2

- [ ] T025 [P] [US2] Implement code detection and formatting in backend/src/utils/code_processor.py
- [ ] T026 [P] [US2] Create code snippet storage in backend/src/models/code_snippets.py
- [ ] T027 [US2] Build code search API endpoint in backend/src/api/search.py
- [ ] T028 [US2] Add code syntax highlighting in siyuan-plugin/src/widgets/code_display.js
- [ ] T029 [US2] Implement clipboard copy functionality in siyuan-plugin/src/utils/clipboard.js

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Writer Discovering Idea Connections (Priority: P2)

**Goal**: Show semantic connections between concepts across writing

**Independent Test**: Can be fully tested by storing interconnected writing notes and verifying relationship graphs

### Tests for User Story 3 (MANDATORY - constitution principle 8) ⚠️

- [ ] T030 [P] [US3] Contract test for semantic connections in backend/tests/contract/test_semantic_links.py
- [ ] T031 [P] [US3] Integration test for writer workflow in backend/tests/integration/test_writer_workflow.py

### Implementation for User Story 3

- [ ] T032 [P] [US3] Implement semantic relationship extraction in backend/src/services/semantic_analyzer.py
- [ ] T033 [P] [US3] Create relationship graph storage in backend/src/models/relationships.py
- [ ] T034 [US3] Build relationship API endpoint in backend/src/api/search.py
- [ ] T035 [US3] Add graph visualization in siyuan-plugin/src/widgets/relationship_graph.js
- [ ] T036 [US3] Implement graph interaction controls in siyuan-plugin/src/utils/graph_interactions.js

**Checkpoint**: At this point, User Stories 1, 2, AND 3 should all work independently

---

## Phase 6: Core Features & Polish (Cross-cutting Concerns)

**Purpose**: Complete core functionality and system-wide improvements

- [ ] T037 [P] Implement LLM routing with free providers in backend/src/services/llm_router.py
- [ ] T038 [P] Add circuit breaker and retry logic in backend/src/utils/circuit_breaker.py
- [ ] T039 [P] Build extractive QA fallback in backend/src/services/qa_service.py
- [ ] T040 Implement graceful degradation routing in backend/src/api/search.py
- [ ] T041 [P] Add thinking traces for high-confidence answers in backend/src/models/traces.py
- [ ] T042 [P] Implement caching indicators in siyuan-plugin/src/widgets/cache_status.js
- [ ] T043 [P] Add export functionality in siyuan-plugin/src/utils/exporters.js
- [ ] T044 Implement localization (ru.json, en.json) in siyuan-plugin/src/locales/

---

## Phase 7: Quality Assurance & Performance (Testing & Optimization)

**Purpose**: Comprehensive testing and performance validation

- [ ] T045 Create golden dataset with 100+ queries in backend/tests/data/golden_dataset.json
- [ ] T046 [P] Implement RAGAS metrics integration in backend/tests/utils/ragas_evaluator.py
- [ ] T047 [P] Performance optimization for latency targets in backend/src/optimizations/
- [ ] T048 [P] Russian language corpus testing (50% of tests) in backend/tests/test_russian_corpus.py
- [ ] T049 Setup monitoring and health checks in infrastructure/monitoring/
- [ ] T050 [P] Final security review and privacy validation in backend/tests/security/

---

## Phase 8: Deployment & Documentation

**Purpose**: Production deployment and system documentation

- [ ] T051 Integrate with existing Traefik setup (use traefik_network, add labels for api/qd services)
- [ ] T052 Configure domain routing (api.${DOMAIN_NAME}, qd.${DOMAIN_NAME})
- [ ] T053 Deploy to target VPS (Ubuntu 24.04, 4vCPU/8GB RAM) alongside existing services
- [ ] T054 Setup daily backups (Qdrant snapshots + SQLite dumps)
- [ ] T055 Configure monitoring dashboard and alerts
- [ ] T056 Documentation completion (README, API docs in RU+EN)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P1 → P2)
- **Core Features (Phase 6)**: Depends on all desired user stories being complete
- **QA (Phase 7)**: Depends on Phase 6 completion
- **Deployment (Phase 8)**: Depends on Phase 7 sign-off

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - No dependencies on other stories

### Within Each User Story

- Tests (MANDATORY) MUST be written and FAIL before implementation
- Models before services
- Services before API endpoints
- API before plugin integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Researcher workflow)
   - Developer B: User Story 2 (Developer workflow)
   - Developer C: User Story 3 (Writer workflow)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (constitution principle 8)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
