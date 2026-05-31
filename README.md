# MedInsight

Drug Visualization Platform | CSEN 377 Data Visualization, SCU Spring 2026

> Search any drug and explore its effects on the human body from three angles: official records, historical adverse event trends, and real patient feedback.

---

## Features

- **Interactive Anatomy Map** — Holographic body figure with 15 clickable organ regions; highlights benefits (green), side effects (red), or both (amber) with animated glow
- **FAERS Adverse Event Heatmap** — Static XY heatmap (X = year, Y = body system) with row-wise color normalization, CUSUM spike detection, missing-data stripe pattern, and a Pearson co-activation correlation matrix
- **Patient Sentiment Tug-of-War** — Visual balance of positive vs. negative reviews per body system; rope position = net sentiment ratio; click any row to open a paginated review drawer
- **Smart Search** — 8,000+ drugs ranked by data quality; A–Z browser; body-part filter tab
- **TF-IDF Word Cloud** — Homepage anatomy-silhouette word cloud: patient vocabulary terms shaped to the body outline, colored by body system, placed beside the anatomy hero

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
│       │                      # TugOfWarChart, ReviewList
│       └── api/client.ts      # Axios API client + TypeScript types
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
│   └── processed/             # DB + cleaning reports (DB gitignored)
│
├── docs/                      # Design documents
├── tests/                     # Backend (pytest) + Frontend (vitest)
│   ├── backend/               # 61 pytest tests
│   └── components/            # Vue component integration tests
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

The SQLite database (`data/processed/medinsight.db`, ~152 MB) is excluded from the repo. Run the steps below to rebuild it from scratch. Total download size is roughly **3 GB**; processing takes 20–40 minutes depending on your machine.

---

#### Step 1 — Download the three raw datasets

**Dataset A: FAERS Drug Event Signal Dataset** (Kaggle)

1. Go to [https://www.kaggle.com/datasets/nicholasgah/faers-drug-event-signal-dataset](https://www.kaggle.com/datasets/nicholasgah/faers-drug-event-signal-dataset)
2. Click **Download** → save the ZIP
3. Place it at:
   ```
   data/processed/FAERS/FAERS Drug Event Signal Dataset.zip
   ```

**Dataset B: WebMD Drug Reviews Dataset** (Kaggle)

1. Go to [https://www.kaggle.com/datasets/rohanharode07/webmd-drug-reviews-dataset](https://www.kaggle.com/datasets/rohanharode07/webmd-drug-reviews-dataset)
2. Click **Download** → save the ZIP
3. Place it at:
   ```
   data/processed/WebMDReview/WebMD Drug Reviews Dataset.zip
   ```

**Dataset C: OpenFDA Drug Labels** (FDA bulk API — script provided)

```bash
# Downloads 13 zip files (~1.82 GB) from download.open.fda.gov
# Resumable: re-running skips already-complete files
bash pipeline/download_openfda.sh
```

The files land in `data/processed/OpenFDA/data/raw/` automatically.

---

#### Step 2 — Clean each dataset

Run the three cleaning scripts independently (order does not matter):

```bash
# Clean FAERS signal dataset → cleaned_faers_signals_prr_ror.csv
python pipeline/clean_faers_signals.py

# Clean WebMD reviews → cleaned_webmd_reviews.csv
python pipeline/clean_webmd_reviews.py

# Stream-process OpenFDA label ZIPs → multiple per-drug JSON/CSV files
python pipeline/clean_openfda_streaming.py
```

Each script prints a summary of rows kept/dropped and writes a cleaning report to `data/processed/reports/`.

---

#### Step 3 — Build the SQLite database

```bash
# Full pipeline: loads all cleaned CSVs and writes medinsight.db
python pipeline/run_pipeline.py
```

Individual steps if you need to rerun only part of the pipeline:

```bash
python pipeline/run_pipeline.py --faers        # reload FAERS signals only
python pipeline/run_pipeline.py --webmd        # reload WebMD reviews only
python pipeline/run_pipeline.py --indications  # re-fill OpenFDA indications
python pipeline/run_pipeline.py --benefits     # rebuild benefit effects
python pipeline/run_pipeline.py --index        # rebuild search index
python pipeline/run_pipeline.py --ratings      # recalculate drug ratings
python pipeline/run_pipeline.py --v35          # run indications + benefits + ratings
```

Expected output: `data/processed/medinsight.db` (~152 MB, 8,689 drugs, 287K+ reviews).

---

#### Step 4 — Run NLP corpus analysis (word cloud data)

```bash
# Computes TF-IDF scores and sentiment distribution per body system
# Writes results into corpus_tfidf and corpus_sentiment tables in the DB
python pipeline/nlp_corpus_analysis.py
```

This step powers the TF-IDF word cloud on the homepage. Skip it if you only need the three main visualizations.

---

#### Expected file tree after setup

```
data/
├── raw/
│   ├── faers/        # (unused — pipeline reads from processed/)
│   ├── webmd/
│   └── openfda/
└── processed/
    ├── FAERS/
    │   ├── FAERS Drug Event Signal Dataset.zip   ← you place this
    │   └── cleaned_faers_signals_prr_ror.csv     ← generated
    ├── WebMDReview/
    │   ├── WebMD Drug Reviews Dataset.zip        ← you place this
    │   └── cleaned_webmd_reviews.csv             ← generated
    ├── OpenFDA/
    │   └── data/
    │       ├── raw/      ← 13 ZIPs downloaded by script
    │       └── processed/
    ├── reports/           ← cleaning summaries (markdown)
    └── medinsight.db      ← final database (~152 MB)
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

| # | Question | Component | Data Source |
|---|----------|-----------|-------------|
| Vis 1 | Which organs does this drug affect? | `AnatomyBody.vue` | openFDA labels + FAERS |
| Vis 2 | How have adverse events changed over time? | `TrendAnimation.vue` | FDA FAERS API (quarterly, 2004–present) |
| Vis 3 | What do patients say about their experience? | `TugOfWarChart.vue` | WebMD reviews (VADER NLP) |

### Vis 2 — FAERS Heatmap Details

- **XY layout**: years on X-axis, body systems on Y-axis
- **Row-wise normalization**: each body system's color scale is independent, so rare and frequent systems are both visible
- **Three cell states**: colored (reports exist) · striped (data gap in API) · dark (zero reports confirmed)
- **CUSUM signals**: cells with statistically unusual spikes get a red border
- **Co-activation matrix**: Pearson correlation of annual report counts across body systems (shown when ≥ 2 systems and ≥ 3 years of data)
- **Row highlight**: click a row to pin it; hovering an organ in the anatomy map also highlights the corresponding row

---

## Testing

The project has a 237-test suite covering all three visualization layers:

```bash
# Backend unit + integration tests (61 tests)
pytest tests/backend/ -v

# Frontend unit tests (176 tests)
cd frontend && npx vitest run --reporter=verbose

# Production build verification
cd frontend && npm run build
```

| Layer | Tests | Coverage |
|-------|-------|----------|
| Backend API (pytest) | 61 | All endpoints: search, drugs, trend, health, reviews |
| Frontend logic — Vis 1 | 52 | highlightType, maxSeverity, organStroke, effectsAt |
| Frontend logic — Vis 2 | 51 | yearData, pearson, correlationData, getActiveRow, cellFill |
| Frontend logic — Vis 3 | 53 | netSentiment, knotX/R, ropeWidth, centerColor, topTerms |
| Component integration | 17 | mount + emit + API mock for all 3 visualizations |
| Word cloud — CorpusWordCloud | 6 | SVG atlas render, loading/error states, TF-IDF API integration |
| Word cloud — wordCloudLayout | 9 | placeWordsInBBox spiral packing, collision detection, font scaling |

---

## Sprint Summary

| Sprint | Period | Highlights |
|--------|--------|------------|
| Sprint 0 | 4/24–4/30 | ✅ Planning, dataset selection, project scoping |
| Sprint 1 | 5/1–5/7  | ✅ Data pipeline, SQLite DB built (8,689 drugs, 287K+ reviews) |
| Sprint 2 | 5/8–5/14 | ✅ FastAPI backend (all endpoints), Vue 3 scaffold, SQLite integration |
| Sprint 3 | 5/15–5/21 | ✅ All three visualizations functional end-to-end |
| Sprint 4 | 5/22–5/28 | ✅ UI polish, heatmap redesign, 234-test suite, clean production build |
| Sprint 5 | 5/29      | ✅ TF-IDF word cloud, tooltip fix, codebase cleanup |
| Sprint 6 | 5/30      | ✅ Symptom Atlas v2.0 (SVG zone-clustered word cloud), 237-test suite |

---

## Course Info

**CSEN 377 Data Visualization** · Santa Clara University · Spring 2026  
Instructor: Dr. Sharon Hsiao
