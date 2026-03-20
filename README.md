# NewsAlpha

**Predicting Market Direction Using Distributed Sentiment Analysis of Financial News**

CS 179G Senior Design Project · University of California, Riverside · 2026

---

## About

NewsAlpha is a full-stack data platform that investigates whether news sentiment can predict S&P 500 sector ETF price movement. The project spans the entire pipeline — from raw article ingestion and distributed NLP scoring through statistical modeling to an interactive web dashboard backed by a live MySQL database and an LLM-powered natural-language-to-SQL analyst.

The system processes **252,187 articles** from 11 news sources, maps them to **12 market sectors** using keyword-based PySpark expressions, joins daily aggregated VADER sentiment scores against historical ETF price data from Yahoo Finance, and computes Pearson correlations, binary prediction accuracy, lagged (next-day) prediction accuracy, cross-sector effects, per-source reliability metrics, and sentiment–volatility relationships — all executed end-to-end in **Apache Spark 3.5.8**.

### Web Interface

The React + TypeScript frontend provides four pages:

- **Home** — Sector cards showing dataset share, prediction accuracy, correlation, and trading days for each ETF
- **Analysis** — Interactive dashboard with source/sector dropdowns, a price chart with prediction accuracy overlay, an RSI-style sentiment indicator, and sentiment/return bar charts — connected to a live MySQL backend via Flask API
- **Paper** — Research findings in an editorial layout with inline charts and data tables
- **About** — Team member profiles

## Key Findings

| Metric | Value |
|---|---|
| Articles Analyzed | 252,187 |
| Sector ETFs Evaluated | 12 (11 with sufficient data) |
| Matched Trading Days | 10,810 |
| Overall Prediction Accuracy | 51.6% (above 50% random baseline) |
| Overall Sentiment–Return Correlation | 0.0105 |

- **Consumer Discretionary (XLY)** and **Technology (XLK)** achieve 53–54% same-day prediction accuracy over 1,000+ trading days — statistically meaningful given sample size
- **International Business Times** is the most genuinely predictive single source at 57.1% accuracy (126 days)
- XLY and XLV show **improved next-day accuracy**, suggesting delayed market effects in consumer and health sectors — a potentially actionable signal
- **More articles ≠ better predictions**: ITA (Aerospace & Defense) has the most articles (72,793) yet the worst accuracy (49.3%), demonstrating that noisy geopolitical coverage dilutes signal quality
- Cross-sector sentiment correlations (e.g., ITA ↔ XLI at r = 0.296) reveal structural relationships in media coverage of economically linked sectors
- Results are broadly consistent with the **efficient market hypothesis** — sentiment provides a measurable but weak edge, confirming that publicly available news is rapidly priced in

## My Contributions

I served as the **technical lead and data pipeline architect** across all three project phases, owning the end-to-end flow from raw data ingestion through distributed analysis to production backend deployment.

### Phase 1 — Data Collection & System Design
- Executed the initial data collection under a compressed timeline, sourcing and uploading the foundational article datasets
- Designed the database schema and system architecture that guided all subsequent development
- Verified and configured the Apache Spark installation on the university cluster
- Defined the cross-sector analysis objective — testing whether sentiment in one sector correlates with returns in a seemingly unrelated sector (e.g., the "Pentagon pizza index" hypothesis) — which became a core differentiator of the project

### Phase 2 — Distributed Spark Pipeline & Statistical Analysis
- Collected historical ETF price data for all 12 S&P 500 sector ETFs via Yahoo Finance API calls (36,656 daily records, 2012–2024)
- Engineered the complete **PySpark data ingestion and analysis pipeline** on the university cluster, including three distinct join strategies:
  1. **Same-sector join** — matching average daily sentiment (collapsed across all articles per sector) with ETF return data by date and sector
  2. **Source-level join** — extending the aggregation to include `source_name`, enabling per-outlet prediction accuracy analysis
  3. **Cross-sector join** — computing Pearson correlations and binary prediction accuracy across all 132 sector pairs (12 × 11)
- Orchestrated the full data analysis workflow: daily sentiment aggregation (17,349 records), market data integration (10,810 matched trading days), lagged next-day analysis via Spark window functions, and SQLite export across 7 analysis tables

### Phase 3 — Data Integrity, Backend Architecture & Production Deployment
- **Identified and resolved a critical CSV parsing bug** that was silently dropping ~18,500 rows (~8% of the dataset). Through systematic testing of escape parameter configurations across each data file, discovered that Spark-written intermediates required `escape='\\'` while externally produced CSVs required `escape='"'`. Authored the master `rebuild_pipeline.py` script to regenerate all analysis tables from scratch with corrected parsing, ensuring full data consistency
- Produced additional time-series visualizations (Figures 7–9) addressing TA revision requests for lagged sentiment-return plots and cross-sector sentiment co-movement charts
- **Architected the production backend**: designed and implemented the Flask API layer connecting the React frontend to the MySQL database on the university cluster. Key endpoints include `/api/analysis` (parameterized time-series + statistics), `/api/sectors`, `/api/accuracy/by-source`, `/api/correlations/cross-sector`, and `/api/chat` (LLM analyst interface)
- Wrote the **SQLite-to-MySQL migration script** (`sqlite_to_mysql.py`) with automatic type inference and batch insert operations, enabling the transition from local development to the university's production database
- Orchestrated the API integration between the frontend, the LLM-powered natural-language-to-SQL pipeline (Gemini), and the MySQL daemon — enabling end users to query the analysis database in plain English and receive dynamic chart visualizations

## Tech Stack

### Frontend
- **React 18** with TypeScript
- **Vite** (SWC) for bundling and dev server
- **React Router** for client-side routing
- **Recharts** for interactive data visualizations
- **CSS** with custom properties (no external UI libraries)
- **Google Fonts** — DM Sans, JetBrains Mono, Instrument Serif

### Backend
- **Flask** (Python) API layer with Flask-CORS
- **PyMySQL** for database access
- **MySQL** hosted on the university cluster (production)
- **SQLite** used during development (7 analysis tables, 10,810+ rows)

### Data Pipeline
- **Apache Spark 3.5.8** with Hadoop 3 for distributed processing
- **PySpark** for sentiment aggregation, market joins, and correlation analysis
- **VADER** (Valence Aware Dictionary for Sentiment Reasoning) for NLP scoring
- **Yahoo Finance API** for historical ETF price data
- **Apache Parquet** for optimized parallel benchmarking (1.55× speedup at 4 workers)

### AI Analyst
- **Google Gemini** LLM for natural-language-to-SQL conversion
- Two-stage prompt pipeline: SQL generation → result interpretation + chart configuration
- Backend guardrails enforcing SELECT-only queries to prevent SQL injection

## Getting Started

```bash
# Clone the repo
git clone https://github.com/petrikatjosh/NewsAlpha-LangChain.git
cd newsalpha

# Install frontend dependencies
npm install

# Start the dev server
npm run dev
```

The app will be available at `http://localhost:5173`.

To connect to the live backend, establish an SSH tunnel to the university cluster and ensure Flask is running on port 5000. The frontend falls back to deterministic mock data if the backend is unreachable.

### Project Structure

```
src/
├── App.tsx                  # Router setup
├── pages/
│   ├── HomePage.tsx         # Landing page with sector cards
│   ├── AnalysisPage.tsx     # Interactive analysis dashboard
│   ├── PaperPage.tsx        # Research findings summary
│   └── AboutPage.tsx        # Team profiles
backend/
├── app.py                   # Flask API (production)
├── sqlite_to_mysql.py       # Database migration script
├── rebuild_pipeline.py      # Master pipeline rebuild script
├── source_sector_analysis.py
├── test_data_csv_escape.py  # CSV parsing validation tests
├── test_df_clean_saved_escape.py
└── test_finalclean_escape.py
```

## Data Pipeline

1. **Data Collection** — 252,187 articles scraped from sources including The Guardian, BBC News, CNN-DailyMail, GlobeNewswire, and others; 36,656 daily ETF price records from Yahoo Finance
2. **Sentiment Analysis** — VADER NLP scoring produces per-article compound sentiment values from −1 to +1
3. **Sector Mapping** — Article categories mapped to 12 S&P 500 sector ETFs via keyword-based PySpark expressions (84% mapping rate)
4. **Daily Aggregation** — Articles grouped by date and sector, producing 17,349 daily-sector summary records
5. **Market Join** — Inner join on date and sector with ETF data yields 10,810 matched trading-day records
6. **Impact Modeling** — Pearson correlations, binary prediction accuracy, lagged next-day analysis, cross-sector effects, per-source reliability, and sentiment–volatility analysis
7. **Storage & Serving** — Results exported to SQLite (dev) and MySQL (production), served via Flask REST API

## Performance

| Workers | Time (s) | Speedup | Efficiency |
|---|---|---|---|
| 1 | 5.13 | 1.00× | 100% |
| 2 | 4.08 | 1.26× | 62.9% |
| 4 | 3.31 | 1.55× | 38.7% |

Benchmarked on Apache Parquet format after converting from CSV to eliminate sequential I/O bottleneck (prior CSV benchmarks showed no speedup at ~20s constant regardless of worker count).

## License

This project was created for CS 179G at UC Riverside. All rights reserved.
