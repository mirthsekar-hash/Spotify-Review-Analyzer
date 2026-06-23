# Spotify Review Discovery Engine

AI-powered Product Research Intelligence Platform that ingests public Spotify feedback (Play Store, App Store, Reddit), analyzes reviews with **Groq** (default) or swappable LLM providers, generates embeddings with **Google Gemini**, and surfaces insights through dashboards and a RAG Research Assistant.

## Documentation

- [How It Works](docs/how-it-works.md)
- [Problem Statement](docs/problemStatement.md)
- [Architecture](docs/architecture.md)
- [Implementation Plan](docs/implementation-plan.md)
- [Deployment Guide](docs/deployment.md)

## Project Structure

```
app/                  Streamlit UI (main.py, pages/, components/)
src/
  llm/                Provider-agnostic Groq/Gemini/OpenAI layer
  schemas/            Pydantic JSON schemas for AI outputs
  ingestion/          Phase 1.3 — scrapers & CSV import
  db/                 Phase 1.2 — Supabase repositories
  analysis/           Phase 1.4+ — AI analysis engines
  rag/                Phase 4 — Research Assistant
  pipeline/           Phase 2.3 — orchestrator
  services/           Phase 1.5+ — dashboard queries
prompts/              LLM prompt templates
supabase/migrations/  Database schema
data/fallback/        Offline CSV samples
tests/                Unit tests
```

## Quick Start

```powershell
git clone https://github.com/mirthsekar-hash/Spotify-Review-Analyzer.git
cd Spotify-Review-Analyzer

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env
# Edit .env — set SUPABASE_URL, SUPABASE_SERVICE_KEY, GROQ_API_KEY, GEMINI_API_KEY, REDDIT_USER_AGENT

streamlit run streamlit_app.py
```

## Configuration

| Variable | Required | Default |
|----------|----------|---------|
| `SUPABASE_URL` | Yes | — |
| `SUPABASE_SERVICE_KEY` | Yes | — |
| `GROQ_API_KEY` | Yes (default LLM) | — |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` |
| `GEMINI_API_KEY` | Yes (embeddings default) | — |
| `GEMINI_EMBEDDING_MODEL` | No | `gemini-embedding-001` |
| `LLM_PROVIDER` | No | `groq` |
| `EMBEDDING_PROVIDER` | No | `gemini` |
| `REDDIT_USER_AGENT` | Yes | — |

**Recommended setup** (Groq analysis + Gemini embeddings):

```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile

EMBEDDING_PROVIDER=gemini
GEMINI_API_KEY=...
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
```

Swap LLM provider without code changes:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
```

## Ingestion (Phase 1.3)

**Sidebar actions:**
- **Fetch Play Store Reviews** — live scrape via `google-play-scraper`
- **Import CSV (Fallback)** — upload CSV or use `data/fallback/playstore_sample.csv`

CSV columns: `source`, `text` (or `review_text`), `rating`, `review_date`, `reviewer_name`

```powershell
# Test ingestion against Supabase
$env:RUN_DB_INTEGRATION=1
pytest tests/test_ingestion_integration.py -v
```

## Analysis (Phase 1.4)

**Sidebar action:** **Run Analysis** — analyzes unanalyzed reviews with Groq (LLM) and Gemini embeddings.

```powershell
python -m src.pipeline.run_analysis --limit 10
pytest tests/test_schemas.py tests/test_review_analyzer.py tests/test_analysis_pipeline.py -v
```

## Executive Summary (Phase 1.5)

Open the **Executive Summary** page to view KPI cards, sentiment chart, trust score gauge, and health indicators.

```powershell
pytest tests/test_dashboard_service.py -v
```

## App Store Ingestion (Phase 2.1)

**Sidebar action:** **Fetch App Store Reviews** — iTunes RSS across regions (optional `app-store-scraper` library via `APP_STORE_USE_LIBRARY=true`)

Fallback offline data: `data/fallback/appstore_sample.csv` (55 rows)

```powershell
pytest tests/test_appstore_scraper.py -v

$env:RUN_DB_INTEGRATION=1
pytest tests/test_appstore_integration.py -v

# Live scrape (may be rate-limited by Apple)
$env:RUN_LIVE_APPSTORE=1
pytest tests/test_appstore_integration.py -v -k live
```

## Reddit Ingestion (Phase 2.2)

**Sidebar action:** **Fetch Reddit Discussions** — public JSON API (`httpx`, no OAuth) across r/spotify, r/truespotify, r/music, r/listentothis

On 429/403 after retries, automatically loads `data/fallback/reddit_sample.csv` (210 rows).

```powershell
python -m src.pipeline.run_ingestion --source reddit

pytest tests/test_reddit_json_scraper.py -v

$env:RUN_DB_INTEGRATION=1
pytest tests/test_reddit_integration.py -v

# Live scrape (may be rate-limited by Reddit)
$env:RUN_LIVE_REDDIT=1
pytest tests/test_reddit_integration.py -v -k live
```

Required env: `REDDIT_USER_AGENT` (e.g. `spotify-review-engine/1.0 (contact: you@email.com)`)

## Pipeline Orchestrator (Phase 2.3)

**Sidebar action:** **Fetch Latest Reviews** — parallel ingest from all three sources, then analyze and embed only new reviews. Run state is logged to `pipeline_runs`.

```powershell
python -m src.pipeline.run_pipeline

pytest tests/test_orchestrator.py -v
```

Partial source failures show per-source status in the sidebar (e.g. Play Store succeeds while App Store fails).

## Source Analysis (Phase 2.4)

Open **Source Analysis** to compare Play Store, App Store, and Reddit:

- Review count bar chart
- Stacked sentiment by source (Plotly)
- Side-by-side comparison table (avg rating, rec. complaint %, sentiment)
- Top 5 complaints per source

```powershell
pytest tests/test_dashboard_service.py -v
```

## Explorer Dashboards (Phase 3.7)

Collective intelligence pages powered by `themes`, `segments`, `root_causes`, and `unmet_needs` tables:

| Page | Features |
|------|----------|
| **Discovery Challenges** | Themes ranked by impact score (falls back to interim data if themes empty) |
| **Theme Explorer** | Theme selector, supporting reviews, segment pie chart, related root causes |
| **Segment Explorer** | Segment cards with size + trust score, goals/behavior/frustrations detail |
| **Root Cause Analysis** | Ranked table + expandable evidence panel |
| **Unmet Needs** | Opportunity matrix scatter + AI solution cards |

```powershell
pytest tests/test_explorer_service.py -v
```

## Discovery Journey (Phase 3.8)

**Discovery Journey** visualizes top paths from `review_analysis`:

`user_goal → listening_behavior → discovery_challenge → workaround (primary_problem) → inferred desired outcome`

Includes a Plotly Sankey diagram, ranked path table, and path detail with supporting review counts.

```powershell
pytest tests/test_journey_service.py -v
```

## Collective Intelligence Schemas (Phase 3.1)

Pydantic schemas and prompts for the four collective engines (used in Phase 3.2–3.5):

| Schema | Prompt | Engine (Phase 3.2+) |
|--------|--------|---------------------|
| `src/schemas/themes.py` | `prompts/theme_extraction.txt` | Theme extractor |
| `src/schemas/segments.py` | `prompts/segmentation.txt` | Segment engine |
| `src/schemas/root_causes.py` | `prompts/root_cause.txt` | Root cause engine |
| `src/schemas/unmet_needs.py` | `prompts/unmet_needs.txt` | Unmet need detector |

```powershell
pytest tests/test_schemas_collective.py -v
```

## Database Setup (Phase 1.2)

1. Open Supabase SQL Editor
2. Run [`supabase/migrations/001_initial_schema.sql`](supabase/migrations/001_initial_schema.sql)
3. Restart the app — sidebar should show **Supabase connected**

```powershell
$env:RUN_DB_INTEGRATION=1
pytest tests/test_db_integration.py -v
```

## Development

```powershell
pytest tests/ -v
streamlit run streamlit_app.py
```

## Implementation Status

| Phase | Status |
|-------|--------|
| 1.1 Project scaffold | Complete |
| 1.2 Database layer | Complete |
| 1.3 Ingestion core | Complete |
| 1.4 Per-review AI | Complete |
| 1.5 Executive Summary | Complete |
| 2.1 App Store scraper | Complete |
| 2.2 Reddit JSON scraper | Complete |
| 2.3 Pipeline orchestrator | Complete |
| 2.4 Source Analysis dashboard | Complete |
| 2.5 Discovery Challenges (interim) | Complete |
| 3.1 Collective prompt library | Complete |
| 3.2–3.5 Collective engines | Complete |
| 3.6 Collective orchestration | Complete |
| 3.7 Explorer dashboards | Complete |
| 3.8 Discovery Journey dashboard | Complete |
| 4.1–4.2 RAG Research Assistant | Complete |
| 4.3 Executive AI summary | Complete |
| 4.4 Interview Validation | Complete |
| 4.5 Deployment (Docker, secrets, smoke test) | Complete |

## Deployment (Phase 4.5)

**Streamlit Cloud** (recommended): connect GitHub, set main file to `streamlit_app.py`, paste secrets from [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example). See [docs/deployment.md](docs/deployment.md).

**Docker** (Render / Railway):

```powershell
docker build -t spotify-review-analyzer .
docker run -p 8501:8501 --env-file .env spotify-review-analyzer
```

**Verify configuration:**

```powershell
python scripts/verify_secrets.py
python scripts/smoke_test.py
python scripts/smoke_test.py --url https://your-app.streamlit.app
```

The **Executive Summary** page shows DB connection status and last pipeline run (health indicator).

Private case study project.
