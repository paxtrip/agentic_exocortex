<!-- Sync Impact Report
Version change: 0.0.0 → 1.0.0
List of modified principles: All principles added (new constitution)
Added sections: Core Principles (12 principles), Additional Constraints, Development Workflow, Governance
Removed sections: None
Templates requiring updates: None - templates are generic
Follow-up TODOs: None
-->

# Agentic_Exocortex Constitution

## Core Principles

### 1. Privacy Without Compromise
Raw user data NEVER leaves the server; Only anonymized, decontextualized summaries sent to LLM; System must operate fully offline (no internet required); User can delete all data instantly.

- Raw user data must never be transmitted to external services
- All LLM interactions use only decontextualized, anonymized summaries
- System must function completely offline without internet connectivity
- Instant data deletion capability must be available to users

### 2. Honesty Over Performance
When uncertain, system says "I don't know" instead of guessing; Confidence scores must be honest and calibrated; Citations must be precise (to character span); No hallucinated facts.

- Uncertainty must be explicitly communicated rather than guessed
- Confidence scores must reflect true probability of correctness
- Citations must reference exact character spans in source documents
- System must never generate information not present in source data

### 3. Graceful Degradation (3 Levels)
Level 1 (Full): RAG + LLM generation with thinking trace + citations; Level 2 (Partial): Extractive QA from matched documents; Level 3 (Basic): Ranked search results for user synthesis; System is useful at every level.

- Full functionality includes RAG, LLM generation, thinking traces, and citations
- Partial functionality provides extractive question answering from matched documents
- Basic functionality delivers ranked search results for manual synthesis
- Each degradation level maintains system usefulness

### 4. Search Quality Targets
Recall@15 ≥ 90%; Citation Precision ≥ 98%; Latency E2E (LLM) < 5-7 seconds; Latency E2E (cached) < 150 milliseconds; Cache hit-rate 60-75%.

- Recall at 15 results must be at least 90%
- Citation precision must exceed 98%
- End-to-end latency for LLM responses must be under 5-7 seconds
- Cached response latency must be under 150 milliseconds
- Cache hit rate must be between 60-75%

### 5. Russian as First-Class Language
Russian support NOT afterthought; Lemmatization mandatory (pymorphy3); Test corpus minimum 50% Russian queries; All metrics validated on Russian data.

- Russian language support must be primary, not secondary
- Lemmatization using pymorphy3 is required for Russian text processing
- Test datasets must include at least 50% Russian language queries
- All performance metrics must be validated on Russian language data

### 6. Cost Model: Zero API, Self-Hosted
No vendor lock-in (only free tier APIs); Deployable on 4vCPU / 8GB RAM VPS ($10-20/month); Docker Compose stack with Traefik reverse proxy.

- No dependency on paid API services or vendor lock-in
- System must deploy on standard VPS with 4vCPU and 8GB RAM
- Docker Compose deployment with Traefik reverse proxy required
- Monthly hosting cost must not exceed $10-20

### 7. Modular, Composable Design
Each component has clear interface (API, CLI); Can swap embeddings without rewriting search; Can change LLM providers without code changes; BGE-M3 unified hybrid as baseline.

- All components must expose clear API and CLI interfaces
- Embedding models must be swappable without search logic changes
- LLM providers must be interchangeable without code modifications
- BGE-M3 hybrid embeddings serve as the baseline implementation

### 8. Testing-First Discipline
No code without failing test first (TDD); Golden dataset: 100+ queries with expected results; Benchmark queries in Russian + English; RAGAS metrics for every generation.

- All code must follow Test-Driven Development with failing tests first
- Golden test dataset must contain over 100 queries with expected results
- Benchmark queries must cover both Russian and English languages
- RAGAS evaluation metrics must be computed for every generation

### 9. Code Quality Standards
EVERY comment and docstring MUST be bilingual (RU + EN); Comments must explain WHY, not just WHAT; Use real-world analogies for complex concepts; Error handling must be documented.

- All comments and docstrings must be provided in both Russian and English
- Comments must explain reasoning and purpose, not just functionality
- Complex concepts must be explained using real-world analogies
- Error handling logic must be thoroughly documented

### 10. SiYuan Integration
SiYuan is user's note-taking app (like Notion); Exocortex fetches notes every 30 seconds via API; Results must include "Open in SiYuan" link; Explain integration in code comments.

- SiYuan serves as the primary note-taking application for users
- Notes must be fetched from SiYuan via API every 30 seconds
- Search results must include direct links to open documents in SiYuan
- Integration details must be explained in code comments

### 11. Localization
All UI strings from locales/ru.json and locales/en.json; Default language = Russian (user can switch to English); No hardcoded strings in code.

- All user interface strings must be sourced from localization files
- Localization files must exist for both Russian and English
- Russian must be the default language with English as an option
- No hardcoded text strings are permitted in source code

### 12. Observability & Documentation
All responses JSON with trace_id; Health checks every 30 seconds; Daily snapshots of vector store + database; README and API docs in Russian + English.

- All system responses must be JSON format with trace_id included
- Health checks must run every 30 seconds
- Daily snapshots of vector store and database must be created
- Documentation must be provided in both Russian and English

## Additional Constraints

Technology stack requirements: Python-based with pymorphy3 for Russian processing, BGE-M3 embeddings, Docker Compose deployment, Traefik reverse proxy.

Compliance standards: GDPR-compliant data handling, offline-first architecture, zero external API dependencies for core functionality.

Deployment policies: Self-hosted only, no cloud vendor lock-in, standard VPS compatibility (4vCPU/8GB RAM).

## Development Workflow

Code review requirements: All changes must pass constitution compliance checks, bilingual documentation mandatory.

Testing gates: TDD mandatory, RAGAS metrics validation, Russian language corpus testing (minimum 50%).

Deployment approval process: Constitution compliance verification required before deployment.

## Governance

Constitution supersedes all other practices; Amendments require documentation, approval, migration plan.

All PRs/reviews must verify compliance; Complexity must be justified; Use constitution.md for runtime development guidance.

**Version**: 1.0.0 | **Ratified**: 2025-10-17 | **Last Amended**: 2025-10-17
