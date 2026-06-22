# Deployment Guide — Phase 4.5

Production deployment for **Spotify Review Analyzer** per [architecture.md](architecture.md) §13 and [implementation-plan.md](implementation-plan.md) §4.5.

## Platforms

| Platform | Entry command | Notes |
|----------|---------------|-------|
| **Streamlit Cloud** | `streamlit run streamlit_app.py` | Primary target; secrets via dashboard |
| **Render / Railway** | Docker (`Dockerfile`) | Uses `$PORT` env var |
| **Local** | `streamlit run streamlit_app.py` | `.env` or `.streamlit/secrets.toml` |

---

## 4.5.3 — Streamlit Cloud

1. Push the repo to GitHub.
2. Open [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Set **Main file path** to `streamlit_app.py`.
4. Under **Advanced settings** → **Secrets**, paste the TOML from [`.streamlit/secrets.toml.example`](../.streamlit/secrets.toml.example) and fill in values.
5. Deploy and note the public URL (e.g. `https://your-app.streamlit.app`).

`streamlit_app.py` maps `st.secrets` into environment variables before loading `app.config.Settings`.

---

## 4.5.4 — Verify secrets

Local (`.env` loaded automatically):

```powershell
python scripts/verify_secrets.py
```

With local Streamlit secrets file:

```powershell
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
# edit secrets.toml, then:
streamlit run streamlit_app.py
# in another terminal:
python scripts/verify_secrets.py
```

Required keys (minimum):

- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
- `GEMINI_API_KEY` (embeddings default)
- `GROQ_API_KEY` when `LLM_PROVIDER=groq` (default)
- `REDDIT_USER_AGENT`

---

## 4.5.5 — Smoke test

**Local** (needs working Supabase):

```powershell
python scripts/smoke_test.py
```

**Skip DB** (structure + secrets only):

```powershell
python scripts/smoke_test.py --skip-db
```

**Deployed URL**:

```powershell
python scripts/smoke_test.py --url https://your-app.streamlit.app
```

Checks: secrets, 9 dashboard pages, fallback CSVs, RAG imports, Supabase (optional), HTTP health endpoint.

---

## Docker (Render / Railway)

```powershell
docker build -t spotify-review-analyzer .
docker run -p 8501:8501 --env-file .env spotify-review-analyzer
```

Set `PORT` when the host assigns a dynamic port:

```bash
docker run -e PORT=8080 -p 8080:8080 --env-file .env spotify-review-analyzer
```

Health endpoint: `GET /_stcore/health`

---

## Production checklist (architecture §13.1)

| Item | Status |
|------|--------|
| Supabase service key server-side only | ✓ `app.config` / backend modules |
| LLM rate limiting (tenacity) | ✓ `src/llm` providers |
| Scraper timeout + partial success | ✓ `src/pipeline/orchestrator.py` |
| Fallback CSVs in `data/fallback/` | ✓ bundled |
| Pinned `requirements.txt` | ✓ |
| Health indicator on Executive Summary | ✓ `app/components/health_indicator.py` |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "Missing required environment variables" | Set secrets in Cloud dashboard or `.env` |
| DB unreachable | Run `supabase/migrations/001_initial_schema.sql` (+ `002`) |
| Scrapers blocked | Use **Import CSV** with `data/fallback/*.csv` |
| LLM 429 | Lower `ANALYSIS_BATCH_SIZE` or switch provider in secrets |
