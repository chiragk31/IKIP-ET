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

## Set up on another Windows laptop

The following instructions reproduce the development environment currently used by
this project. They assume Windows 10/11 and PowerShell.

### 1. Install prerequisites

- [Git](https://git-scm.com/download/win)
- **Python 3.12.0 (64-bit)**. During installation, select **Add Python to PATH**.
  Verify it with `py -3.12 --version`.
- [Node.js 22 LTS](https://nodejs.org/) (the project was installed with Node 22.20.0
  and npm 10.9.3). Verify with `node --version` and `npm --version`.
- Access to the same Supabase, Neo4j Aura, Pinecone, Google AI, and Inngest
  accounts used by the project.

> Do not copy the `venv312`, `.venv`, `node_modules`, `.next`, `.env`, or `.env.local`
> folders from another computer. Create the environments locally using the locked
> dependency files below.

### 2. Clone the repository

In PowerShell, replace `<YOUR-GITHUB-REPOSITORY-URL>` with this project's GitHub
clone URL:

```powershell
git clone <YOUR-GITHUB-REPOSITORY-URL>
cd IndustrialKnowledgeIntelligence
```

### 3. Create the backend environment

Run these commands from the repository root:

```powershell
py -3.12 -m venv backend\.venv
.\backend\.venv\Scripts\Activate.ps1
python --version
python -m pip install --upgrade pip
python -m pip install -r backend\requirementsvenv312.txt
```

`requirementsvenv312.txt` is an exact package snapshot generated from the current
`backend/venv312` environment. The new environment is deliberately named `.venv`,
which is ignored by Git. Use this file instead of `backend/requirements.txt` when
you need the matching setup. The first installation can take several minutes
because it downloads document-processing and machine-learning packages.

If PowerShell prevents activation, run this once in the same terminal and then
repeat the activation command:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### 4. Configure backend credentials

```powershell
Copy-Item backend\.env.example backend\.env
notepad backend\.env
```

Fill every service value in `backend/.env` with the credentials from the existing
working setup. Keep this file private; it is intentionally not committed to Git.

### 5. Install and configure the frontend

Open a **second** PowerShell window at the repository root and run:

```powershell
cd frontend
npm ci
Copy-Item .env.local.example .env.local
notepad .env.local
```

Set `NEXT_PUBLIC_API_URL=http://localhost:8000` and copy the Supabase URL and anon
key into `frontend/.env.local`. `npm ci` uses the committed `package-lock.json`,
so it installs the same frontend dependency versions.

### 6. Start the application

In the first PowerShell window (the activated backend environment):

```powershell
cd backend
python -m uvicorn app.main:app --reload
```

In the second PowerShell window:

```powershell
cd frontend
npm run dev
```

Open http://localhost:3000. The backend API documentation is at
http://localhost:8000/docs.

### 7. Verify the backend

While the backend is running, open this address in a browser or run:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/health
```

`healthy` means all configured cloud services are reachable. `degraded` normally
means a value in `backend/.env` is missing or invalid; check the backend terminal
output to identify the service.

### Common setup issues

| Problem | What to do |
|---|---|
| `py -3.12` is not found | Install the 64-bit Python 3.12.0 launcher, then close and reopen PowerShell. |
| Dependency installation fails | Confirm that the environment is activated (`(.venv)` appears in the prompt) and retry `python -m pip install -r backend\requirementsvenv312.txt`. |
| `npm ci` fails | Use Node 22 LTS, remove only the newly created `frontend/node_modules` folder, then run `npm ci` again. Do not edit `package-lock.json`. |
| Backend starts but the health check is `degraded` | Compare `backend/.env` with the working computer's credentials and service access. |
| OCR is unavailable | The backend can use PaddleOCR and an optional Tesseract fallback. Install Tesseract separately only if the backend logs say that OCR is unavailable. |

### Daily start-up

After the one-time setup, use two terminals:

```powershell
# Terminal 1: from the repository root
.\backend\.venv\Scripts\Activate.ps1
cd backend
python -m uvicorn app.main:app --reload
```

```powershell
# Terminal 2: from the repository root
cd frontend
npm run dev
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
