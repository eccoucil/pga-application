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

# Backend tests
cd backend && uv run pytest

# Backend linting
cd backend && uv run ruff format . && uv run ruff check --fix .

# Frontend lint
cd frontend && npm run lint
```

## Architecture

### Backend Configuration (`backend/app/`)

- **config.py** - Pydantic settings management (loads from `.env`)
- **auth/dependencies.py** - Supabase JWT validation via `get_current_user` dependency

### Backend Services (`backend/app/services/`)

- **neo4j_service.py** - Graph database operations (Company, DigitalAsset, Policy, Document nodes)
- **qdrant_service.py** - Vector database operations for semantic search
- **embedding_service.py** - OpenAI text embeddings (text-embedding-3-small)
- **assessment_orchestrator.py** - Lightweight coordination agent (no LLM, pure Python orchestration)
- **web_crawler_agent.py** - CRAWL4AI-powered web intelligence extraction with Claude Opus 4.5 sub-agents

### Backend Routers (`backend/app/routers/`)

- **assessment.py** - Assessment submission and status endpoints (multipart/form-data)
- **knowledge.py** - Knowledge graph endpoints
- **search.py** - Semantic search endpoints
- **web_crawler.py** - Web crawling endpoints (crawl domain, list/get/delete results, asset graph)

**Note:** `client_members.py` router is referenced in frontend but not yet implemented.

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

### Frontend State Management

Five React contexts manage application state:
- `ThemeContext` - Dark/light mode theme management (persists to localStorage)
- `AuthContext` - Supabase authentication
- `ClientContext` - Selected client (clears project on change)
- `ProjectContext` - Selected project (auto-clears when client changes)
- `ClientMembershipContext` - Team membership, roles (owner/admin/member/viewer), and permissions

### Frontend Layout Components (`frontend/src/components/layout/`)

- **DashboardLayout** - Main layout wrapper with Header, Sidebar, and Footer
- **Header** - Fixed top header with Organization Portal branding and dark mode toggle
- **Sidebar** - Collapsible icon rail that expands on hover (16px collapsed, 56px expanded)
  - Shows icons when collapsed, full labels when expanded
  - Single "Clients" menu item linking to `/clients`
- **Footer** - Fixed bottom footer with copyright and links

### Frontend Client Management (`frontend/src/components/clients/`)

- **ClientManagement** - Main component with stats cards, search/filter, and CRUD operations
- **ClientTable** - Table component displaying clients with proper field mapping (`name` = company name, `company` = contact person)
- **ClientModal** - Modal for creating/editing clients with validation
- **DeleteConfirmation** - Confirmation dialog for client deletion
- **CreateClientDialog** - Dialog component for creating new clients
- **EditClientDialog** - Dialog component for editing existing clients

### Frontend Web Crawler Components (`frontend/src/components/web-crawler/`)

- **CrawlResultCard** - Displays individual crawl results with expandable details
- **CrawlingProgressDialog** - Shows crawl progress with status updates
- **BusinessContextSection** - Displays extracted business context (industry, services)
- **DigitalAssetsSection** - Lists discovered digital assets (subdomains, portals, APIs)
- **OrganizationInfoSection** - Shows organization info (contacts, certifications)
- **AssetGraphSection** - Visual graph representation of discovered assets

**Backend:** Implemented via `web_crawler.py` router with CRAWL4AI + Claude Opus 4.5.

### Frontend Routes

- `/` - Dashboard/home page
- `/clients` - Client management page (uses ClientManagement component)
- `/organizations` - Organizations page (alternative client management view)
- `/clients/[id]/projects/[projectId]/assessment` - Assessment submission page
- `/clients/[id]/projects/[projectId]/{documents|framework|questionnaires|web-crawl}` - Project-specific routes

### Database Schema

**Supabase tables** (with Row Level Security):
- `clients` - Client organizations (fields: `name` = company name, `company` = contact person)
- `projects` - Projects under clients
- `client_members` - Multi-tenant client membership with roles (owner/admin/member/viewer)
- `project_documents` - Document upload metadata
- `framework_questions` - Generated questions with `batch_id` tracking
- `question_responses` - User responses to framework questions
- `gap_analysis_findings` - Analysis results with compliance levels
- `web_crawl_results` - Web crawler results (business_context, digital_assets, organization_info as JSONB)
- `iso_requirements`, `bnm_rmit_requirements` - Framework control definitions
- `compliance_mapping` - Mapping between ISO and BNM RMIT requirements

**Neo4j nodes**:
- `Company` - Organization from web crawl (domain, name, industry)
- `DigitalAsset` - URLs discovered (asset_type: subdomain/portal/api/application/website)
- `Policy`, `Document` - Document analysis relationships

**Migrations** in `migrations/` - Run manually against Supabase SQL editor.

## Key Patterns

### Backend Package Manager
Always use `uv` (not pip): `uv run <command>`, `uv sync`

### Compliance Levels
- `compliant` - Policy explicitly addresses all control aspects
- `partially_compliant` - Policy exists but has gaps
- `non_compliant` - Policy contradicts requirements
- `not_assessed` - Insufficient evidence

### Framework Identifiers
- ISO 27001: `identifier` like "A.5.1", "A.8.34" (Annex A) or clauses 4-10 (management)
- BNM RMIT: `reference_id` like "8.1", `section_number` for numeric sorting

### UI Styling

**Theme Support:**
- Light/dark mode toggle in header
- Theme preference persisted in localStorage
- Uses Tailwind `dark:` variants throughout

**Custom Classes:**
- `cyber-gradient-bg`, `cyber-grid-dark`, `glow-effect`, `text-glow`
- Button variant: `cyber` (cyan gradient)

**Layout Styling:**
- Sidebar: Collapsible icon rail (16px collapsed, 56px expanded on hover)
- Header/Footer: Fixed positioning with backdrop blur
- Main content: Responsive padding and margins based on sidebar state

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
```

**Frontend** (`frontend/.env.local`):
```
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_ANON_KEY (or NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY)
NEXT_PUBLIC_API_URL=http://localhost:8001
```

