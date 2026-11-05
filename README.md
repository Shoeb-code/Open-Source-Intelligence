# Public Appearance Intelligence System (Level 2)
### OSINT Public Source Discovery, Data Extraction and AI-Powered Analysis Platform

An open-source OSINT intelligence backend built with **FastAPI**, **SQLAlchemy**, **Celery**, and **LLMs** to discover, extract, verify, deduplicate, and analyze public appearances of any individual across the web, YouTube, podcasts, news articles, and conference talks.

---

## 🚀 Key Features

1. **Targeted Query Generation**: Dynamically builds contextual search queries incorporating name, profession, and affiliated organizations across multiple media channels.
2. **Multi-Source Discovery Engine**:
   - **YouTube**: Video discovery via YouTube Data API v3 & yt-dlp flat-search.
   - **News & Media**: High-coverage article discovery via Exa or DuckDuckGo fallback.
   - **Podcasts & Events**: Keynotes, panels, and guest episodes.
3. **Resilient Extraction Engine**:
   - Automatic YouTube subtitle/transcript extraction via `youtube-transcript-api` and `yt-dlp`.
   - Web article extraction via `Firecrawl` or resilient `BeautifulSoup` + `lxml`.
   - Graceful handling of unavailable transcripts or restricted websites without pipeline halts.
4. **Multi-Signal Identity Verification**:
   - Calculates weighted confidence scores ($0.0 - 1.0$) combining fuzzy name matching (`rapidfuzz`), organizational affiliation, role attribution, and handle links.
   - Assigns unambiguous verification status: `VERIFIED`, `LIKELY_MATCH`, `NEEDS_REVIEW`, or `REJECTED`.
5. **Deduplication Engine**: Consolidates appearances using canonical URLs, YouTube video IDs, content hashes, and fuzzy title matching.
6. **AI Analysis & Evidence Attribution**:
   - Categorizes appearance types (`PODCAST`, `INTERVIEW`, `NEWS_ARTICLE`, `CONFERENCE`, `WEBINAR`).
   - Extracts structured executive summaries, recurring discussion topics, person roles, and verifiable evidence quotes.
7. **Consolidated Reporting & Timeline**: Chronological appearance timeline, frequency analysis of themes, and complete source provenance.

---

## 🛠️ Architecture & Folder Structure

```
├── app/
│   ├── main.py                     # FastAPI application entrypoint & lifecycle
│   ├── config.py                   # Pydantic Settings & environment variables
│   │
│   ├── database/
│   │   ├── connection.py           # Engine & SessionLocal (PostgreSQL / SQLite fallback)
│   │   └── models.py               # Persons, Profiles, Jobs, Appearances, Sources, Analysis
│   │
│   ├── modules/
│   │   ├── persons/                # Registration & IdentityContext generation
│   │   ├── discovery/              # QueryBuilder & SearchProvider (Exa / DuckDuckGo)
│   │   ├── collectors/             # YouTube, News, Podcasts, Webpages collectors
│   │   ├── extraction/             # Article & Transcript extractors
│   │   ├── identity/               # Multi-signal identity verification & scoring
│   │   ├── deduplication/          # Canonical URL & content hash deduplicator
│   │   ├── analysis/               # Classifier, Summarizer & Report generator
│   │   └── reports/                # Report endpoints & job management
│   │
│   ├── workers/
│   │   ├── celery_app.py           # Celery configuration
│   │   └── tasks.py                # End-to-end OSINT research workflow
│   │
│   └── utils/
│       ├── url_validator.py        # URL canonicalization & video ID extractors
│       ├── text_cleaner.py         # Text normalization & SHA-256 content hashing
│       └── logger.py               # Structured logging
│
├── tests/                          # Automated Pytest suite
├── docker-compose.yml              # Production stack (API, Worker, Postgres, Redis)
├── Dockerfile                      # Application container
└── requirements.txt                # Python dependencies
```

---

## 🚦 REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/persons` | Register person & parse social profiles |
| `GET` | `/api/v1/persons/{person_id}` | Retrieve person identity details |
| `GET` | `/api/v1/persons/{person_id}/context` | View normalized identity context |
| `POST` | `/api/v1/research/start` | Start asynchronous public appearance discovery job |
| `GET` | `/api/v1/research/{job_id}` | Poll research progress (0-100%) and status |
| `GET` | `/api/v1/persons/{person_id}/appearances` | Retrieve discovered & verified appearances |
| `GET` | `/api/v1/persons/{person_id}/timeline` | Retrieve chronological timeline |
| `GET` | `/api/v1/persons/{person_id}/sources` | Retrieve all source references and extraction statuses |
| `GET` | `/api/v1/persons/{person_id}/report` | Retrieve consolidated final intelligence report |

---

## 💻 Local Development Setup

1. **Activate virtual environment**:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   Copy `.env.example` to `.env` and fill in any optional API keys:
   ```env
   OPENAI_API_KEY=your_openai_key
   EXA_API_KEY=your_exa_key
   YOUTUBE_API_KEY=your_youtube_key
   ```
   *(Note: The system functions out-of-the-box with zero credentials using resilient fallback extractors and zero-credential search!)*

4. **Run the Backend API Server**:
   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```
   Interactive Swagger docs: [http://localhost:8000/docs](http://localhost:8000/docs)

5. **Run the React Frontend**:
   ```powershell
   cd frontend
   npm run dev
   ```
   Open your browser at: [http://localhost:5173](http://localhost:5173)

6. **Run tests**:
   ```bash
   pytest -v
   ```

---

## 🐳 Docker Deployment

To launch the full production environment (FastAPI Backend + React Frontend + PostgreSQL + Redis + Celery Worker):
```bash
docker-compose up --build
```
- **Frontend Dashboard**: [http://localhost:3000](http://localhost:3000)
- **Backend API & Swagger**: [http://localhost:8000/docs](http://localhost:8000/docs)

