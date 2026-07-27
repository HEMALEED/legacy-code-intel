# Legacy Code Intelligence Platform — Track 1

AI-powered documentation for RPG, RPGLE, COBOL, CLP, CLLE, DDS and other IBM i source code.

## Quick Start

### 1 · Start dependencies (PostgreSQL + Redis)

```bash
docker compose up -d
```

### 2 · Backend

```bash
cd backend

# First time only
cp .env.example .env
# Edit .env — set OPENAI_API_KEY (or WATSONX_* keys)

python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt

# Start the API server (auto-creates DB tables on first run)
uvicorn app.main:app --reload --port 8000
```

Open a **second terminal**, activate the same venv, then start the Celery worker:

```bash
cd backend
source .venv/bin/activate        # or .venv\Scripts\activate on Windows
celery -A celery_worker worker --loglevel=info
```

### 3 · Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/jobs` | Upload source files (multipart) — returns `job_id` |
| `GET`  | `/api/jobs` | List all jobs newest-first |
| `GET`  | `/api/jobs/{job_id}` | Get job + documentation result |
| `GET`  | `/health` | Health check |

Interactive docs: **http://localhost:8000/docs**

---

## Project Structure

```
legacy-code-intel/
├── backend/
│   ├── app/
│   │   ├── main.py            FastAPI app + CORS
│   │   ├── config.py          Settings (pydantic-settings)
│   │   ├── database.py        SQLAlchemy engine + session
│   │   ├── models.py          Job, SourceFile, DocumentationResult
│   │   ├── schemas.py         Pydantic response models
│   │   ├── storage.py         File store abstraction (local / S3)
│   │   ├── routers/
│   │   │   └── jobs.py        Upload + job status endpoints
│   │   └── agent/
│   │       ├── doc_agent.py   LangGraph 5-step documentation agent
│   │       └── prompts.py     Language-aware LLM prompts
│   ├── celery_worker.py       Celery task — runs agent in background
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── src/
│       ├── App.tsx            Two-column layout
│       ├── api/client.ts      Typed API client
│       └── components/
│           ├── UploadZone.tsx  Drag-drop upload
│           ├── JobList.tsx     Polling job list
│           ├── JobStatus.tsx   Status badge
│           └── JobDetail.tsx   Documentation viewer
└── docker-compose.yml         PostgreSQL + Redis
```

---

## Configuration

All config lives in `backend/.env` (copy from `.env.example`).

| Key | Default | Notes |
|-----|---------|-------|
| `DATABASE_URL` | `postgresql://lcip:lcip@localhost:5432/lcip` | |
| `REDIS_URL` | `redis://localhost:6379/0` | |
| `LLM_PROVIDER` | `openai` | `openai` or `watsonx` |
| `OPENAI_API_KEY` | — | Required when `LLM_PROVIDER=openai` |
| `OPENAI_MODEL` | `gpt-4o` | |
| `WATSONX_API_KEY` | — | Required when `LLM_PROVIDER=watsonx` |
| `STORAGE_BACKEND` | `local` | `local` or `s3` |
| `MAX_UPLOAD_BYTES` | `52428800` | 50 MB |

---

## Track 2 (next)

- Mermaid diagram rendering in the browser (react-mermaid or mermaid.js CDN)
- Modernization Agent + side-by-side diff (`react-diff-viewer-continued`)
- Multi-file job support (one result per file, tabbed viewer)

## Track 3 (after that)

- JWT auth + RBAC (`author` / `senior-officer` roles)
- Two-stage approval workflow with self-approval guard
- Audit log (append-only)
- GitHub publish (branch + commit + PR)
- SharePoint publish (Microsoft Graph SDK)
