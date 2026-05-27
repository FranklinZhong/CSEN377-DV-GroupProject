# MedInsight

Drug Visualization Platform | CSEN 377 Data Visualization, SCU Spring 2026

> Search any drug and explore its effects on the human body from three angles: official records, historical adverse event trends, and real patient feedback.

---

## Features

- **Interactive Anatomy Map** — Clickable holographic body figure highlights which organs are affected (benefits in green, side effects in red)
- **FAERS Trend Animation** — Quarterly adverse event timeline with D3.js heatmap, playback controls, and CUSUM statistical spike detection
- **Patient Sentiment Tug-of-War** — Visual balance of positive vs. negative patient reviews by body system, with a review drawer
- **Smart Search** — 8,000+ drugs ranked by data quality; A–Z browser with Full Data badges

---

## Data Sources

| Dataset | Source | Coverage |
|---------|--------|----------|
| openFDA Drug Labels | api.fda.gov | ~8,000 drugs — indications, mechanism, dosage |
| FDA FAERS Adverse Events | open.fda.gov/drug/event | Quarterly reports 2004–present |
| WebMD Drug Reviews | Kaggle (CC BY-NC-SA 4.0, academic use) | 4.2M+ patient reviews |

> The SQLite database (`data/processed/medinsight.db`, ~151 MB) is excluded from git. See **Data Setup** below.

---

## Project Structure

```
medinsight/
├── backend/                   # FastAPI backend
│   ├── main.py
│   ├── db.py
│   ├── api/                   # Routes: search, drugs, trend, health
│   └── services/              # drug_service, faers_service, cache_service
│
├── frontend/                  # Vue 3 + Vite + TypeScript
│   └── src/
│       ├── pages/             # HomePage.vue, DrugDetailPage.vue
│       ├── components/        # AnatomyBody, AnatomyHero, TrendAnimation,
│       │                      # TugOfWarChart, IsotypeGrid, ReviewList
│       └── api/client.ts      # Axios API client
│
├── pipeline/                  # Data processing scripts
│   ├── run_pipeline.py        # Main entry → generates medinsight.db
│   ├── nlp_webmd.py           # VADER sentiment + body-system mapping
│   ├── clean_faers_signals.py
│   ├── clean_webmd_reviews.py
│   └── clean_openfda_streaming.py
│
├── data/
│   ├── raw/                   # Raw downloads (gitignored)
│   └── processed/             # DB + cleaning scripts (DB gitignored)
│
├── docs/                      # Design documents
├── tests/                     # Backend (pytest) + Frontend (vitest)
└── requirements.txt
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+

### 1. Install dependencies

```bash
pip install -r requirements.txt
npm install --prefix frontend
```

### 2. Data Setup

The database is not included in the repo. You have two options:

**Option A — Get the DB from a teammate** (recommended)  
Place `medinsight.db` at `data/processed/medinsight.db`.

**Option B — Rebuild from raw data**

```bash
# Download raw data (see pipeline/download_openfda.sh for OpenFDA)
# Place FAERS zip in data/processed/FAERS/
# Place WebMD zip in data/processed/WebMDReview/

python pipeline/clean_faers_signals.py
python pipeline/clean_webmd_reviews.py
python pipeline/clean_openfda_streaming.py
python pipeline/run_pipeline.py
```

### 3. Run the app

```bash
# Backend (port 8000)
uvicorn backend.main:app --reload --port 8000

# Frontend (port 5173)
cd frontend && npx vite --port 5173
```

Open [http://localhost:5173](http://localhost:5173)

---

## Three Visualizations

| # | Question | Component | Data |
|---|----------|-----------|------|
| Vis 1 | Which organs does this drug affect? | `AnatomyBody.vue` | openFDA labels + FAERS |
| Vis 2 | How have adverse events changed over time? | `TrendAnimation.vue` | FDA FAERS quarterly |
| Vis 3 | What do patients say about their experience? | `TugOfWarChart.vue` | WebMD reviews (NLP) |

---

## Sprint Summary

| Sprint | Period | Status |
|--------|--------|--------|
| Sprint 0 | 4/24–4/30 | ✅ Planning + dataset approval |
| Sprint 1 | 5/1–5/7  | ✅ Data pipeline + SQLite DB |
| Sprint 2 | 5/8–5/14 | ✅ FastAPI backend + Vue scaffold |
| Sprint 3 | 5/15–5/21 | ✅ All three visualizations |
| Sprint 4 | 5/22–5/28 | 🔧 UI polish ✅ · write-up ⬜ · video ⬜ |

## Recent Changes

| Date | Change |
|------|--------|
| 2026-05-26 | Fixed layout jumping in `TrendAnimation.vue` during playback — replaced `<TransitionGroup>` with plain `<div v-for>` and added `mode="out-in"` to narrative transition |
| 2026-05-24 | Full UI overhaul: holographic anatomy hero (homepage), interactive anatomy body (detail page), hover-card height stabilization |
| 2026-05-24 | Added "About the Data" modal on homepage with three data-source cards |
| 2026-05-23 | SQLite concurrency fix (`check_same_thread=False`, `busy_timeout=5000`) |

---

## Course Info

**CSEN 377 Data Visualization** · Santa Clara University · Spring 2026  
Instructor: Dr. Sharon Hsiao
