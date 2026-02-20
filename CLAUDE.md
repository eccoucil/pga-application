# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**PGA (Policy Gap Analysis)** is a compliance analysis application for BNM RMIT and ISO 27001:2022 standards. It provides tools for managing policy documents, knowledge graphs, and semantic search across compliance frameworks.

## Development Commands

```bash
# Full stack (starts Docker, backend, frontend together)
./start.sh

# Backend only (FastAPI on port 8001)
cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Frontend only (Next.js on port 3001)
cd frontend && npm run dev -- -p 3001

# Docker services (Qdrant + Neo4j)
cd backend && docker-compose up -d

# Full-stack Docker (production)
docker compose up --build

# Full-stack Docker (dev with hot reload)
docker compose --profile dev up

# Backend tests
cd backend && uv run pytest

# Single backend test file
cd backend && uv run pytest tests/test_assessment.py -v

# Single test function
cd backend && uv run pytest tests/test_assessment.py::test_health_check -v

# Install dev dependencies (required before running tests)
cd backend && uv sync --extra dev

# Backend linting
cd backend && uv run ruff format . && uv run ruff check --fix .

# Frontend lint
cd frontend && npm run lint
```

## Architecture

### Backend Stack

- **FastAPI** with `asynccontextmanager` lifespan (not deprecated `on_event`)
- **Supabase** (PostgreSQL + Auth + RLS) — backend uses **service key** (bypasses RLS)
- **Qdrant** — vector DB, collection `"pga_documents"`, 1536-dim cosine (matches `text-embedding-3-small`). Also has **pgvector** alternative via `SupabaseVectorService` (migration 015, `document_chunks` table)
- **Neo4j** 5.15 with APOC — graph DB for organization/asset relationships
- **uv** as package manager (not pip): `uv run <command>`, `uv sync`

### Backend Key Files

- **config.py** — Pydantic settings management (loads from `.env`). Default Claude model: `claude-sonnet-4-20250514`.
- **auth/dependencies.py** — Supabase JWT validation (`get_current_user` dependency). Supports both ES256 (JWKS) and HS256 (legacy). Returns `{"user_id", "email", "role"}`.
- **db/supabase.py** — Database client creation (see Gotchas below)
- **routers/framework_docs.py** — CRUD for ISO 27001 and BNM RMIT controls. Reads/writes markdown files from `docs/framework/` as authoritative source. Prefix: `/framework-docs`.

### Backend Services (`backend/app/services/`)

- **assessment_orchestrator.py** — Lightweight coordination (no LLM, pure Python). Receives multipart submissions, runs document processing + web crawling in parallel via `asyncio.gather()`. 5-minute timeout.
- **questionnaire_agent.py** — Conversational Claude agent using `tool_use` interview loop with two tools: `askQuestionToMe` (ask user) and `generateQuestionnaire` (trigger batch generation). Processes controls in batches of 15.
- **web_crawler_agent.py** / `app/services/web_crawler/` — CRAWL4AI web intelligence extraction with parallel sub-agents. Refactored into a package with `BaseLLMExtractor` ABC template method pattern.
- **neo4j_service.py** — Graph operations (Company, DigitalAsset, Policy, Document nodes)
- **qdrant_service.py** — Vector search. Uses `AsyncQdrantClient` with `query_points` (not `search`).
- **embedding_service.py** — OpenAI `text-embedding-3-small` embeddings
- **question_swarm.py** — 4-agent parallel question generation. Round-robin distributes controls across `WorkerAgent` instances via `asyncio.gather()`. Exploits Anthropic prompt caching — shared context (org info, criteria, JSON schema) marked `cache_control: {"type": "ephemeral"}` is identical across all workers, yielding ~90% input token discount on workers 2-4. `generate_stream()` yields SSE events via `asyncio.Queue` with 180s per-agent timeout.
- **supabase_vector_service.py** — pgvector-based vector search (alternative to Qdrant). Uses `document_chunks` table with `vector(1536)` and RPC functions `match_document_chunks`/`match_client_extractions`.
- **document_analyzer.py** — Claude-powered policy document analyzer. Classifies documents by `PolicyType` (15 enum values) and maps to ISO 27001 / BNM RMIT controls.

### Assessment Flow (data pipeline)

1. **Router** (`POST /assessment/submit`): Accepts `multipart/form-data` (NOT JSON). Flat form fields + optional file uploads.
2. **Orchestrator**: Creates Organization node in Neo4j first, then runs in parallel:
   - Document processing (LlamaExtract if `LLAMA_CLOUD_API_KEY` set, else `DocumentTextExtractor` fallback for PDF/DOCX/XLSX/CSV/TXT)
   - Web crawling (only if `web_domain` provided)
3. **Persistence**: Best-effort — catches exceptions and logs warnings rather than failing the request.
4. **Knowledge graph**: Builds React Flow-compatible graph with radial layout (center=Organization, radius=250).

### Assessment Payload (`POST /assessment/submit`)

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `client_id` | string | Yes | UUID |
| `project_id` | string | Yes | UUID |
| `organization_name` | string | Yes | - |
| `nature_of_business` | string | Yes | min 10 chars |
| `industry_type` | IndustryType | Yes | Enum value |
| `department` | string | Yes | - |
| `scope_statement_isms` | string | Yes | min 10 chars |
| `web_domain` | string | No | Domain format if provided |
| `documents` | File[] | No | PDF, DOCX, TXT, XLSX, CSV |

### Questionnaire Conversational Flow

Two generation paths:

1. **Conversational** (`POST /questionnaire/generate-question` → `POST /questionnaire/respond` loop): Claude uses `askQuestionToMe` tool to ask clarifying questions. User answers are wrapped as `tool_result` messages. When Claude calls `generateQuestionnaire`, batch generation starts.

2. **Wizard/batch** (`POST /questionnaire/generate-with-criteria`): All criteria provided upfront, skips conversation.

3. **Streaming wizard** (`POST /questionnaire/generate-with-criteria-stream`): Same as wizard but returns SSE (`StreamingResponse`). Events: `progress` (per-batch), `agent_complete` (per-worker), `complete` (full result), `error`. Uses the 4-agent `QuestionGenerationSwarm`. Frontend hook `useQuestionnaireAgent` tracks per-agent status via `agentProgress` map.

**Session retrieval**: `GET /questionnaire/sessions?project_id=X&assessment_id=Y` (list) and `GET /questionnaire/sessions/{session_id}` (full detail).

Context fetching is two-phase parallel: (project + findings + crawl results) then (client info + framework controls conditional on selected frameworks). Neo4j and Qdrant context are optional/non-blocking.

### Frontend Stack

- **Next.js 15** with App Router, **React 19**, **TypeScript** (strict mode)
- **Tailwind CSS 4** with `@tailwindcss/postcss`
- **@xyflow/react** v12 for knowledge graph visualization
- **Radix UI** primitives (dialog, select, checkbox, dropdown, popover, toast)
- **lucide-react** for icons (primary), **@heroicons/react** (secondary)
- **react-markdown** for rich text rendering
- **Jest** + **@testing-library/react** for frontend tests
- Path alias: `@/*` → `./src/*`

### Frontend State Management

Five React contexts, nested in this order (order matters for dependencies):

```
ThemeProvider
  AuthProvider
    ClientProvider              ← auto-clears when navigating away from /clients/...
      ClientMembershipProvider  ← depends on AuthContext + ClientContext
        ProjectProvider         ← auto-clears when URL doesn't match /clients/[id]/projects/[projectId]
```

Permissions are calculated client-side from role: `viewer` (view only) → `member` (+write) → `admin` (+manage) → `owner` (all).

### Frontend API Patterns

- **Supabase direct**: `frontend/src/lib/supabase.ts` is a ~300-line data access layer with CRUD functions for clients, projects, profiles. Uses `client_members!inner` join for multi-tenant visibility.
- **Backend API**: No centralized API client. Each feature uses raw `fetch()` with `Authorization: Bearer` headers from `supabase.auth.getSession()`. See `use-questionnaire-agent.ts` as the pattern.

### Frontend Routes

- `/login` — Supabase email/password auth (also handles sign-up; redirects authenticated users)
- `/clients` — Client management with CRUD (also accessible via `/organizations`)
- `/clients/[id]/projects` — Project listing
- `/clients/[id]/projects/[projectId]/assessment` — Multi-step assessment (stepper UI)
- `/clients/[id]/projects/[projectId]/findings` — Results with knowledge graph
- `/clients/[id]/projects/[projectId]/controls` — Unified ISO 27001 controls (Annex A + management clauses merged)
- `/clients/[id]/projects/[projectId]/bnm-rmit` — BNM RMIT requirements

### Database Schema

**Supabase tables** (with Row Level Security):
- `clients` — Client organizations (**Note**: `name` = company name, `company` = contact person)
- `projects` — `framework` field is `string[] | null` (multi-framework)
- `client_members` — Multi-tenant membership with roles (owner/admin/member/viewer)
- `assessments` — Assessment records with auto-incrementing `version` per project (migration 012)
- `questionnaire_sessions` — Completed sessions persisted with `generated_questions`, `agent_criteria`, `conversation_history` as JSONB. Has `assessment_id` FK, plus `pending_tool_use_id`/`started_at_ms` for surviving backend restarts.
- `profiles` — User profiles (auto-created by trigger on sign-up): `full_name`, `organization`, `phone`, `job_title`
- `document_chunks` — pgvector-powered chunks with `vector(1536)` columns (migration 015)
- `gap_analysis_findings`, `project_documents`, `web_crawl_results`
- `iso_requirements`, `bnm_rmit_requirements`, `compliance_mapping`

**Neo4j nodes**: `Company`, `DigitalAsset` (with `HAS_ASSET` relationships), `Policy`, `Document`

**Migrations** in `migrations/` — Run manually against Supabase SQL editor.

## Key Patterns

### Compliance Levels
- `compliant` — Policy explicitly addresses all control aspects
- `partially_compliant` — Policy exists but has gaps
- `non_compliant` — Policy contradicts requirements
- `not_assessed` — Insufficient evidence

### Framework Identifiers
- ISO 27001: `identifier` like "A.5.1", "A.8.34" (Annex A) or clauses 4-10 (management)
- BNM RMIT: `reference_id` like "8.1", `section_number` for numeric sorting

### UI Styling
- Light/dark mode via `ThemeContext` (persists to localStorage), uses Tailwind `dark:` variants
- Custom classes: `cyber-gradient-bg`, `cyber-grid-dark`, `glow-effect`, `text-glow`
- Button variant: `cyber` (cyan gradient)
- Sidebar: Collapsible icon rail (16px collapsed, 56px expanded on hover)

### Testing
- Auth mocking: `app.dependency_overrides[get_current_user] = mock_get_current_user` at module level
- Use `reset_orchestrator()` in fixtures for test isolation
- No `conftest.py` — each test file sets up its own mocks
- Pre-existing failure in `test_assessment.py` (LlamaExtract conflict) — not a regression

## Gotchas

### Supabase Client — Two Async Functions
- `get_async_supabase_client()` — uses `asyncio.run()`, **cannot be called from within an async context**. Will raise `RuntimeError`.
- `get_async_supabase_client_async()` — the correct one for async endpoints. Always use this one.
- Both use `supabase_service_key` (bypasses RLS). Sync `get_supabase_client()` also exists for specific sync paths.

### In-Memory State
Both the orchestrator (`active_assessments` dict) and questionnaire agent (`_sessions` dict) store state in memory. **Server restarts lose all active sessions.** Completed questionnaire sessions are persisted to Supabase, active conversations are not.

### CORS
Configurable via `CORS_ORIGINS` env var (comma-separated). Defaults to `http://localhost:3001`. Set in `config.py`, split by comma in `main.py`.

### Graceful Degradation
The app starts even if Neo4j/Qdrant Docker services are down. `GET /health` returns `"degraded"` status. Services that depend on them will fail at call time, not at startup.

### Assessment Endpoint is Form-Data
`POST /assessment/submit` uses `Form(...)` and `File(...)` parameters, NOT a JSON body. Frontend must send `multipart/form-data`.

### Questionnaire Agent HTTP Client
Forces HTTP/1.1 (`http2=False`) to avoid Mac connection issues. Custom timeout: 600s total (30s connect, 570s read). Retries on `RateLimitError`/`APITimeoutError` with exponential backoff (3 attempts).

## Service URLs (Development)

**Note:** Docker services use non-standard ports to avoid conflicts.

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3001 |
| Backend API | http://localhost:8001 |
| Swagger Docs | http://localhost:8001/docs |
| Qdrant Dashboard | http://localhost:16333/dashboard |
| Neo4j Browser | http://localhost:17474 |
| Neo4j Bolt | bolt://localhost:17687 |

## Environment Variables

**Backend** (`backend/.env`):
```
SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY
ANTHROPIC_API_KEY
OPENAI_API_KEY
NEO4J_URI=bolt://localhost:17687
NEO4J_USER=neo4j
NEO4J_PASSWORD
QDRANT_HOST=localhost
QDRANT_PORT=16333
CORS_ORIGINS=http://localhost:3001  # comma-separated for multiple
```

**Frontend** (`frontend/.env.local`):
```
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_ANON_KEY (or NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY)
NEXT_PUBLIC_API_URL=http://localhost:8001
```
