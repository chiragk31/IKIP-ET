# Industrial Knowledge Intelligence Platform (IKIP)

> An AI-powered platform that transforms heterogeneous industrial documents into an intelligent, searchable, continuously evolving knowledge base.

---

## Vision

IKIP functions as a centralized "Industrial Brain" where engineers, operators, managers, and compliance officers can upload documents, discover relationships, retrieve institutional knowledge, perform semantic search, visualize knowledge graphs, and interact with an AI Copilot backed by evidence.

---

## Architecture

```
Browser
  └── Next.js 15 (Frontend)
        └── FastAPI (Backend)
              ├── Supabase (Auth + Storage + Metadata)
              ├── Inngest (Event-Driven Pipeline)
              │     ├── Docling (Parsing)
              │     ├── PaddleOCR (OCR)
              │     ├── Gemini 2.5 Flash (AI Extraction)
              │     ├── Google Embeddings (text-embedding-004)
              │     └── Compliance/Maintenance Agents
              ├── Neo4j Aura (Knowledge Graph)
              └── Pinecone (Vector Search)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 + TypeScript + Tailwind CSS + Shadcn UI |
| Backend | FastAPI + Python 3.12+ |
| LLM | Google Gemini 2.5 Flash |
| OCR | PaddleOCR |
| Document Parsing | Docling |
| Embeddings | Google text-embedding-004 |
| Database | Supabase (PostgreSQL) |
| Graph DB | Neo4j Aura |
| Vector DB | Pinecone |
| Events | Inngest |

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- Accounts: Supabase, Neo4j Aura, Pinecone, Google AI, Inngest

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Fill in .env with your credentials
uvicorn app.main:app --reload
```

Backend runs at: http://localhost:8000
Swagger docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
# Fill in .env.local with your credentials
npm run dev
```

Frontend runs at: http://localhost:3000

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

Expected:
```json
{
  "status": "healthy",
  "services": {
    "supabase": "up",
    "neo4j": "up",
    "pinecone": "up",
    "gemini": "up"
  }
}
```

---

## Project Structure

```
IndustrialKnowledgeIntelligence/
├── docs/            # All project documentation
│   └── tasks/       # Epic task files
├── frontend/        # Next.js 15 application
├── backend/         # FastAPI application
├── scripts/         # Utility scripts
├── docker/          # Docker configuration
└── .github/         # CI/CD workflows
```

---

## Documentation

| Document | Purpose |
|---|---|
| [PRD.md](docs/PRD.md) | Product requirements |
| [Architecture.md](docs/Architecture.md) | System architecture |
| [Design.md](docs/Design.md) | Engineering guidelines |
| [Database.md](docs/Database.md) | Database schema |
| [API.md](docs/API.md) | API specifications |
| [Ontology.md](docs/Ontology.md) | Knowledge graph ontology |
| [Rules.md](docs/Rules.md) | Engineering rules |
| [Prompts.md](docs/Prompts.md) | AI prompt design |
| [Epics.md](docs/Epics.md) | Development roadmap |
| [Memory.md](docs/Memory.md) | Project memory (always read first) |

---

## Development Roadmap

- [x] Phase 0 — Project Foundation
- [X] Phase 1 — Document Upload
- [X] Phase 2 — Document Processing Pipeline
- [X] Phase 3 — AI Knowledge Extraction
- [X] Phase 4 — Ontology Management
- [X] Phase 5 — Knowledge Graph
- [X] Phase 6 — Embeddings & Semantic Search
- [X] Phase 7 — AI Copilot (RAG)
- [X] Phase 8 — Asset Intelligence
- [X] Phase 9 — Dashboard
- [ ] Phase 10 — Authentication
- [ ] Phase 11 — Deployment & Demo

---

## License

MIT License — See [LICENSE](LICENSE)
