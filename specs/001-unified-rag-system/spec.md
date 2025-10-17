# Feature Specification: Unified RAG System

**Feature Branch**: `001-unified-rag-system`
**Created**: 2025-10-17
**Status**: Draft
**Input**: User description: "Create detailed functional specification for Feature #1: Unified RAG System. DO NOT include: Tech stack, databases, APIs, implementation details DO include: User experience, what they see, why it matters"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Researcher Finding Context Chains (Priority: P1)

**As a researcher with 10+ years of accumulated notes**, I want to instantly see how my ideas evolved and connect across different documents, so that I can build upon my previous thinking without losing context.

**Why this priority**: Researchers need to trace intellectual evolution across time - this is the core value proposition of a personal knowledge base.

**Independent Test**: Can be fully tested by querying historical research notes and verifying that related documents from different time periods are correctly linked and displayed.

**Acceptance Scenarios**:

1. **Given** I have notes from 2015 about machine learning fundamentals, **When** I search "neural network basics", **Then** I see connections to my 2023 advanced papers that build on those fundamentals.
2. **Given** I query a specific research question, **When** the system finds relevant documents, **Then** I can click "related documents" and see a timeline of how my thinking evolved on that topic.
3. **Given** I find a key insight in one document, **When** I explore connections, **Then** I see what documents cite this one and what this one cites.
4. **Given** I want to understand the evolution of a concept, **When** I view the timeline, **Then** I see documents ordered chronologically with connection strength indicators.

---

### User Story 2 - Developer Getting Code Examples (Priority: P1)

**As a developer maintaining code with documentation and examples**, I want working code snippets from my own notes instantly, so that I can solve problems using my proven solutions.

**Why this priority**: Developers waste time reinventing solutions they've already documented - this delivers immediate productivity gains.

**Independent Test**: Can be fully tested by storing code examples in the knowledge base and verifying they appear in search results with proper formatting and context.

**Acceptance Scenarios**:

1. **Given** I have documented a PostgreSQL replication setup, **When** I search "Как я настраивал PostgreSQL репликацию?", **Then** I get my exact setup steps with citations to the source document.
2. **Given** I need a code snippet, **When** I search for a programming problem, **Then** I see working code from my own projects with "Open in SiYuan" links to the original.
3. **Given** I find a code example, **When** I click the citation, **Then** I jump to the exact location in my notes where I documented that solution.
4. **Given** I need to copy a code snippet, **When** I click the code block, **Then** it gets copied to clipboard with proper formatting preserved.
5. **Given** I want to see code in context, **When** I view the result, **Then** I see surrounding documentation and comments that explain the code's purpose.

---

### User Story 3 - Writer Discovering Idea Connections (Priority: P2)

**As a writer tracking ideas and their relationships**, I want to see semantic connections between concepts across my writing, so that I can create richer, more interconnected content.

**Why this priority**: Writers need to see how ideas relate to build coherent narratives - this enhances creative output.

**Independent Test**: Can be fully tested by storing writing notes with interconnected ideas and verifying that searches reveal relationship graphs.

**Acceptance Scenarios**:

1. **Given** I have notes about "creativity techniques" and "writing habits", **When** I search for writing improvement, **Then** I see how these concepts connect in my notes.
2. **Given** I explore an idea, **When** I click "related documents", **Then** I see a network of connected concepts that shows my thinking patterns.
3. **Given** I want to develop an idea further, **When** I see connections, **Then** I can follow links to see how similar ideas evolved in my past writing.
4. **Given** I want to visualize connections, **When** I view related documents, **Then** I see a graph showing how concepts branch and interconnect.
5. **Given** I find a cluster of related ideas, **When** I explore the network, **Then** I can save the connection map for later reference.

---

### User Story 4 - Student Learning from Personal Materials (Priority: P2)

**As a student using my own study materials**, I want personalized explanations using my notes, so that I can learn in my own context and terminology.

**Why this priority**: Personal learning materials are more effective when presented in familiar terms - this improves learning outcomes.

**Independent Test**: Can be fully tested by storing study notes and verifying that answers incorporate the student's own examples and explanations.

**Acceptance Scenarios**:

1. **Given** I have study notes with my own examples, **When** I ask a question, **Then** the answer uses my examples and explanations from my notes.
2. **Given** I need to understand a concept, **When** the system answers, **Then** it explains using analogies and examples I've collected in my notes.
3. **Given** I want to review a topic, **When** I search, **Then** I get a summary that connects my various notes on that subject.
4. **Given** I need clarification on a difficult concept, **When** I ask for more detail, **Then** the system explains using my own simplified explanations from study notes.
5. **Given** I want to test my understanding, **When** I ask a question, **Then** the answer includes self-quiz questions based on my study materials.

---

### Edge Cases

- What happens when a query matches documents in multiple languages? System processes mixed queries naturally with unified model.
- How does system handle very old documents (5+ years)? Recency factor in confidence score ensures fresh content is prioritized but old relevant content still appears.
- What if user searches for something not in their notes? System gracefully degrades to search results with low confidence score.
- How does caching affect repeated searches? Cached results appear instantly with "From cache" badge and option to refresh.
- What happens when SiYuan API is temporarily unavailable? System continues to work with cached document index but shows connection warning.
- How does system handle documents with corrupted or invalid content? System skips invalid documents and logs errors without failing the entire search.
- What if user has 10,000+ documents? System maintains performance through efficient indexing and pagination of results.
- How does system handle concurrent searches from multiple users? Single-user system queues requests to prevent resource exhaustion.
- What happens when query expansion finds no additional relevant terms? System proceeds with original query without expansion indicators.
- How does system handle documents that were deleted in SiYuan but still in index? System detects stale documents and removes them from results with re-indexing prompt.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide unified search interface accepting natural language queries in Russian or English
- **FR-002**: System MUST return top-12 documents ranked by relevance with title, snippet, confidence percentage, cache status, and date
- **FR-003**: System MUST display confidence scores (0-100%) with explanations of scoring factors when clicked
- **FR-004**: System MUST show multi-hop knowledge connections: parent, referenced, and sibling documents
- **FR-005**: System MUST provide instant cached results (<150ms) for repeated queries with cache badges and refresh options
- **FR-006**: System MUST include inline citations [Ref 1] linking to exact source locations with ≥98% precision
- **FR-007**: System MUST implement graceful degradation: LLM answers (>0.15 confidence), extracted QA (0.05-0.15), raw search (<0.05)
- **FR-008**: System MUST handle multilingual queries seamlessly without language selection
- **FR-009**: System MUST integrate with SiYuan via plugin showing search widget within SiYuan interface
- **FR-010**: System MUST display thinking traces showing reasoning process for high-confidence answers
- **FR-011**: System MUST provide seamless search experience without leaving SiYuan application
- **FR-011**: System MUST support query expansion showing related search terms and synonyms used in matching
- **FR-012**: System MUST provide result filtering by date range, document type, and confidence threshold
- **FR-013**: System MUST allow saving and organizing search results into custom collections
- **FR-014**: System MUST show search history with ability to re-run previous queries
- **FR-015**: System MUST provide export functionality for search results and citations in multiple formats

### Key Entities *(include if feature involves data)*

- **Document**: User knowledge base content with title, content, date, SiYuan block ID, language, tags, and metadata
- **Query**: Natural language search input with automatic language detection, expansion terms, and search history
- **Result**: Ranked document with confidence score, snippets, citations, connections, and cache status
- **Citation**: Exact character span reference to source document with precision tracking and validation
- **Connection**: Relationship between documents (parent, child, sibling) with semantic strength and connection type
- **Collection**: User-defined grouping of search results with name, description, and sharing options
- **SearchSession**: Query execution context with filters, sorting, and pagination state
- **CacheEntry**: Stored query results with timestamp, similarity score, and expiration metadata
- **ExportFormat**: Structured output format (JSON, Markdown, PDF) with citation and link preservation

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users find relevant documents in top 15 results for 90% of queries (Recall@15 ≥ 90%)
- **SC-002**: Citation sources accurately match claimed information ≥ 98% of the time
- **SC-003**: 90% of queries receive responses within 5-7 seconds end-to-end
- **SC-004**: 60-75% of repeated queries served from cache with <150ms latency
- **SC-005**: Users successfully find needed information 85% of the time
- **SC-006**: Confidence scores predict actual usefulness within ±5% accuracy
- **SC-007**: Researchers open 3+ linked documents and find answers within 2 minutes
- **SC-008**: Developers get working code snippets from personal notes within 30 seconds
- **SC-009**: All user personas achieve their success criteria in independent testing
- **SC-010**: System remains useful across all degradation levels (high/medium/low confidence)
- **SC-011**: Query expansion shows relevant synonyms/terms for 80% of searches
- **SC-012**: Result filtering reduces irrelevant results by 70% when applied
- **SC-013**: Saved collections maintain 95% of their relevance after 30 days
- **SC-014**: Search history allows successful re-execution of 95% of previous queries
- **SC-015**: Export functionality preserves formatting and links in 100% of cases
