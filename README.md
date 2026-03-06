# NewsAlpha

**Predicting Market Direction Using Distributed Sentiment Analysis of Financial News**

CS 179G Senior Design Project · Group 7 · University of California, Riverside · 2026

---

## About

NewsAlpha is a web application built to visualize and explore the relationship between news sentiment and S&P 500 sector ETF performance. The project analyzes 233,609 articles from 11 news sources across 12 market sectors, using VADER sentiment scoring and Apache Spark for distributed processing.

The front end provides four pages:

- **Home** — Project overview with sector cards showing dataset share, prediction accuracy, correlation, and trading days for each of the 12 ETFs
- **Analysis** — Interactive dashboard with dropdowns for news source, news sector, and market sector. Features a price chart with prediction accuracy overlay, an RSI-style sentiment indicator, and separate sentiment/return bar charts. Currently displays mock data — backend connection is in progress
- **Paper** — Research findings presented in an editorial layout with inline charts and data tables covering same-day prediction, next-day lagged analysis, source reliability, cross-sector effects, and volatility analysis
- **About** — Team member profiles with individual contributions

## Key Findings

| Metric | Value |
|---|---|
| Articles Analyzed | 233,609 |
| Sector ETFs | 12 |
| Matched Trading Days | 10,080 |
| Overall Prediction Accuracy | 51.7% |
| Overall Sentiment-Return Correlation | 0.014 |

- Consumer Discretionary (XLY) and Technology (XLK) achieve 53–54% same-day prediction accuracy with 800–1,500 trading days
- International Business Times is the most genuinely predictive source at 57.1% accuracy
- XLY and XLV show improved next-day accuracy, suggesting delayed market effects in consumer and health sectors
- Real Estate (XLRE) exhibits nonlinear volatility responses to sentiment, consistent with loss aversion theory

## Tech Stack

- **React 18** with TypeScript
- **Vite** (SWC) for bundling and dev server
- **React Router** for client-side routing
- **CSS** with custom properties (no external UI libraries)
- **Google Fonts** — DM Sans, JetBrains Mono, Instrument Serif

### Backend (planned)

- **MySQL** database hosted on the university cluster
- **SQLite** used during development (7 analysis tables, 10,080+ rows)
- **Apache Spark 3.5.8** for data processing pipeline
- **Yahoo Finance** for historical ETF price data

## Getting Started

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The app will be available at `http://localhost:5173`.

### Project Structure

```
src/
├── App.tsx                  # Router setup
├── pages/
│   ├── HomePage.tsx         # Landing page with sector cards
│   ├── HomePage.css
│   ├── AnalysisPage.tsx     # Interactive analysis dashboard
│   ├── AnalysisPage.css
│   ├── PaperPage.tsx        # Research findings summary
│   ├── PaperPage.css
│   ├── AboutPage.tsx        # Team profiles
│   └── AboutPage.css
```

## Data Pipeline

1. **Data Collection** — 233,609 articles scraped from sources including The Guardian, BBC News, CNN-DailyMail, GlobeNewswire, and others
2. **Sentiment Analysis** — VADER NLP scoring produces per-article compound sentiment values from −1 to +1
3. **Sector Mapping** — Article categories mapped to 12 S&P 500 sector ETFs via keyword-based PySpark expressions
4. **Impact Modeling** — Pearson correlations and binary prediction accuracy measure sentiment-to-price relationships

## Team

| Name | Contribution |
|---|---|
| Edward | Spark execution, reproducibility validation, front-end development |
| Gelvesh | Cross-sector sentiment-to-market prediction analysis and heatmap visualization |
| HaiShan | Dataset integrity verification and CSV parsing validation |
| John-Paul | Initial article data processing |
| Josh | Spark pipeline development, ETF data collection, benchmarking, SQLite export |
| Rafat | Volatility analysis, LOESS smoothing, sentiment quintile breakdowns |

## License

This project was created for CS 179G at UC Riverside. All rights reserved.