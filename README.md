# 🧠 DocMind — Multi-Tenant RAG SaaS

A production-ready Retrieval-Augmented Generation backend with full tenant isolation.  
Each user gets their **own private namespace** in Pinecone — zero data leakage by design.

---

## Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI 0.111 |
| Auth | JWT (HS256) via `python-jose` |
| Rate limiting | SlowAPI + in-memory per-user window |
| Vector DB | Pinecone (serverless, per-user namespace) |
| Embeddings | Google Gemini `embedding-001` (768-dim) |
| LLM | Groq `llama3-70b-8192` |
| Database | MongoDB Atlas via Beanie ODM |
| Frontend | Streamlit |

---

## Project Structure

```
rag-saas/
├── backend/
│   ├── config.py               # Centralised settings (pydantic-settings)
│   ├── main.py                 # FastAPI app factory + lifespan
│   ├── models/
│   │   └── db_models.py        # Beanie ODM models + Pydantic schemas
│   ├── routers/
│   │   ├── auth.py             # /api/v1/auth/*
│   │   ├── documents.py        # /api/v1/documents/*
│   │   ├── query.py            # /api/v1/query/*
│   │   └── stats.py            # /api/v1/stats/*
│   ├── services/
│   │   ├── embeddings.py       # Gemini embedding-001 wrapper
│   │   ├── vector_store.py     # Pinecone CRUD with namespace isolation
│   │   ├── document_processor.py # Parse → chunk → embed → upsert pipeline
│   │   └── rag_pipeline.py     # Retrieve → prompt → Groq LLaMA → log
│   ├── middleware/
│   │   └── rate_limiter.py     # Per-user query + upload rate limiting
│   └── utils/
│       └── auth.py             # JWT helpers + FastAPI dependency
├── frontend/
│   ├── app.py                  # Streamlit application (all pages)
│   └── api_client.py           # HTTP client wrapping the FastAPI backend
├── requirements.txt
├── .env.example
├── docker-compose.yml
├── Dockerfile.api
└── Dockerfile.frontend
```

---

## Quick Start

### 1. Clone & configure

```bash
git clone <your-repo>
cd rag-saas
cp .env.example .env
# Edit .env with your real API keys
```

### 2. Required API keys

| Key | Where to get |
|-----|-------------|
| `MONGODB_URL` | [MongoDB Atlas](https://cloud.mongodb.com) → Connect → Drivers |
| `PINECONE_API_KEY` | [Pinecone Console](https://app.pinecone.io) → API Keys |
| `PINECONE_ENVIRONMENT` | Pinecone → your index region e.g. `us-east-1` |
| `GOOGLE_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `GROQ_API_KEY` | [Groq Console](https://console.groq.com/keys) |
| `JWT_SECRET_KEY` | Generate with `openssl rand -hex 32` |

### 3. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Run the API

```bash
cd rag-saas
python -m uvicorn backend.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### 5. Run the Streamlit frontend

```bash
streamlit run frontend/app.py
```

Frontend at: http://localhost:8501

### 6. Docker (optional)

```bash
docker-compose up --build
```

---

## API Reference

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Create account |
| POST | `/api/v1/auth/login` | Get JWT tokens |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| GET  | `/api/v1/auth/me` | Get current user |

### Documents
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/documents/upload` | Upload PDF/DOCX/TXT (async) |
| GET  | `/api/v1/documents/` | List user's documents |
| GET  | `/api/v1/documents/{id}` | Get document status |
| DELETE | `/api/v1/documents/{id}` | Delete document + vectors |

### Query
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/query/` | RAG query |
| GET  | `/api/v1/query/history` | Query history |

### Stats
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/v1/stats/` | Usage stats |
| GET  | `/api/v1/stats/namespace` | Pinecone namespace info |

---

## Multi-Tenancy Architecture

```
User A  ──► JWT (user_id_A) ──► Pinecone namespace: user_id_A ──► 🔒 Isolated vectors
User B  ──► JWT (user_id_B) ──► Pinecone namespace: user_id_B ──► 🔒 Isolated vectors
```

- One **Pinecone index**, N **namespaces** — no cross-tenant queries possible
- MongoDB documents scoped by `user_id` with indexed queries
- Rate limiting tracked per `user_id` (not IP)

---

## Rate Limits (configurable in .env)

| Action | Default limit |
|--------|--------------|
| Queries | 20 / minute per user |
| Uploads | 50 / day per user |

---

## Document Processing Pipeline

```
Upload file
    │
    ▼
Parse (PyPDF2 / python-docx / plain text)
    │
    ▼
Chunk (RecursiveCharacterTextSplitter, 600 tokens, 80 overlap)
    │
    ▼
Embed (Gemini embedding-001 → 768-dim vectors)
    │
    ▼
Upsert to Pinecone (user namespace, batches of 100)
    │
    ▼
Update MongoDB DocumentRecord (status: ready)
```

## Production Considerations

- Replace in-memory rate limiter with **Redis** for multi-worker deployments
- Add **email verification** flow to auth router
- Add **Stripe** integration to enforce plan-based limits
- Use **Celery + Redis** for background ingestion at scale
- Add **CloudFront / CDN** in front of Streamlit for production
