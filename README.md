# PGA - Policy Gap Analysis

A compliance analysis application for **BNM RMIT** and **ISO 27001:2022** standards. PGA uses AI-powered analysis to identify gaps between organizational policies and regulatory requirements.

## Features

- **Document Analysis**: Upload and analyze organizational policy documents (PDF, DOCX, XLSX, CSV, TXT)
- **Questionnaire Generation**: AI-generated compliance assessment questions covering all ISO 27001 controls (93 Annex A + 23 management clauses) and BNM RMIT requirements (121 entries). Uses a 6-agent parallel swarm with prompt caching for fast generation.
- **Gap Identification**: AI-powered identification of compliance gaps with compliance levels (compliant, partially compliant, non-compliant, not assessed)
- **Semantic Search**: Search across policies using natural language (Qdrant vector DB + pgvector alternative)
- **Knowledge Graph**: Visual representation of organization, digital asset, policy, and document relationships with interactive info banner and legend
- **Web Crawling**: Discover digital assets and extract business context from organization websites using CRAWL4AI with parallel sub-agents
- **Multi-Tenant Teams**: Role-based access control (owner/admin/member/viewer) with Row Level Security
- **Multi-Framework Support**: BNM RMIT and ISO 27001:2022 compliance checking
- **Multi-Department Selection**: Assess multiple departments simultaneously within an organization

## Tech Stack

### Backend
- **FastAPI** - High-performance Python web framework with async support
- **Supabase** - PostgreSQL database, authentication, and Row Level Security
- **Qdrant** - Vector database for semantic search (1536-dim, cosine similarity)
- **Neo4j 5.15** - Graph database with APOC for organization/asset relationships
- **Claude AI** (Sonnet 4 / Haiku) - Question generation, document analysis, web intelligence
- **OpenAI** - Text embeddings (`text-embedding-3-small`)
- **uv** - Python package manager

### Frontend
- **Next.js 15** - React framework with App Router
- **React 19** - UI library with strict TypeScript
- **Tailwind CSS 4** - Utility-first styling with dark mode
- **@xyflow/react v12** - Knowledge graph visualization
- **Radix UI** - Accessible component primitives
- **Supabase JS** - Client SDK for database and auth

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Docker** and **Docker Compose**
- **uv** - Python package manager ([install guide](https://docs.astral.sh/uv/getting-started/installation/))

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd pga-application
```

### 2. Set Up Backend

```bash
cd backend

# Install dependencies
uv sync

# Copy environment template and configure
cp .env.example .env
# Edit .env with your API keys and database credentials
```

### 3. Set Up Frontend

```bash
cd frontend

# Install dependencies
npm install

# Copy environment template and configure
cp .env.example .env.local
# Edit .env.local with your Supabase credentials
```

### 4. Run Database Migrations

Run all SQL migrations (001-017) against your Supabase SQL editor. Migration 017 is critical — it seeds the `iso_requirements` table (116 ISO 27001 controls) and `bnm_rmit_requirements` table (121 BNM RMIT requirements).

```bash
# Migrations are in the migrations/ directory
# Copy-paste each .sql file into Supabase SQL Editor and run in order
```

### 5. Start Docker Services

```bash
cd backend
docker-compose up -d
```

This starts:
- **Qdrant** on port 16333 (non-standard to avoid conflicts)
- **Neo4j** on ports 17474 (browser) and 17687 (bolt)

## Configuration

### Backend Environment Variables (`backend/.env`)

```env
# AI Services
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENAI_API_KEY=your_openai_api_key

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_key

# Neo4j (non-standard ports to avoid conflicts)
NEO4J_URI=bolt://localhost:17687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Qdrant (non-standard port)
QDRANT_HOST=localhost
QDRANT_PORT=16333

# Optional
LLAMA_CLOUD_API_KEY=             # enables LlamaExtract for document parsing
QUESTION_GENERATION_MODEL=       # e.g., claude-haiku-4-20250514 for faster question gen
CORS_ORIGINS=http://localhost:3001  # comma-separated for multiple origins
```

### Frontend Environment Variables (`frontend/.env.local`)

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
NEXT_PUBLIC_API_URL=http://localhost:8001
```

## Running the Application

### Option 1: Full Stack (Recommended)

```bash
./start.sh
```

### Option 2: Run Services Separately

**Backend:**
```bash
cd backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

**Frontend:**
```bash
cd frontend
npm run dev -- -p 3001
```

## Accessing the Application

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3001 |
| Backend API | http://localhost:8001 |
| API Documentation | http://localhost:8001/docs |
| Neo4j Browser | http://localhost:17474 |
| Qdrant Dashboard | http://localhost:16333/dashboard |

## API Overview

### Assessment (mounted)
- `POST /assessment/submit` - Submit assessment (multipart/form-data)
  - Required: `client_id`, `project_id`, `organization_name`, `nature_of_business` (min 10 chars), `industry_type`, `department` (comma-separated for multiple), `scope_statement_isms` (min 10 chars)
  - Optional: `web_domain`, `documents` (PDF, DOCX, TXT, XLSX, CSV)
- `GET /assessment/status/{assessment_id}` - Get assessment processing status

### Questionnaire (mounted)
- `POST /questionnaire/generate-question` - Start conversational question generation
- `POST /questionnaire/respond` - Respond to a conversational question
- `POST /questionnaire/generate-with-criteria` - Batch generation (all criteria upfront)
- `POST /questionnaire/generate-with-criteria-stream` - Streaming batch generation (SSE)
- `GET /questionnaire/sessions` - List sessions (`?project_id=X&assessment_id=Y`)
- `GET /questionnaire/sessions/{session_id}` - Get full session detail

### Framework (mounted)
- `GET /framework/iso27001/sections` - ISO 27001 control sections
- `GET /framework/bnm-rmit/*` - BNM RMIT framework data

### Framework Docs (mounted)
- `GET /framework-docs/annex-a` - ISO 27001 Annex A controls (93 controls)
- `GET /framework-docs/management-clauses` - ISO 27001 management clauses (4.1-10.2)
- `GET /framework-docs/bnm-rmit` - BNM RMIT requirements

### Search (not mounted)
- `POST /search/semantic` - Semantic search across policies
- `GET /search/stats` - Search statistics

### Knowledge (not mounted)
- `GET /knowledge/graph` - Get policy relationship graph
- `GET /knowledge/gaps` - Get identified compliance gaps

### Health
- `GET /health` - API health check (Supabase only)

## Development

### Running Tests

**Backend:**
```bash
cd backend
uv run pytest
```

**Frontend:**
```bash
cd frontend
npm test
```

### Code Formatting

**Backend:**
```bash
cd backend
uv run ruff format .
uv run ruff check --fix .
```

**Frontend:**
```bash
cd frontend
npm run lint
npm run format
```

## Project Structure

```
pga-application/
├── backend/
│   ├── app/
│   │   ├── auth/         # Authentication (Supabase JWT validation, ES256 + HS256)
│   │   ├── db/           # Database connections (async Supabase clients)
│   │   ├── models/       # Pydantic models (assessment, questionnaire, knowledge_graph)
│   │   ├── routers/      # API routes (assessment, framework, framework_docs, questionnaire)
│   │   ├── services/     # Business logic
│   │   │   ├── assessment_orchestrator.py   # Coordination (no LLM)
│   │   │   ├── questionnaire_agent.py       # Conversational Claude agent
│   │   │   ├── question_swarm.py            # 6-agent parallel generation
│   │   │   ├── question_swarm_prompts.py    # Prompt templates (50-word limit)
│   │   │   ├── document_analyzer.py         # Claude-powered policy classifier
│   │   │   ├── document_text_extractor.py   # Fallback PDF/DOCX/XLSX extraction
│   │   │   ├── neo4j_service.py             # Graph operations
│   │   │   ├── qdrant_service.py            # Vector search
│   │   │   ├── embedding_service.py         # OpenAI embeddings
│   │   │   ├── supabase_vector_service.py   # pgvector alternative
│   │   │   └── web_crawler/                 # 13-module CRAWL4AI package
│   │   ├── config.py     # Pydantic settings (incl. question_generation_model)
│   │   └── main.py       # FastAPI app, mounts 4 routers
│   ├── tests/            # Backend tests (assessment, orchestrator, swarm)
│   ├── pyproject.toml    # Dependencies managed by uv
│   └── Dockerfile        # 3-stage build (builder, dev, production)
├── frontend/
│   ├── src/
│   │   ├── app/          # Next.js App Router pages
│   │   │   └── clients/[id]/projects/[projectId]/  # assessment, findings, controls, bnm-rmit
│   │   ├── components/   # React components by feature
│   │   │   ├── assessment/      # Form, history, questionnaire (incl. GeneratedQuestionsPanel)
│   │   │   ├── clients/         # CRUD, modals, tables
│   │   │   ├── framework/       # Editable control cards
│   │   │   ├── knowledge-graph/ # ContextNodesGraph (with info banner + legend)
│   │   │   ├── layout/          # Dashboard, sidebar, header
│   │   │   └── ui/              # Radix primitives (date-picker, dialog, select, etc.)
│   │   ├── contexts/     # 5 providers (Theme, Auth, Client, ClientMembership, Project)
│   │   ├── hooks/        # use-questionnaire-agent.ts, use-toast.ts
│   │   └── lib/          # supabase.ts (data access layer), utils.ts
│   ├── package.json
│   └── .env.local
├── migrations/           # 017 SQL migrations (run manually in Supabase SQL editor)
├── docs/                 # Framework documentation (ISO 27001, BNM RMIT)
├── docker-compose.yml    # Production + dev profiles
├── start.sh              # Full-stack launcher
├── CLAUDE.md             # Claude Code project guidance
└── README.md
```

## Compliance Frameworks

### BNM RMIT
Bank Negara Malaysia's Risk Management in Technology (RMIT) policy document covering:
- Technology risk governance
- Technology operations management
- Cybersecurity management
- Technology audit

### ISO 27001:2022
International standard for information security management systems (ISMS) covering:
- Organizational controls
- People controls
- Physical controls
- Technological controls

## AI Agents

### Question Generation Swarm

Generates compliance assessment questions using a **6-agent parallel swarm** with Anthropic prompt caching:

- Controls are sorted hierarchically: management clauses (4.1-10.2) first, then Annex A (A.5.1-A.8.34)
- Each question is limited to 50 words, targeting one specific control aspect
- Batch size of 20 controls per worker, 120s timeout per agent
- Prompt caching gives ~90% input token discount on workers 2-6

**Coverage:**
- ISO 27001: 116 controls (23 management clauses + 93 Annex A)
- BNM RMIT: 121 requirements (sections 8-18)

**Generation paths:**
1. **Conversational**: Claude asks clarifying questions, then generates
2. **Batch**: All criteria upfront, skips conversation
3. **Streaming batch**: Same as batch but returns SSE events for real-time progress

### Document Intake

Processes uploaded policy documents:
- Supports PDF, DOCX, XLSX, PPTX, TXT, XLS, CSV
- LlamaExtract (if API key set) or fallback `DocumentTextExtractor`
- Claude-powered policy classification into 15 `PolicyType` categories

### Assessment Orchestrator

Lightweight coordination agent (no LLM, pure Python):
- Receives assessment submissions via `/assessment/submit`
- Validates organization info (including required `scope_statement_isms`)
- Supports multi-department selection (comma-separated)
- Runs document processing + web crawling in parallel via `asyncio.gather()`
- 5-minute timeout, best-effort persistence

### Web Crawler Agent

CRAWL4AI-powered web intelligence extraction with parallel sub-agents:

**Sub-Agents (run in parallel):**
- **CrawlCoordinator** - URL discovery and crawling strategy
- **BusinessContextAnalyzer** - Extracts company info with grounding sources
- **AssetDiscoveryAgent** - Identifies subdomains, portals, APIs
- **OrganizationInfoExtractor** - Extracts contacts, certifications, partnerships

**Anti-Hallucination Measures:**
- All extractions require `grounding_source` (URL + quoted text)
- 95% confidence threshold using multi-factor scoring
- Cross-validation across multiple pages

**Storage:**
- **Supabase** - Crawl results (JSONB for business context, assets, org info)
- **Neo4j** - Company and DigitalAsset nodes with HAS_ASSET relationships
- **Qdrant** - Embedded content for semantic search

## Database Schema

### Supabase Tables (with Row Level Security)
- `clients` — Client organizations (`name` = company name, `company` = contact person)
- `projects` — `framework` field is `string[] | null` (multi-framework)
- `client_members` — Multi-tenant membership with roles (owner/admin/member/viewer)
- `assessments` — Assessment records with auto-incrementing `version` per project
- `questionnaire_sessions` — Completed sessions with `generated_questions`, `agent_criteria`, `conversation_history` as JSONB
- `profiles` — User profiles (auto-created by trigger on sign-up)
- `document_chunks` — pgvector-powered chunks with `vector(1536)` columns
- `iso_requirements` — 116 ISO 27001:2022 controls (migration 017)
- `bnm_rmit_requirements` — 121 BNM RMIT requirements (migration 017)
- `gap_analysis_findings`, `project_documents`, `web_crawl_results`, `compliance_mapping`

### Neo4j Nodes
- `Company`, `DigitalAsset` (with `HAS_ASSET` relationships), `Policy`, `Document`
- `Industry`, `Department`, `ISMSScope`, `BusinessContext`

## Known Gotchas

- **Supabase Client**: Use `get_async_supabase_client_async()` in async code (not `get_async_supabase_client()` which uses `asyncio.run()`)
- **In-Memory State**: Orchestrator and questionnaire agent store active sessions in memory — server restarts lose them
- **Assessment Endpoint**: Uses `multipart/form-data` (not JSON) — `Form(...)` and `File(...)` parameters
- **Health Check**: Only verifies Supabase — Neo4j and Qdrant fail at call time if unavailable
- **Department field**: Stored as comma-separated string for form-data compatibility, parsed to array in frontend

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
