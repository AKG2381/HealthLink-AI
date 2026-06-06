# HealthLink-AI  :  Smart Health Management System

HealthLink-AI is an AI-assisted health triage application. A user describes their
symptoms in plain language; a multi-agent pipeline analyzes them, recommends
appropriate specialists from a doctor directory, proposes appointment slots, and
produces a plain-language summary with next steps.

> **Disclaimer:** HealthLink-AI is for informational purposes only. It is **not** a
> medical diagnosis and **not** a substitute for professional care. In an
> emergency, contact local emergency services.

---

## Architecture at a glance

The system is built as **two deployable container images** plus shared backend code:

| Image | Contents | Serves |
| ----- | -------- | ------ |
| **Image 1 — Backend + React** (root `Dockerfile`) | FastAPI API + compiled React SPA | API at `/api/v1`, React app at `/` |
| **Image 2 — Streamlit** (`ui/Dockerfile`) | Standalone Streamlit UI | An alternative web UI that calls the backend over HTTP |

The React frontend is bundled **into** the backend image: a Node build stage
compiles `frontend/` and copies the static output into the Python image, so
FastAPI serves both the API and the SPA from a single origin (no CORS needed for
React). The Streamlit UI is a separate, small image that talks to the backend
via the `API_BASE_URL` environment variable.

```
                    +--------------------------------------+
   Browser  ------->|  Image 1: FastAPI + React (one URL)  |
                    |   /          -> React SPA            |
                    |   /api/v1/*  -> REST API             |
                    |   /docs      -> OpenAPI docs         |
                    +---------------+----------------------+
                                    | HTTP
                    +---------------+----------------------+
   Browser  ------->|  Image 2: Streamlit UI (separate)    |---+
                    +--------------------------------------+   | calls /api/v1
                                                               v
                                                      (Image 1 backend)
```

### The multi-agent pipeline

A request to `/api/v1/assess` flows through an orchestrator that runs four agents
in sequence, each with a single responsibility:

1. **Symptom agent** — extracts structured symptoms, severity, and urgency from
   free text (optionally enriched by RAG retrieval).
2. **Doctor agent** — maps the assessment to a specialty and selects matching
   doctors from the directory.
3. **Scheduling agent** — proposes available appointment slots.
4. **Summary agent** — writes a plain-language summary, key findings, and
   recommended actions.

### Technology

- **LLM:** Anthropic Claude via `langchain-anthropic` (default
  `claude-sonnet-4-6`), using structured (Pydantic) outputs.
- **Embeddings:** local `sentence-transformers/all-MiniLM-L6-v2` (384-dim, runs
  on CPU, no API key required).
- **Vector store / RAG:** Pinecone (optional — toggled with `ENABLE_RAG`).
- **Database:** SQLite via SQLAlchemy, seeded from `data/doctors.csv`.
- **Backend:** FastAPI + Uvicorn.
- **Frontends:** React (Vite) and Streamlit.
- **Deploy:** Docker -> Google Cloud Run, via GitHub Actions + Artifact Registry.

---

## Project structure

```
.
├── main.py                      # FastAPI app entry; serves API + React SPA
├── requirements.txt             # Backend + ML dependencies
├── setup.sh                     # Local setup helper
├── Dockerfile                   # IMAGE 1: Node build stage (React) + Python backend
├── docker-compose.yml           # Local: api (backend+React) + streamlit together
├── .dockerignore  .gitignore  .env.example
├── README.md                    # This file
├── CHANGES.md                   # Log of fixes / migration notes
│
├── config/                      # Configuration
│   ├── settings.py              #   Pydantic settings (env-driven)
│   └── logging.py               #   Logging setup
│
├── core/                        # Core engine
│   ├── llm.py                   #   Claude (ChatAnthropic) wrapper + structured output
│   ├── rag.py                   #   Pinecone vector store + local HF embeddings
│   ├── orchestrator.py          #   Runs the 4 agents in sequence
│   ├── database.py              #   SQLAlchemy models, session mgmt, doctor seeding
│   └── schemas.py               #   Pydantic request/response models
│
├── agents/                      # Multi-agent pipeline
│   ├── symptom_agent.py
│   ├── doctor_agent.py
│   ├── scheduling_agent.py
│   └── summary_agent.py
│
├── api/
│   └── routes.py                # API endpoints (mounted under /api/v1)
│
├── utils/
│   ├── helpers.py
│   └── validators.py
│
├── data/
│   ├── doctors.csv              # 100 doctors (seeded into the DB at startup)
│   └── symptoms_kb.json         # 200-entry knowledge base (RAG corpus)
│
├── frontend/                    # React SPA (bundled into IMAGE 1 at build time)
│   ├── index.html
│   ├── package.json  package-lock.json  vite.config.js
│   ├── Dockerfile  nginx.conf   #   (standalone-serve option; unused by combined image)
│   ├── .env.example  .gitignore  .dockerignore  README.md
│   └── src/
│       ├── main.jsx             #   React entry
│       ├── App.jsx              #   Top-level app, nav, health status
│       ├── styles.css           #   Design tokens + component styles
│       ├── components/          #   IntakeForm, Loading, Results, Doctors, Icons
│       └── lib/                 #   api.js (API client), format.js (helpers)
│
├── ui/                          # IMAGE 2: standalone Streamlit UI
│   ├── streamlit_app.py
│   ├── requirements.txt         #   Minimal: streamlit + requests
│   └── Dockerfile  .dockerignore
│
├── tests/
│   ├── test_api.py              # API endpoint tests
│   ├── test_agents.py           # Agent tests (mocked LLM)
│   ├── test_e2e.py              # Live end-to-end (requires a running server)
│   └── mock_llm_outputs.json
│
└── .github/workflows/
    └── deploy.yaml              # CI: test -> build+deploy backend -> build+deploy Streamlit
```

---

## API reference

All endpoints are mounted under `/api/v1`. Interactive docs at `/docs`.

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET`  | `/api/v1/health` | Service health (`llm`, `database`, `rag` status) |
| `POST` | `/api/v1/assess` | Run a full health assessment |
| `GET`  | `/api/v1/doctors` | List doctors; query params `specialty`, `limit` |
| `GET`  | `/api/v1/doctors/{doctor_id}` | Get a single doctor |
| `GET`  | `/api/v1/specialties` | List available specialties |
| `GET`  | `/api` | API metadata (JSON) — available even when `/` serves React |

**Assessment request body:**

```json
{
  "user_input": "I've had a throbbing headache and mild fever for two days.",
  "user_id": "optional-id",
  "preferred_date": "2026-06-10",
  "preferred_location": "Pune"
}
```

The response contains four sections: `symptom_analysis`, `doctor_recommendations`,
`scheduling_options`, and `health_summary`.

---

## Configuration

Settings are loaded from environment variables (or a local `.env`). See
`.env.example`.

| Variable | Required | Default | Purpose |
| -------- | -------- | ------- | ------- |
| `ANTHROPIC_API_KEY` | **Yes** | — | Claude API key (all generation) |
| `PINECONE_API_KEY` | Only if `ENABLE_RAG=true` | — | Pinecone vector store |
| `ENABLE_RAG` | No | `true` | Toggle RAG retrieval on/off |
| `LLM_MODEL_NAME` | No | `claude-sonnet-4-6` | Claude model |
| `EMBEDDING_MODEL_NAME` | No | `sentence-transformers/all-MiniLM-L6-v2` | Local embedding model |
| `PINECONE_INDEX_NAME` | No | `HealthLink-AI` | Index name (must be 384-dim) |
| `CORS_ORIGINS` | No | localhost dev origins | Comma-separated allowed origins |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `PORT` | No | `8080` | Port the server binds (Cloud Run injects this) |

> If you previously ran with Gemini embeddings, delete any existing Pinecone
> index first — it was created at 3072 dimensions and won't accept the new
> 384-dim vectors. The app recreates the index at the right size on startup.

---

## Running locally

### Option A — backend + React (one process)

```bash
# 1. Install backend deps
pip install -r requirements.txt

# 2. Build the React frontend so FastAPI can serve it
cd frontend && npm install && npm run build && cd ..

# 3. Set your key and run
export ANTHROPIC_API_KEY=sk-ant-...
export ENABLE_RAG=false            # or set PINECONE_API_KEY and leave RAG on
uvicorn main:app --reload
```

Open http://localhost:8000 — the React app loads, and the API is at
`/api/v1`. (If you skip step 2, `/` returns JSON instead of the SPA.)

### Option B — React dev server (hot reload)

```bash
# terminal 1: backend
uvicorn main:app --reload
# terminal 2: frontend dev server (proxies /api to :8000)
cd frontend && npm install && npm run dev      # http://localhost:3000
```

### Option C — Streamlit UI

```bash
cd ui
pip install -r requirements.txt
API_BASE_URL=http://localhost:8000/api/v1 streamlit run streamlit_app.py
```

### Option D — Docker Compose (backend+React and Streamlit together)

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export PINECONE_API_KEY=...         # or set ENABLE_RAG=False in the compose env
docker compose up --build
```

- Backend + React: http://localhost:8000
- Streamlit: http://localhost:8501

---

## Testing

```bash
# offline tests (mocked LLM) — no API key needed
pytest tests/test_api.py tests/test_agents.py -v

# end-to-end (requires a running server with a real key)
pytest tests/test_e2e.py -v
```

---

## Deployment (Google Cloud Run)

Deployment is automated via `.github/workflows/deploy.yaml`: pushing to `main`
runs tests, builds and deploys the **backend + React** image, then builds and
deploys the **Streamlit** image. Both go to one Artifact Registry repo
(`HealthLink-AI`) as two images, and become two Cloud Run services.

### One-time setup

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  secretmanager.googleapis.com cloudbuild.googleapis.com

# Secrets
echo -n "sk-ant-..." | gcloud secrets create ANTHROPIC_API_KEY --data-file=-
echo -n "pcn-..."    | gcloud secrets create PINECONE_API_KEY  --data-file=-

# Let the runtime service account read them
RUNTIME_SA=YOUR_RUNTIME_SA_EMAIL
for S in ANTHROPIC_API_KEY PINECONE_API_KEY; do
  gcloud secrets add-iam-policy-binding $S \
    --member="serviceAccount:$RUNTIME_SA" \
    --role="roles/secretmanager.secretAccessor"
done
```

### GitHub configuration

- **Secrets:** `GCP_PROJECT_ID`, `GCP_SA_KEY` (deployer SA JSON),
  `ANTHROPIC_API_KEY`, `PINECONE_API_KEY`
- **Variable:** `SERVICE_ACCOUNT` (the runtime SA email)

The deployer SA (in `GCP_SA_KEY`) needs: Cloud Run Admin, Artifact Registry
Writer, and Service Account User on the runtime SA.

### Manual deploy (alternative to CI)

```bash
# Backend + React
gcloud run deploy HealthLink-AI \
  --source . --region asia-south1 --allow-unauthenticated --port 8080 \
  --memory 4Gi --cpu 2 \
  --set-secrets "ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest,PINECONE_API_KEY=PINECONE_API_KEY:latest"

# Streamlit (point it at the backend URL)
cd ui
gcloud run deploy HealthLink-AI-streamlit \
  --source . --region asia-south1 --allow-unauthenticated --port 8080 \
  --set-env-vars API_BASE_URL=https://YOUR_BACKEND_URL/api/v1
```

After deploy, verify:

```bash
curl https://YOUR_BACKEND_URL/api/v1/health     # JSON health
curl -s https://YOUR_BACKEND_URL/ | head -c 40  # should start with <!doctype html>
```

---

## Notes & gotchas

- **SQLite is ephemeral on Cloud Run.** The DB is re-seeded per instance from
  `data/doctors.csv`; appointments don't persist across restarts. Use Cloud SQL
  / Firestore for persistence.
- **First cold start is slower** — the backend image bundles the embedding model
  and the React build; the first request after scale-from-zero pays a startup cost.
- **Two images accumulate in Artifact Registry.** Consider a cleanup policy to
  keep only the most recent N versions per image.
- **Run on Claude alone:** set `ENABLE_RAG=false` to drop the Pinecone dependency
  entirely — the symptom agent degrades gracefully without retrieval.