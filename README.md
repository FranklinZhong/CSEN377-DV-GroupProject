# MedInsight — Drug Visualization Platform

A data visualization platform that helps users understand how medications affect the human body through three complementary lenses: official FDA records, historical reporting trends, and real patient reviews.

**Course:** CSEN 377 Data Visualization — Santa Clara University, Spring 2026

---

## Visualizations

| # | Question | Data Source | Type |
|---|----------|-------------|------|
| **Vis 1** | Which body parts does this drug affect? | FDA Drug Labels + FAERS | Interactive anatomy highlight |
| **Vis 2** | How have adverse event reports evolved over time? | FDA FAERS quarterly data | Animated timeline |
| **Vis 3** | What do patients actually say? | WebMD Reviews (NLP) | Tug-of-war sentiment chart |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vue 3 + TypeScript + Vite |
| Visualization | D3.js + ECharts |
| State Management | Pinia |
| Backend | FastAPI + Python |
| Database | SQLite (generated locally) |
| NLP | spaCy + VADER Sentiment |
| Search | RapidFuzz (fuzzy matching) |

---

## Quick Start

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 2. Download datasets and build the database

> **First-time setup only.** This downloads ~9 GB of raw data and builds `medinsight.db`.
> Requires the [Kaggle CLI](https://www.kaggle.com/docs/api) configured with your API key.

If you only need a small local dataset for testing the app, skip the download and run:

```bash
python scripts/create_sample_data.py
```

This creates a tiny synthetic `data/processed/medinsight.db` and sample FAERS CSV for the README drugs.

```bash
bash scripts/setup_data.sh
```

**What it does:**
- Downloads FAERS data from Kaggle (`anurmi/faers-drug-event-signals`)
- Downloads WebMD reviews from Kaggle (`rohanharode07/webmd-drug-reviews-dataset`)
- Downloads OpenFDA drug label zips (~1.82 GB, with resume support)
- Runs the full data pipeline → outputs `data/processed/medinsight.db`

If you already have the raw data, skip downloads:
```bash
bash scripts/setup_data.sh --skip-dl
```

### 3. Start the application

Open two terminals from the project root:

```bash
# Terminal 1 — Backend (auto-reloads on code changes)
uvicorn backend.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm install
npx vite --port 5173
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

**Try these drugs:** metformin, ibuprofen, aspirin, lisinopril, amoxicillin, sertraline, warfarin, prednisone, adalimumab, gabapentin

---

## Project Structure

```
├── backend/              FastAPI backend
│   ├── api/              Route handlers (drugs, search, trend, health)
│   ├── services/         Business logic (drug lookup, FAERS, caching)
│   ├── schemas/          Pydantic response models
│   ├── db.py             SQLite connection + schema init
│   └── main.py           App entry point + CORS middleware
│
├── frontend/             Vue 3 + Vite frontend
│   └── src/
│       ├── components/   Visualization components
│       │   ├── AnatomyHero.vue     Decorative anatomy (homepage)
│       │   ├── AnatomyBody.vue     Interactive anatomy (14 organs)
│       │   ├── BodyMap.vue         Static organ highlight
│       │   ├── TrendAnimation.vue  FAERS timeline animation
│       │   ├── TugOfWarChart.vue   Benefit vs. side-effect chart
│       │   └── ReviewList.vue      Paginated review viewer
│       ├── pages/        HomePage, DrugDetailPage
│       ├── stores/       Pinia state (drug data, view mode)
│       ├── api/          Axios client + TypeScript types
│       └── router/       Vue Router (/, /drugs/:id)
│
├── pipeline/             Data processing scripts
│   ├── run_pipeline.py   Main orchestrator (run this to build the DB)
│   ├── config.py         Path configuration
│   ├── clean_faers*.py   FAERS data cleaning
│   ├── clean_webmd*.py   WebMD review cleaning + NLP
│   ├── clean_openfda*.py OpenFDA label processing (streaming)
│   ├── nlp_webmd.py      spaCy NER + VADER sentiment analysis
│   ├── build_*.py        Derived data builders (benefits, aliases)
│   ├── aggregate_rating.py   Rating aggregation from reviews
│   ├── fill_indication_summary.py  OpenFDA → drug indication fields
│   ├── soc_body_map.py   MedDRA SOC → body part mapping
│   └── download_openfda.sh  Download OpenFDA zips (curl, resume-safe)
│
├── scripts/
│   └── setup_data.sh     One-shot data download + pipeline runner
│
├── docs/
│   └── DATASET_SOURCES.md               Dataset sources + license notes
│
├── design/
│   └── User_Story.md     User stories and requirements
│
└── requirements.txt      Python dependencies
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/search?q=<drug>` | Search drugs by name (fuzzy) |
| GET | `/api/drugs/{id}` | Drug summary + data coverage |
| GET | `/api/drugs/{id}/sideeffects` | Side effects by body part |
| GET | `/api/drugs/{id}/overview` | Indication, mechanism, quick facts |
| GET | `/api/drugs/{id}/reviews/list` | Paginated patient reviews |
| GET | `/api/drugs/{id}/trend` | FAERS quarterly report trend |
| GET | `/api/health` | Health check |

Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Data Sources

| Dataset | Source | License |
|---------|--------|---------|
| FAERS Drug Event Signals | FDA / [Kaggle](https://www.kaggle.com/datasets/anurmi/faers-drug-event-signals) | Public Domain |
| WebMD Drug Reviews | [Kaggle](https://www.kaggle.com/datasets/rohanharode07/webmd-drug-reviews-dataset) | CC BY-NC-SA 4.0 (academic use only) |
| OpenFDA Drug Labels | [open.fda.gov](https://open.fda.gov/apis/drug/label/) | Public Domain |

> **Note:** WebMD data is used under CC BY-NC-SA 4.0 for academic research purposes only.
> This project is not intended for commercial use.
