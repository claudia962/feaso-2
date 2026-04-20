# feaso-2 — STR Feasibility Calculator

Second-pass hybrid build of the STR Feasibility & Risk Calculator.
FastAPI + SQLAlchemy 2.0 async + Celery + Next.js 14.

> **Status:** Backend pipeline runs end-to-end on mock AirDNA data.
> Real data integrations pending API-key sourcing (AirDNA, Walk Score, Mapbox).
> Frontend is skeletal; interactive dashboard pending.

---

## Quickstart (backend)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL + API keys
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Health check: `GET http://localhost:8000/health`
Interactive docs: `http://localhost:8000/docs`

---

## Architecture

```
frontend (Next.js 14) ──→ FastAPI ──→ services/ ──→ PostgreSQL
                                 └──→ ml/
                                 └──→ tasks/ (Celery — idle)
```

### Services (`app/services/`)

| Service | Purpose |
|---|---|
| `airdna_client.py` | Comp lookup + market overview (mock when no key) |
| `property_intel.py` | Geocoding + Walk Score + neighbourhood enrichment |
| `regulation_scraper.py` | Jurisdiction lookup with halt-on-banned semantics |
| `comp_analyzer.py` | Weighted similarity scoring (0.35 beds + 0.25 type + 0.20 dist + 0.20 quality) |
| `seasonality_modeler.py` | Month-by-month revenue/occupancy curves |
| `financial_engine.py` | Full pro forma — 3 scenarios |
| `monte_carlo.py` | 2000-simulation MC, samples from real comp distribution |
| `stress_tester.py` | 7 pre-built scenarios with specific adaptations |
| `event_impact_scorer.py` | Event calendar revenue contribution |
| `portfolio_fit.py` | Diversification vs existing portfolio |
| `renovation_roi.py` | Amenity payback analysis using comp pairs |
| `exit_strategy.py` | Continue-STR vs LTR vs sell comparison |
| `rag_engine.py` | Methodology citations (empty-safe when ChromaDB offline) |
| `video_learner.py` | Walkthrough analysis via Claude Vision (no-op when no video) |
| `supply_pipeline.py` | New-listing / building-permit pressure detection |
| `report_generator.py` | 11-section markdown report |

### ML (`app/ml/`)

- `risk_scorer.py` — transparent weighted scoring (precursor to trained model)

### Pipeline order (Critical Rule #11)

Regulation check runs **immediately after geocoding**. If STR is effectively banned
in the jurisdiction, the pipeline short-circuits with a `strong_avoid` recommendation
and a clear reasoning string — no wasted downstream work.

### Data cleanliness

- `annual_expenses` JSONB is reserved strictly for expense line items.
  Monte Carlo extras and event/score metadata live on `FeasibilityAnalysis.metadata`.
- All regulation records carry `last_verified`.
- Comps below the similarity cutoff flag the analysis as low-confidence rather
  than silently polluting projections.

---

## What's still pending

See `PROMPT-feasibility-hybrid.md` §§ 4.5 (RAG), 4.6 (video learner), 5.2 (frontend)
for the remaining work. Blockers:

- **AirDNA API key** — without it, all comp/market data is mock.
- **Walk Score API key** — neighbourhood scoring degrades to heuristic.
- **Mapbox access token** — frontend comp map blank.
- **Fresh Supabase token** — the prior one was rotated.

---

## Testing

```bash
pytest -v
```

Nine test files exist. As of the last known run, only
`test_analysis_endpoint`, `test_financial_basics`, and `test_geocoding` have
executed cleanly — the financial-engine / Monte Carlo / renovation / stress /
report tests have not been executed end-to-end.

---

## Cost awareness (LLM-driven bits)

- Report narrative uses Claude Sonnet.
- Video walkthrough assessment uses Claude Vision.
- RAG query uses Claude (once knowledge base is populated).

Keep session timeouts reasonable and archive completed sessions promptly.
