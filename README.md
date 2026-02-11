# PGA - Policy Gap Analysis

A compliance analysis application for **BNM RMIT** and **ISO 27001:2022** standards. PGA uses AI-powered analysis to identify gaps between organizational policies and regulatory requirements.

## Features

- **Document Analysis**: Upload and analyze organizational policy documents
- **Questionnaire Generation**: AI-generated compliance assessment questions (25-30 per framework)
- **Gap Identification**: AI-powered identification of compliance gaps
- **Semantic Search**: Search across policies using natural language
- **Knowledge Graph**: Visual representation of policy relationships
- **Web Crawling**: Discover digital assets and extract business context from organization websites
- **Multi-Tenant Teams**: Role-based access control (owner/admin/member/viewer)
- **Multi-Framework Support**: BNM RMIT and ISO 27001:2022 compliance checking

## Tech Stack

### Backend
- **FastAPI** - High-performance Python web framework
- **Supabase** - PostgreSQL database and authentication
- **Qdrant** - Vector database for semantic search
- **Neo4j** - Graph database for policy relationships
- **Claude AI & OpenAI** - AI-powered analysis

### Frontend
- **Next.js 15** - React framework with App Router
- **React 19** - UI library
- **TypeScript** - Type-safe JavaScript
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

### 4. Start Docker Services

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

### Documents
- `POST /documents/upload` - Upload a policy document
- `GET /documents/{id}` - Get document details
- `POST /documents/analyze` - Analyze document for compliance

### Search
- `POST /search/semantic` - Semantic search across policies
- `GET /search/suggestions` - Get search suggestions

### Knowledge
- `GET /knowledge/policies` - List all policies
- `GET /knowledge/gaps` - Get identified compliance gaps
- `GET /knowledge/graph` - Get policy relationship graph

### Questionnaire
- `POST /questionnaire/generate` - Generate compliance assessment questions
- `GET /questionnaire/{project_id}` - Get questions for a project
- `POST /questionnaire/responses` - Submit question responses

### Assessment
- `POST /assessment/submit` - Submit assessment (multipart/form-data)
  - Required: `client_id`, `project_id`, `organization_name`, `nature_of_business` (min 10 chars), `industry_type`, `department`, `scope_statement_isms` (min 10 chars)
  - Optional: `web_domain`, `documents` (PDF, DOCX, TXT, XLSX, CSV)
- `GET /assessment/status/{assessment_id}` - Get assessment processing status

### Web Crawler
- `POST /web-crawler/crawl` - Start web crawl for a domain (extracts business context, assets, org info)
- `GET /web-crawler/{project_id}/results` - List crawl results for project
- `GET /web-crawler/{project_id}/result/{result_id}` - Get detailed crawl result
- `DELETE /web-crawler/{project_id}/results` - Delete all crawl results for project
- `GET /web-crawler/{project_id}/graph/{domain}` - Get Neo4j asset graph for domain

### Health
- `GET /health` - API health check

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
│   │   ├── agents/       # AI Agents
│   │   │   ├── document_intake/     # Document processing
│   │   │   └── question_generator/  # Questionnaire generation
│   │   ├── auth/         # Authentication (JWT validation)
│   │   ├── routers/      # API routes
│   │   ├── models/       # Data models (assessment, etc.)
│   │   ├── services/     # Business logic (orchestrator, etc.)
│   │   ├── db/           # Database connections
│   │   ├── config.py     # Pydantic settings
│   │   └── main.py       # Application entry point
│   ├── tests/            # Backend tests
│   ├── docker-compose.yml
│   ├── pyproject.toml
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── app/          # Next.js App Router pages
│   │   ├── components/   # React components
│   │   ├── contexts/     # React contexts
│   │   ├── lib/          # Utilities and helpers
│   │   └── hooks/        # Custom React hooks
│   ├── public/           # Static assets
│   ├── package.json
│   └── .env.local
├── migrations/           # Supabase SQL migrations
├── BNM_RMIT_Policy_Requirements.md
├── iso27001_2022_complete.md
├── start.sh
├── CLAUDE.md
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

### Question Generator

Generates compliance assessment questions using a **framework-level hybrid approach**:

- **Overview Questions**: Strategic, framework-wide maturity assessment
- **Section Questions**: Deep-dive into specific control domains

| Metric | Per-Control (Legacy) | Framework-Level |
|--------|---------------------|-----------------|
| Questions per framework | ~1,250 | 25-30 |
| API calls | ~250 | ~12 |
| Processing time | ~10 min | ~60 sec |
| Cost reduction | - | 95% |

**Question Distribution per Framework:**

| Section Type | ISO 27001 | BNM RMIT |
|--------------|-----------|----------|
| Overview | 5 | 5 |
| Core Sections | 20 | 20 |
| **Total** | **25** | **25** |

### Document Intake

Processes uploaded policy documents:
- Supports PDF, DOCX, XLSX, PPTX, TXT, XLS, CSV
- Extracts and cleans text content
- Prepares for AI analysis

### Assessment Orchestrator

Lightweight coordination agent (no LLM, pure Python):
- Receives assessment submissions via `/assessment/submit`
- Validates organization info (including required `scope_statement_isms`)
- Documents are optional - assessments can be submitted with scope statement only
- Tracks assessment state and status
- Prepares payloads for downstream AI agents

### Web Crawler Agent

CRAWL4AI-powered web intelligence extraction using Claude Opus 4.5:

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

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
