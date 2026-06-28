# CLAUDE.md — Aether Clinician

## Project Overview

Aether Clinician is a clinician-facing diagnostic and management decision-support system (CDSS) built around a multi-agent diagnostic reasoning engine. It reads fragmented patient histories (paper prescriptions, lab PDFs, scanned reports), builds structured longitudinal records, asks clarifying questions like a specialist, and produces grounded differential diagnoses, drug-safety checks, and guideline-cited management options.

The core innovation is an orchestrated team of eight LLM-powered agents — specialist reasoning agents, a devil's-advocate agent, a verifier, and a "can't-miss" sentinel — that debate and cross-check each other before any clinical output reaches the clinician. Every clinical claim is traceable to patient data or a cited clinical guideline. The clinician is always the decision-maker; the system never prescribes, only supports.

---

## Tech Stack

| Layer                 | Technology                              | Notes                                                        |
| --------------------- | --------------------------------------- | ------------------------------------------------------------ |
| Monorepo              | Turborepo                               | Shared build/lint/test orchestration                         |
| Backend               | Python 3.12+ / FastAPI                  | Async, ML/AI integration, LangGraph compatibility            |
| Frontend              | Next.js 14 / React 18 / TypeScript      | App Router, server components where appropriate              |
| Database              | PostgreSQL 16                           | Relational store for patient graph + immutable audit log     |
| Vector Store          | Qdrant                                  | Guideline corpus RAG                                         |
| Cache                 | Redis 7                                 | Session cache, rate limiting, agent result caching            |
| AI/LLM                | Anthropic Claude                        | Primary LLM; multimodal for document extraction              |
| OCR Fallback          | Tesseract                               | When Claude vision extraction is insufficient                |
| Agent Orchestration   | LangGraph                               | Stateful graph orchestrator for the 8-agent reasoning engine |
| Auth                  | JWT + bcrypt                            | Email/password; demo mode has no credential gate             |
| File Storage          | Local filesystem + S3-compatible (MinIO)| MinIO for dev, S3-compatible for prod                        |

---

## Key Commands

```bash
# --- Monorepo (from project root) ---
turbo dev                        # Start all apps in dev mode
turbo build                      # Build all apps and packages
turbo lint                       # Lint all workspaces
turbo test                       # Run all tests
turbo typecheck                  # TypeScript type checking across workspaces

# --- Backend (from apps/api/) ---
uvicorn app.main:app --reload    # Start FastAPI dev server
pytest                           # Run Python tests
pytest --cov=app                 # Run with coverage
ruff check .                     # Lint Python code
ruff format .                    # Format Python code
mypy app/                        # Type-check Python code

# --- Frontend (from apps/web/) ---
npm run dev                      # Start Next.js dev server
npm run build                    # Production build
npm run lint                     # ESLint
npm run test                     # Vitest / Jest
npx tsc --noEmit                 # TypeScript check

# --- Database ---
alembic upgrade head             # Apply all migrations
alembic downgrade -1             # Rollback last migration
alembic revision --autogenerate -m "description"  # Generate migration

# --- Reasoning Engine (from services/reasoning/) ---
python -m pytest tests/          # Test agent orchestration
python -m reasoning.graph --dry-run  # Validate graph structure without LLM calls

# --- Infrastructure (dev) ---
docker compose up -d             # Start PostgreSQL, Redis, Qdrant, MinIO
docker compose down              # Tear down dev infrastructure
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    apps/web (Next.js 14)                     │
│   Reasoning Theatre UI  |  Patient Timeline  |  Intake Flow  │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST / WebSocket
┌──────────────────────────▼──────────────────────────────────┐
│                    apps/api (FastAPI)                         │
│   Auth  |  Patient CRUD  |  Document Upload  |  Encounter API│
└───┬──────────┬──────────────┬───────────────────────────────┘
    │          │              │
    ▼          ▼              ▼
┌────────┐ ┌──────────┐ ┌─────────────────────────────────────┐
│ PostgreSQL│ │ Redis    │ │ services/reasoning (LangGraph)     │
│ Patient  │ │ Cache    │ │                                     │
│ Graph +  │ │ Sessions │ │ ┌─────────┐  ┌──────────────────┐  │
│ Audit Log│ │          │ │ │Orchestr.│──│ Hypothesis Agents │  │
└────────┘ └──────────┘ │ │(Synth.) │  │ (specialist panel)│  │
                         │ └────┬────┘  └──────────────────┘  │
                         │      │                              │
                         │ ┌────▼────┐  ┌──────────────────┐  │
                         │ │Verifier │  │ Devil's Advocate  │  │
                         │ │(gatekpr)│  │ Can't-Miss Sentnl │  │
                         │ └─────────┘  └──────────────────┘  │
                         └──────┬──────────────────────────────┘
                                │
                  ┌─────────────▼─────────────┐
                  │ services/rag (Qdrant)       │
                  │ Guideline-RAG Agent         │
                  │ ICMR + WHO/NICE corpus      │
                  └─────────────────────────────┘
```

### Module Descriptions

- **`apps/web/`** — Next.js 14 frontend. Patient intake, document upload, longitudinal timeline, and the "Reasoning Theatre" UI that shows agent deliberation transparently. Anti-automation-bias UX: evidence is always shown before conclusions.

- **`apps/api/`** — FastAPI backend. REST endpoints for auth, patient CRUD, document ingestion, encounter management, and WebSocket channels for streaming reasoning output. All clinical outputs are immutably logged before reaching the frontend.

- **`services/reasoning/`** — LangGraph-based multi-agent reasoning engine. Contains the 8-agent graph definition, individual agent prompts, state schemas, and the autonomy-tier classification logic. This is the clinical brain.

- **`services/extraction/`** — Document processing pipeline. Handles PDF/image ingestion, Claude multimodal extraction, Tesseract OCR fallback, and structured data extraction into the patient graph.

- **`services/rag/`** — Guideline RAG service. Manages the Qdrant vector store, guideline ingestion pipeline, and the Guideline-RAG Agent's retrieval logic. Sources: ICMR Standard Treatment Workflows (spine), WHO Essential Medicines List, NICE guidelines.

- **`packages/shared-types/`** — Shared type definitions used by both TypeScript (frontend) and Python (backend). Canonical source for data model shapes.

- **`packages/ui/`** — Shared React component library. Design system components used across the web app.

- **`packages/config/`** — Shared ESLint, Prettier, TypeScript, and Ruff configurations.

- **`data/guidelines/`** — Curated clinical guideline corpus for RAG ingestion.

- **`data/drugs/`** — DrugVocabulary seed data. Indian brand name to generic name to reference ID mappings.

- **`data/migrations/`** — Alembic database migrations for PostgreSQL schema.

---

## Critical Safety Rules (NON-NEGOTIABLE)

These rules govern all code in this project. They are not optional, not overridable by feature flags, and not bypassable "just for testing." Violating any of these is a blocking defect.

### 1. Verifier Is Mandatory and Cannot Be Bypassed
Every clinical output (differential diagnoses, drug-safety checks, management suggestions) MUST pass through the Verifier Agent before reaching the clinician. There is no `skip_verification` flag, no admin override, no debug shortcut. If you find yourself writing code that routes clinical output around the Verifier, stop.

### 2. Conservative Output Wins on Disagreement
When agents disagree on risk level or autonomy tier, the MORE conservative classification always wins. A suggestion flagged as "flag-for-review" by any agent stays "flag-for-review" even if three other agents rated it "informational."

### 3. Allergy/Contraindication Conflicts Are Hard Blocks
If a suggested medication conflicts with a documented allergy or known contraindication, it MUST be hard-blocked. Not a warning, not a soft alert — a hard block that requires explicit clinician override with documented reasoning. This logic must work offline (deterministic, no LLM dependency).

### 4. No Certainty Language in Clinical Output
No diagnosis or management suggestion is ever presented as certain. Microcopy must be prescriber-framed: "Guidelines support considering X" — never "Give drug X" or "The patient has Y." Imperative clinical language is a bug.

### 5. Devil's-Advocate Dissent Is Always Shown
The Devil's-Advocate Agent's counter-argument is always displayed to the clinician. It cannot be hidden, collapsed-by-default, or deprioritized in the UI. This is an anti-automation-bias requirement.

### 6. Anti-Automation-Bias: Evidence Before Conclusion
In the Reasoning Theatre UI, evidence and reasoning steps are always shown BEFORE the conclusion. The UI must not lead with the answer and then justify it — this is a deliberate anti-automation-bias design choice.

### 7. ClinicalSuggestion Records Are Immutable
Once a `ClinicalSuggestion` is logged to the audit trail, it is never updated or deleted. No `UPDATE` or `DELETE` statements against `clinical_suggestions`. Corrections are new records that reference the original.

### 8. Offline Safety Checks Must Work Without LLM
Core record access and rule-based safety checks (allergy cross-checking, contraindication detection, drug interaction alerts) MUST work offline. These are deterministic checks against local data, not LLM calls. When offline, LLM features degrade gracefully with an "AI reasoning paused — offline" indicator.

---

## The 8-Agent Reasoning Engine

| #  | Agent                     | Role                                                                 | Key Constraint                                      |
| -- | ------------------------- | -------------------------------------------------------------------- | --------------------------------------------------- |
| 1  | Triage/Intake Agent       | Decides if enough info exists; generates clarifying questions         | Must not guess when data is missing                  |
| 2  | Hypothesis Agents (panel) | Role-primed specialists (IM, cardio, ID, primary care) generate DDx  | Each reasons independently before seeing others      |
| 3  | Can't-Miss Sentinel       | Scans for dangerous/time-critical "can't-miss" diagnoses             | Always runs; output always shown even if low-ranked  |
| 4  | Devil's-Advocate Agent    | Attacks the leading hypothesis with counter-evidence                 | Dissent is always displayed; cannot be suppressed    |
| 5  | Investigation Strategist  | Computes single most discriminating next test                        | Must justify information gain, not shotgun testing   |
| 6  | Guideline-RAG Agent       | Retrieves from curated guideline corpus; strictly grounded           | Cannot hallucinate guidelines; must cite source      |
| 7  | Verifier (gatekeeper)     | Re-checks every output; assigns autonomy tier; final gate            | CANNOT be bypassed; conservative classification wins |
| 8  | Synthesis/Orchestrator    | Reconciles all outputs; preserves disagreement; formats final output | Must surface disagreements, not hide them            |

### Autonomy Tiers

- **Informational** (low stakes) — facts, reference links, educational content
- **Suggestive** (moderate) — ranked options with cited evidence; clinician decides
- **Flag-for-review** (high stakes or low confidence) — requires active clinician engagement before proceeding

---

## Data Model

Core entities — refer to `packages/shared-types/` for canonical definitions:

| Entity              | Purpose                                                                   |
| ------------------- | ------------------------------------------------------------------------- |
| Patient             | Demographics, identifiers                                                 |
| Document            | Uploaded file metadata (PDF, image, prescription scan)                    |
| Encounter           | Clinical encounter record (visit, consultation)                           |
| MedicationEvent     | Prescription, administration, or discontinuation of a medication          |
| LabResult           | Lab test result with reference ranges                                     |
| Condition           | Diagnosed or suspected condition                                          |
| Allergy             | Known allergy or adverse reaction (critical for safety checks)            |
| DerivedMarker       | Computed clinical markers (eGFR, BMI, etc.)                               |
| ClinicalSuggestion  | Immutable record of any clinical suggestion made by the system            |
| DrugVocabulary      | Indian brand name to generic name to reference ID mapping                  |
| IntakeQuestion      | Generated clarifying question from Triage Agent                           |
| IntakeAnswer        | Clinician's response to an intake question                                |

---

## Module Patterns

### Adding a New Agent to the Reasoning Engine

1. Create the agent module in `services/reasoning/agents/your_agent.py`
2. Define the agent's state schema extending the shared `ReasoningState`
3. Write the agent's system prompt in `services/reasoning/prompts/your_agent.md`
4. Register the agent as a node in the LangGraph graph definition (`services/reasoning/graph.py`)
5. Define edges (what agents run before/after yours) in the graph
6. Add the agent's output to the Verifier's checklist — all clinical output must be verified
7. Write tests in `services/reasoning/tests/test_your_agent.py` including a test that confirms output routes through the Verifier
8. Update the Synthesis/Orchestrator to incorporate the new agent's output

### Adding a New API Endpoint

1. Create a router file in `apps/api/app/routers/your_resource.py`
2. Define Pydantic request/response models in `apps/api/app/schemas/your_resource.py`
3. Implement business logic in `apps/api/app/services/your_service.py` (keep routers thin)
4. Register the router in `apps/api/app/main.py`
5. If the endpoint touches clinical data, ensure the audit log records the action
6. Add tests in `apps/api/tests/test_your_resource.py`
7. Update shared types in `packages/shared-types/` if the frontend needs the new shapes

### Adding a New UI Screen

1. Create the page in `apps/web/src/app/(routes)/your-page/page.tsx` (App Router)
2. If it needs shared components, add them to `packages/ui/src/components/`
3. Use the shared types from `packages/shared-types/` for API response typing
4. If the screen displays clinical output, ensure:
   - Evidence is shown before conclusions (anti-automation-bias)
   - Devil's-advocate dissent is visible
   - Autonomy tier badges are displayed
   - No certainty language in any microcopy
5. Add the route to navigation and test with `npm run test`

### Adding a New Drug to the Vocabulary

1. Add entries to `data/drugs/` seed data (CSV or JSON format)
2. Map: Indian brand name -> generic name (INN) -> reference ID
3. Run the seed script to update the database
4. Verify allergy/contraindication cross-references resolve correctly

### Adding Guidelines to the RAG Corpus

1. Place source documents in `data/guidelines/`
2. Run the ingestion pipeline (`services/rag/ingest.py`) to chunk and embed
3. Each chunk must retain its source citation metadata (guideline name, section, page)
4. Verify retrieval quality with test queries in `services/rag/tests/`

---

## Code Conventions

### Python (Backend + Services)

- **Formatter/Linter:** Ruff (format + lint)
- **Type checking:** mypy with strict mode
- **Naming:** `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants
- **Async:** Use `async/await` throughout FastAPI handlers and service layer
- **Error handling:** Raise domain-specific exceptions (e.g., `PatientNotFoundError`, `VerificationFailedError`), catch at the router level with FastAPI exception handlers. Never swallow exceptions silently.
- **Pydantic:** All API boundaries use Pydantic v2 models for validation
- **Imports:** Use absolute imports from package root (`from app.services.patient import PatientService`)
- **Docstrings:** Required on all public functions; Google style

### TypeScript (Frontend)

- **Formatter/Linter:** Prettier + ESLint (shared config from `packages/config/`)
- **Naming:** `camelCase` for variables/functions, `PascalCase` for components/types, `UPPER_SNAKE_CASE` for constants
- **Components:** Functional components only; no class components
- **State management:** React Server Components where possible; client state with React hooks
- **API calls:** Centralized in `apps/web/src/lib/api/` with typed request/response wrappers
- **Error handling:** Error boundaries at route level; toast notifications for user-facing errors

### General

- **No `any` types** in TypeScript — use `unknown` and narrow
- **No bare `except:` / `except Exception:`** in Python without logging — always log the exception
- **File structure mirrors feature structure**, not technical layers (e.g., `patient/` contains model, service, router, and tests for patient)
- **Tests live next to the code they test** or in a parallel `tests/` directory — both patterns are acceptable, but be consistent within a module
- **Git commits:** Conventional Commits format (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`)
- **Branch naming:** `feat/short-description`, `fix/short-description`, `refactor/short-description`

---

## Environment Variables

```bash
# --- Application ---
APP_ENV=development                  # development | staging | production
APP_SECRET_KEY=                      # JWT signing secret (generate with: openssl rand -hex 32)
APP_DEBUG=true                       # Enable debug mode (never true in production)
DEMO_MODE=true                       # Show persistent demo banner; disable credential gate

# --- Database ---
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/aether_clinician
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# --- Redis ---
REDIS_URL=redis://localhost:6379/0

# --- Anthropic (LLM) ---
ANTHROPIC_API_KEY=                   # Required for all LLM features
ANTHROPIC_MODEL=claude-sonnet-4-20250514     # Default model for reasoning agents
ANTHROPIC_MAX_TOKENS=4096            # Default max tokens per agent call

# --- Qdrant (Vector Store) ---
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=guidelines         # Collection name for guideline corpus

# --- File Storage ---
S3_ENDPOINT_URL=http://localhost:9000  # MinIO for dev
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET_NAME=aether-documents

# --- OCR ---
TESSERACT_CMD=/usr/bin/tesseract     # Path to Tesseract binary (fallback OCR)

# --- Frontend (apps/web/.env.local) ---
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
NEXT_PUBLIC_DEMO_MODE=true
```

---

## Common Pitfalls

### 1. Bypassing the Verifier "just for testing"
Do not create test utilities or debug flags that skip the Verifier Agent. If you need to test individual agents in isolation, test their output format and content — but integration tests must always include the Verifier in the pipeline. If the Verifier is slow in tests, mock the LLM call but keep the verification logic.

### 2. Mutable ClinicalSuggestion records
Never write SQL that updates or deletes from `clinical_suggestions`. If a suggestion needs correction, insert a new record with a `supersedes_id` pointing to the original. The Alembic migration framework should not generate `DROP` or `ALTER` statements on this table's data columns.

### 3. Imperative clinical language in microcopy
All user-facing clinical text must be prescriber-framed. Grep for patterns like "Give ", "Administer ", "The patient has ", "Diagnose with " — these are bugs. Correct forms: "Guidelines support considering...", "Evidence suggests...", "Consider evaluating for...".

### 4. Drug name resolution shortcuts
Never match drug names by string equality. Always resolve through the DrugVocabulary pipeline: Indian brand name -> generic name (INN) -> reference ID. A patient's allergy to "Crocin" must match against "Paracetamol" / "Acetaminophen" via the vocabulary.

### 5. Forgetting offline safety checks
Allergy cross-checks, contraindication detection, and drug interaction alerts are deterministic and must not depend on LLM availability. If you add a new safety check, ask: "Does this work when the network is down?" If the answer is no, it needs a local/deterministic fallback.

### 6. Hiding agent disagreement in the UI
The Reasoning Theatre must show all agent perspectives, especially dissent. Do not collapse, truncate, or visually deprioritize the Devil's-Advocate Agent's output. Do not sort agents by "confidence" in a way that pushes dissent to the bottom.

### 7. Evidence-after-conclusion ordering in UI
The anti-automation-bias requirement means evidence must appear BEFORE the conclusion in the rendering order. If you are building a component that shows a diagnosis with supporting evidence, the evidence section must render first. This is counterintuitive for typical UI patterns — it is intentional.

### 8. Async/await consistency in FastAPI
All database operations and external API calls must be async. Mixing sync and async calls in a handler will block the event loop. Use `asyncpg` for database access, `httpx.AsyncClient` for HTTP calls.

### 9. DPDP Act compliance
This system targets India. Patient data handling must comply with the Digital Personal Data Protection Act. Key points: explicit consent for data processing, data minimization, purpose limitation, and data residency requirements (data must stay in India in production). Do not add analytics or telemetry that sends patient data outside India.

### 10. Demo mode is not "no security"
Demo mode (`DEMO_MODE=true`) removes the credential gate for easy access but does NOT disable auth, audit logging, or safety checks. All clinical safety rules apply in demo mode. The demo banner must be persistently visible so users never mistake it for a production system.

---

## Project Phasing

For context on what to build when:

- **Phase 1:** Auth, document ingestion, longitudinal patient graph, deterministic safety checks (allergy/contraindication/interaction), audit log
- **Phase 2:** Multi-agent reasoning engine, Reasoning Theatre UI, anti-automation-bias UX patterns, export functionality
- **Phase 3:** Guideline RAG with cited management options, ICMR/WHO/NICE corpus integration
- **Phase 4:** Validation instrumentation, CDSCO SaMD regulatory pathway, monitored clinical pilot

---

## India-Specific Context

- **Regulatory:** CDSCO SaMD (Software as Medical Device) pathway governs this product class
- **Privacy:** Digital Personal Data Protection (DPDP) Act 2023 — consent-first, data residency in India
- **Drug vocabulary:** Indian brand names (Crocin, Dolo, Augmentin, etc.) must resolve to INN generics
- **Guidelines:** ICMR Standard Treatment Workflows are the primary guideline spine; supplemented by WHO and NICE
- **Language:** English-first interface; Hindi/regional language support is a future consideration
