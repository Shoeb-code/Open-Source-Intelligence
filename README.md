# Public Appearance Intelligence System (`Leadzen Intelligence`)

### OSINT Public Source Discovery, Cost-Optimized Extraction, Identity Verification & AI Insights Platform

An end-to-end intelligence platform built with **FastAPI**, **SQLAlchemy**, **React (Vite + Tailwind)**, and **LLMs (Groq / OpenAI)** to discover, extract, verify, enrich, and synthesize public appearances and professional records of any target individual.

---

## Core Capabilities

1. **Per-User Multi-Source Discovery (`DiscoveryService`)**:
   - Generates targeted search queries (`QueryBuilder`) incorporating name, profession, and inferred organizations.
   - **YouTube**: Discovers videos via YouTube Data API v3 (`YOUTUBE_API_KEY`) or zero-key `yt-dlp` flat search.
   - **Web, News, Podcasts, Events, LinkedIn & Instagram**: Uses **Exa AI** neural search (`EXA_API_KEY`) with automatic zero-credential fallback to **DuckDuckGo** (`lite.duckduckgo.com` / `html.duckduckgo.com`).
   - Independent per-person job tracking ensures starting discovery for one user never affects or mixes with other targets.

2. **Cost-Optimized Content Extraction (`MetadataExtractor`)**:
   - **Articles, News, Blogs, Podcasts & Web Pages (`ArticleExtractor`)**:
     1. Tries free **HTTPX + BeautifulSoup** first with automated content-quality checks (enforces configurable `ARTICLE_MIN_CONTENT_LENGTH`, word count, strips nav/cookie banners, and rejects login walls/CAPTCHAs/`200` bot gates).
     2. Falls back to **Firecrawl `/v0/scrape`** (`FIRECRAWL_API_KEY`) only when HTTPX is blocked (`401`/`403`/`429`), times out, or fails quality validation.
     3. Falls back to discovery search snippets (`METADATA_FALLBACK`) if direct page scraping is blocked.
   - **YouTube (`TranscriptExtractor`, 0 Firecrawl credits)**:
     1. Native/auto-generated captions via `youtube-transcript-api`.
     2. 10-minute audio download via `yt-dlp` + Whisper transcription (`whisper-large-v3-turbo` via Groq or `whisper-1` via OpenAI).
     3. Zero-credential rich description & chapter markers via `yt-dlp --dump-single-json`.

3. **Multi-Signal Identity Verification & Scoring (`IdentityVerifier` & `IdentityScorer`)**:
   - Builds an `IdentityContext` (name, profession, inferred organizations, social handles, and profile URLs).
   - Computes weighted confidence ($0.0 - 1.0$) combining fuzzy name matching (`rapidfuzz`), organization match, role tokens, and username/handle match.
   - Assigns status thresholds (`VERIFIED`, `LIKELY_MATCH`, `NEEDS_REVIEW`, `REJECTED`) and automatically discards `REJECTED` candidates before storage.

4. **LinkedIn Profile Enrichment (`LinkedInProfileEnrichmentService`)**:
   - Explicit, user-confirmed enrichment (`POST /api/v1/linkedin/enrich/{target_id}`) via **Firecrawl Alexandria (`enrichlayer`, `people/profile`)** (~10 Firecrawl credits per fresh lookup).
   - Enforces a `VERIFIED` LinkedIn `/in/` profile URL, optional Bearer/API token & `X-Authorized-Targets` access checks, and cached deduplication unless `force=true`.
   - Supports zero-credit import from cached `*_enrichlayer_response.json` files (`POST /api/v1/linkedin/import-cache`).

5. **7-Section AI Insights Generator (`backend/modules/intelligence/`)**:
   - Synthesizes **already-stored database records** (LinkedIn enrichment, posts, web articles, news, podcasts, interviews, and YouTube transcripts) with **0 Firecrawl credits**.
   - Powered by Groq (`GROQ_API_KEY`, automatically falling back across `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b` if a configured model returns `404`), OpenAI (`OPENAI_API_KEY`), or deterministic `extractive-fallback-v1`.
   - Produces structured Pydantic JSON across **7 sections**:
     1. `professional_insights`
     2. `interest_insights`
     3. `knowledge_and_expertise`
     4. `company_insights`
     5. `recent_activities`
     6. `business_insights`
     7. `key_takeaways`
   - Distinguishes `VERIFIED_FACT` vs `AI_HYPOTHESIS`, assigns `HIGH` / `MEDIUM` / `LOW` confidence, resolves citations strictly against DB source URLs, flags `insufficient_evidence`, and saves versioned snapshots in `person_insights_reports`.

6. **White Light-Mode React Dashboard (`frontend/`)**:
   - Crisp light UI featuring Target Profile Management, **Profile & Public Appearances**, **AI Insights** (with report version history & focus notes), **Overview**, **Appearances**, **Timeline**, and **Sources**.

---

## Architecture & Folder Structure

```text
├── backend/
│   ├── main.py                         # FastAPI app, CORS, router mounting & DB startup init
│   ├── config.py                       # Pydantic Settings & environment variables
│   ├── database/
│   │   ├── connection.py               # Engine, SessionLocal & idempotent enrichment column migration
│   │   └── models.py                   # Person, SocialProfile, ResearchJob, Appearance, Source,
│   │                                   # AppearanceAnalysis, CollectionLog, PersonInsightsReport
│   ├── modules/
│   │   ├── persons/                    # Target registration, CRUD, IdentityContext builder
│   │   ├── discovery/                  # QueryBuilder & SearchProviderFactory (Exa / DuckDuckGo)
│   │   ├── collectors/                 # YouTube, News, Podcasts, Webpages, LinkedIn, Instagram
│   │   ├── extraction/                 # HTTPX-first ArticleExtractor, TranscriptExtractor, MetadataExtractor
│   │   ├── identity/                   # Weighted IdentityScorer & threshold IdentityVerifier
│   │   ├── deduplication/              # Canonical URL, YouTube ID & content-hash deduplicator
│   │   ├── analysis/                   # AppearanceClassifier, AppearanceSummarizer & ReportGenerator
│   │   ├── enrichment/                 # Firecrawl Alexandria (EnrichLayer) LinkedIn enrichment & cache import
│   │   ├── intelligence/               # 7-section AI Insights service, prompts, schemas & router
│   │   └── reports/                    # Research job dispatch, URL ingestion & appearance/report endpoints
│   ├── workers/
│   │   ├── celery_app.py               # Optional Celery worker configuration
│   │   └── tasks.py                    # End-to-end OSINT research pipeline
│   └── utils/                          # URL canonicalization, text cleaning, SHA-256 hashing & logging
├── frontend/                           # React 19 + Vite + Tailwind light-mode dashboard
│   ├── src/
│   │   ├── App.jsx                     # Workspace shell & per-person async job polling
│   │   ├── api.js                      # REST API client
│   │   └── modules/                    # TargetSelector, TargetAccountPage, AIInsightsPanel, Overview, etc.
├── tests/                              # Automated Pytest suite (32 unit & integration tests)
├── docker-compose.yml                  # Production stack (API, Celery worker, Postgres, Redis, Frontend)
├── Dockerfile                          # Backend container image
└── requirements.txt                    # Python dependencies
```

---

## Identity Verification & Scoring Model

In [`backend/modules/identity/scoring.py`](backend/modules/identity/scoring.py) and [`backend/modules/identity/verifier.py`](backend/modules/identity/verifier.py), each candidate builds a lowercase search corpus from `title + description + extracted_content`:

| Signal | Weight | How It Is Scored |
| :--- | :---: | :--- |
| **Name Match** | `0.50` | `1.0` for exact full-name substring match in corpus; otherwise `rapidfuzz.partial_ratio` capped at `0.85` (must be `> 70`, else `0.0`). **Gate:** if `name_match < 0.60`, total score short-circuits immediately to `0.10`. |
| **Organization Match** | `0.25` | `1.0` if any inferred organization (parsed from `profession` delimiters like `at`, `@`, `of`, company keywords, or `biography`) appears in the corpus. |
| **Profession / Role Match** | `0.15` | Ratio of matched profession words (`len > 3` chars) found in the corpus (`min(matched / total, 1.0)`). |
| **Known Handles / Usernames** | `0.10` | `1.0` if any linked social handle appears in the corpus or `canonical_url`. |

$$\text{total\_score} = 0.50 \cdot \text{name} + 0.25 \cdot \text{organization} + 0.15 \cdot \text{role} + 0.10 \cdot \text{handle}$$

| Score Range | Verification Status | Pipeline Behavior |
| :---: | :--- | :--- |
| `>= 0.80` | `VERIFIED` | Stored + Stage-1 AI analyzed + auto-links/verifies LinkedIn & Instagram profile URLs |
| `0.55 - 0.79` | `LIKELY_MATCH` | Stored + Stage-1 AI analyzed + eligible to link verified social profiles |
| `0.35 - 0.54` | `NEEDS_REVIEW` | Stored + Stage-1 AI analyzed for human review |
| `< 0.35` | `REJECTED` | **Discarded immediately** (`tasks.py`) to prevent wrong-person contamination |

---

## Environment Variables (`.env`)

All keys except `DATABASE_URL` default safely so the system can run even with minimal or zero external keys using fallbacks.

| Variable | Where Used | Purpose & Fallback Behavior |
| :--- | :--- | :--- |
| `GROQ_API_KEY` | `intelligence/summarizer.py`, `analysis/summarizer.py`, `transcript_extractor.py` | Primary fast LLM inference (AI Insights, Stage-1 analysis, Whisper `whisper-large-v3-turbo` audio transcription). Falls back to OpenAI or `extractive-fallback-v1`. |
| `GROQ_MODEL` | `config.py`, `intelligence/summarizer.py`, `analysis/summarizer.py` | Configured Groq chat model (default `llama-3.3-70b-versatile`). AI Insights automatically falls back across `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b` on `404 NotFoundError`. |
| `OPENAI_API_KEY` / `OPENAI_MODEL` / `OPENAI_BASE_URL` | `intelligence/summarizer.py`, `analysis/summarizer.py`, `transcript_extractor.py` | Secondary LLM & Whisper (`whisper-1`) provider when `GROQ_API_KEY` is unset (default chat model: `gpt-4o-mini`). |
| `EXA_API_KEY` | `discovery/search_providers.py` | Semantic/neural search via `https://api.exa.ai/search` for News, Podcasts, Events/Web, LinkedIn, and Instagram collectors. Falls back cleanly to `DuckDuckGoSearchProvider` when unset or failing. |
| `FIRECRAWL_API_KEY` | `enrichment/linkedin_profile.py`, `extraction/article_extractor.py` | Used for explicit LinkedIn EnrichLayer enrichment (`v2/scrape`, ~10 credits) and as a fallback scraper (`v0/scrape`) only when free HTTPX + BeautifulSoup fails or hits bot/CAPTCHA/login walls. |
| `ARTICLE_MIN_CONTENT_LENGTH` | `config.py`, `extraction/article_extractor.py` | Minimum cleaned character length (`200` default) required for free HTTPX article extraction to skip Firecrawl fallback. |
| `YOUTUBE_API_KEY` | `collectors/youtube.py` | Optional YouTube Data API v3 discovery (`googleapis.com/youtube/v3/search`). Automatically falls back to zero-key `yt-dlp` search when unset. |
| `API_AUTH_TOKEN` | `enrichment/router.py` | Optional Bearer / `X-API-Key` secret protecting `POST /api/v1/linkedin/enrich/{target_id}` and `/import-cache`. |
| `DATABASE_URL` | `database/connection.py` | Database connection URL (default `sqlite:///./appearance_intelligence.db`; Postgres in Docker). |
| `REDIS_URL` / `WORKER_MODE` | `workers/celery_app.py`, `reports/router.py` | `"async_task"` (default local FastAPI `BackgroundTasks`) or `"celery"` (with Redis broker in Docker/production). |

---

## REST API Endpoints (`/api/v1`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/persons` | Register person & linked social profile URLs |
| `GET` | `/api/v1/persons` | List registered persons |
| `GET` | `/api/v1/persons/{person_id}` | Retrieve person details & LinkedIn enrichment fields |
| `GET` | `/api/v1/persons/{person_id}/context` | View normalized `IdentityContext` |
| `PUT` | `/api/v1/persons/{person_id}` | Update person details & social profiles |
| `DELETE` | `/api/v1/persons/{person_id}` | Delete a person and all associated records |
| `POST` | `/api/v1/research/start` | Start asynchronous discovery job for a single person |
| `GET` | `/api/v1/research/{job_id}` | Poll research job status and progress (`0–100%`) |
| `GET` | `/api/v1/persons/{person_id}/appearances` | List discovered appearances (optional `identity_status` filter) |
| `GET` | `/api/v1/persons/{person_id}/timeline` | Retrieve chronological appearance timeline |
| `GET` | `/api/v1/persons/{person_id}/sources` | List collected source URLs & `extraction_status` |
| `GET` | `/api/v1/persons/{person_id}/report` | Retrieve consolidated appearance summary report |
| `POST` | `/api/v1/persons/{person_id}/analyze-url` | Directly ingest, extract, verify, and analyze a URL |
| `DELETE` | `/api/v1/persons/{person_id}/appearances/{appearance_id}` | Delete an appearance record |
| `POST` | `/api/v1/linkedin/enrich/{target_id}` | Trigger Firecrawl Alexandria (`enrichlayer`) enrichment (`force=true` to refresh) |
| `POST` | `/api/v1/linkedin/import-cache` | Import local `*_enrichlayer_response.json` at `0` credits |
| `POST` | `/api/v1/persons/{person_id}/generate-insights` | Generate and persist a 7-section AI Insights report from DB records |
| `GET` | `/api/v1/persons/{person_id}/insights` | Retrieve latest AI Insights report and snapshot history |
| `GET` | `/health` | Service health check |

---

## Local Development Setup

1. **Activate virtual environment**:
   - macOS / Linux:
     ```bash
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   cd frontend && npm install && cd ..
   ```

3. **Configure environment variables**:
   Copy `.env.example` to `.env` and fill in any optional keys:
   ```bash
   cp .env.example .env
   ```

4. **Run the Backend API Server**:
   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```
   Interactive Swagger docs: `http://localhost:8000/docs`

5. **Run the React Frontend**:
   ```bash
   cd frontend
   npm run dev
   ```
   Open your browser at: `http://localhost:5173`

6. **Run Backend Tests & Frontend Checks**:
   ```bash
   .venv/bin/pytest -v
   npm --prefix frontend run lint && npm --prefix frontend run build
   ```

---

## Docker Deployment

Launch the full production stack (FastAPI Backend, Celery Worker, PostgreSQL, Redis, and React Frontend):

```bash
docker-compose up --build
```

- **Frontend Dashboard**: `http://localhost:3000`
- **Backend API & Swagger**: `http://localhost:8000/docs`
