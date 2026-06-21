# Spotify Review Discovery Engine

AI-powered Product Research Intelligence Platform that ingests public Spotify feedback (Play Store, App Store, Reddit), analyzes it with **Google Gemini 2.5 Flash**, and surfaces insights through dashboards and a RAG Research Assistant.

## Documentation

- [Problem Statement](docs/problemStatement.md)
- [Architecture](docs/architecture.md)
- [Implementation Plan](docs/implementation-plan.md)

## Quick Start

```powershell
# Clone
git clone https://github.com/mirthsekar-hash/Spotify-Review-Analyzer.git
cd Spotify-Review-Analyzer

# Environment
copy .env.example .env
# Fill in SUPABASE_URL, SUPABASE_SERVICE_KEY, GEMINI_API_KEY

# Install (once app code is scaffolded)
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Streamlit |
| Backend | Python |
| Database | Supabase + pgvector |
| LLM (default) | Google Gemini 2.5 Flash |
| Embeddings | Gemini `text-embedding-004` |
| Ingestion | Play Store, App Store, Reddit JSON API |

## Configuration

Copy `.env.example` to `.env`. Required variables:

- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
- `GEMINI_API_KEY`, `GEMINI_MODEL=gemini-2.5-flash`
- `REDDIT_USER_AGENT`

LLM provider is swappable via `LLM_PROVIDER=gemini|openai` without code changes.

## License

Private case study project.
