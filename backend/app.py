"""
NewsAlpha — Flask API Backend (with Chatbot)
=============================================
Serves MySQL analysis data + chatbot to the React frontend.
XLRE excluded from all results per TA recommendation (only 37 trading days).

Usage:
    pip install flask flask-cors pymysql
    python app.py

Environment variables (set these before running):
    MYSQL_HOST     — default: 127.0.0.1
    MYSQL_PORT     — default: 3306
    MYSQL_USER     — default: root
    MYSQL_PASSWORD — default: (empty)
    MYSQL_DB       — default: mysql
"""

import pymysql
import os
import re
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from langchain_backend import langchain_bp   # near top

app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------------
# Database helper — MySQL via PyMySQL
# ---------------------------------------------------------------------------
MYSQL_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.environ.get("MYSQL_PORT", 3306)),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", ""),
    "database": os.environ.get("MYSQL_DB", "mysql"),
    "cursorclass": pymysql.cursors.DictCursor,
}

# Sector excluded due to insufficient sample size (37 trading days)
EXCLUDE = "XLRE"


def get_db():
    if "db" not in g:
        g.db = pymysql.connect(**MYSQL_CONFIG)
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query_db(sql, args=(), one=False):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(sql, args)
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows


# ---------------------------------------------------------------------------
# Health / meta
# ---------------------------------------------------------------------------
@app.route("/api/health")
def health():
    try:
        count = query_db(
            "SELECT COUNT(*) as n FROM joined_sentiment_market WHERE sector != %s",
            [EXCLUDE], one=True,
        )
        tables = query_db("SELECT table_name AS name FROM information_schema.tables WHERE table_schema = %s ORDER BY table_name", [MYSQL_CONFIG['database']])
        return jsonify({
            "status": "ok",
            "database": MYSQL_CONFIG['database'],
            "joined_rows": count["n"],
            "tables": [t["name"] for t in tables],
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# HOME PAGE
# ---------------------------------------------------------------------------
@app.route("/api/sectors")
def sectors():
    accuracy = query_db(
        "SELECT * FROM prediction_accuracy WHERE sector != %s ORDER BY accuracy DESC",
        [EXCLUDE],
    )
    correlations = query_db(
        "SELECT * FROM sector_correlations WHERE sector != %s ORDER BY correlation DESC",
        [EXCLUDE],
    )
    corr_map = {r["sector"]: r for r in correlations}
    article_counts = query_db("""
        SELECT sector, SUM(article_count) as total_articles
        FROM joined_sentiment_market
        WHERE sector != %s
        GROUP BY sector
    """, [EXCLUDE])
    article_map = {r["sector"]: r["total_articles"] for r in article_counts}

    result = []
    for row in accuracy:
        sector = row["sector"]
        corr_data = corr_map.get(sector, {})
        result.append({
            "sector": sector,
            "accuracy": row.get("accuracy"),
            "days": row.get("num_days"),
            "correlation": corr_data.get("correlation"),
            "mean_sentiment": corr_data.get("mean_sentiment"),
            "total_articles": article_map.get(sector, 0),
        })
    return jsonify(result)


# ---------------------------------------------------------------------------
# ANALYSIS PAGE
# ---------------------------------------------------------------------------
@app.route("/api/timeseries")
def timeseries():
    sector = request.args.get("sector")
    if not sector:
        return jsonify({"error": "sector parameter is required"}), 400
    if sector.upper() == EXCLUDE:
        return jsonify([])

    sql = "SELECT * FROM joined_sentiment_market WHERE sector = %s"
    args = [sector]

    start = request.args.get("start")
    end = request.args.get("end")
    if start:
        sql += " AND date >= %s"
        args.append(start)
    if end:
        sql += " AND date <= %s"
        args.append(end)

    sql += " ORDER BY date ASC"
    return jsonify(query_db(sql, args))


@app.route("/api/timeseries/all")
def timeseries_all():
    sql = "SELECT * FROM joined_sentiment_market WHERE sector != %s"
    args = [EXCLUDE]

    start = request.args.get("start")
    end = request.args.get("end")
    if start:
        sql += " AND date >= %s"
        args.append(start)
    if end:
        sql += " AND date <= %s"
        args.append(end)

    sql += " ORDER BY date ASC, sector ASC"
    return jsonify(query_db(sql, args))


# ---------------------------------------------------------------------------
# ANALYSIS PAGE — combined endpoint for the AnalysisPage dashboard
# ---------------------------------------------------------------------------
def _parse_date(date_str):
    """Parse dates from the DB. Handles MM-DD-YYYY, YYYY-MM-DD, and similar."""
    if not date_str:
        return None
    parts = date_str.replace("/", "-").split("-")
    try:
        if len(parts[0]) == 4:
            # YYYY-MM-DD
            return (int(parts[0]), int(parts[1]), int(parts[2]))
        else:
            # MM-DD-YYYY
            return (int(parts[2]), int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        return None


def _format_date(date_str):
    """Convert raw DB date to readable 'Jan 15, 2019' format."""
    parsed = _parse_date(date_str)
    if not parsed:
        return date_str
    y, m, d = parsed
    month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{month_names[m]} {d}, {y}"


def _sort_rows_by_date(rows):
    """Sort row dicts by their 'date' field chronologically."""
    return sorted(rows, key=lambda r: _parse_date(r.get("date", "")) or (0, 0, 0))


@app.route("/api/analysis")
def analysis():
    """
    Combined endpoint powering the AnalysisPage dashboard.
    Query params:
        news_sector   (required) — e.g. XLK
        market_sector (required) — e.g. XLK
        source        (optional) — e.g. "all", "guardian", etc.

    Returns JSON with: dailyData, priceSeries, correlation, accuracy,
    tradingDays, meanSentiment, meanReturn, articles, isLimited
    """
    news_sector = request.args.get("news_sector", "XLK").upper()
    market_sector = request.args.get("market_sector", "XLK").upper()
    source = request.args.get("source", "all")

    if news_sector == EXCLUDE or market_sector == EXCLUDE:
        return jsonify({"error": f"{EXCLUDE} excluded (insufficient sample size)"}), 400

    same_sector = news_sector == market_sector
    is_limited = False

    # ── Daily time-series data ──
    # Full daily data is available for same-sector, all-sources
    if same_sector:
        daily_rows = query_db(
            """SELECT date, avg_sentiment AS sentiment,
                      daily_return_pct AS returnPct,
                      article_count, market_direction
               FROM joined_sentiment_market
               WHERE sector = %s
               ORDER BY date""",
            [market_sector],
        )
        if source != "all":
            is_limited = True  # can't filter by source in this table
    else:
        # Cross-sector: sentiment from news_sector, returns from market_sector
        # Join on matching dates using the same joined_sentiment_market table
        daily_rows = query_db(
            """SELECT m.date AS date,
                      n.avg_sentiment AS sentiment,
                      m.daily_return_pct AS returnPct,
                      n.article_count AS article_count,
                      m.market_direction AS market_direction
               FROM joined_sentiment_market m
               INNER JOIN joined_sentiment_market n
                   ON m.date = n.date
               WHERE m.sector = %s AND n.sector = %s
               ORDER BY m.date""",
            [market_sector, news_sector],
        )
        is_limited = False

    # ── Sort chronologically (DB date format may not sort as strings) ──
    daily_rows = _sort_rows_by_date(daily_rows)

    # ── Build price series from cumulative returns ──
    price = 100.0
    price_series = []
    for row in daily_rows:
        ret = row["returnPct"] or 0
        price *= (1 + ret / 100)
        price = max(price, 1)
        sent = row["sentiment"]
        predicted = None
        if sent is not None:
            predicted = (sent >= 0 and ret >= 0) or (sent < 0 and ret < 0)
        price_series.append({
            "date": _format_date(row["date"]),
            "price": round(price, 2),
            "sentiment": round(sent, 4) if sent is not None else None,
            "returnPct": round(ret, 4),
            "predicted": predicted,
        })

    # ── Monthly-bucketed bar chart data ──
    daily_data = _bucket_monthly(daily_rows)

    # ── Correlation ──
    if same_sector:
        corr_row = query_db(
            "SELECT correlation FROM sector_correlations WHERE sector = %s",
            [news_sector], one=True,
        )
        correlation = corr_row["correlation"] if corr_row else 0.0
    else:
        corr_row = query_db(
            """SELECT correlation FROM cross_sector_correlations
               WHERE sent_sector = %s AND mkt_sector = %s""",
            [news_sector, market_sector], one=True,
        )
        correlation = corr_row["correlation"] if corr_row else 0.0

    # ── Prediction accuracy ──
    source_map = {
        "guardian": "The Guardian", "cnn_dailymail": "CNN-DailyMail/Other",
        "ibt": "International Business Times", "globenewswire": "GlobeNewswire",
        "times_of_india": "The Times of India", "bbc": "BBC News",
        "npr": "NPR", "boing_boing": "Boing Boing",
        "business_insider": "Business Insider",
        "globalsecurity": "Globalsecurity.org", "abc": "ABC News",
    }

    if source != "all":
        source_name = source_map.get(source, source)
        acc_row = query_db(
            "SELECT accuracy, num_days FROM source_accuracy WHERE source_name = %s",
            [source_name], one=True,
        )
        acc = acc_row["accuracy"] if acc_row else 0.5
        trading_days = acc_row["num_days"] if acc_row else 0
    elif same_sector:
        acc_row = query_db(
            "SELECT accuracy, num_days FROM prediction_accuracy WHERE sector = %s",
            [news_sector], one=True,
        )
        acc = acc_row["accuracy"] if acc_row else 0.5
        trading_days = acc_row["num_days"] if acc_row else 0
    else:
        # Cross-sector: compute accuracy from the joined data we already fetched
        correct = 0
        total = 0
        for r in daily_rows:
            s = r["sentiment"]
            ret = r["returnPct"]
            if s is not None and ret is not None:
                if (s >= 0 and ret >= 0) or (s < 0 and ret < 0):
                    correct += 1
                total += 1
        acc = correct / total if total > 0 else 0.5
        trading_days = total

    # ── Aggregate stats ──
    sentiments = [r["sentiment"] for r in daily_rows if r["sentiment"] is not None]
    returns = [r["returnPct"] for r in daily_rows if r["returnPct"] is not None]
    articles_list = [r["article_count"] for r in daily_rows if r.get("article_count")]

    mean_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
    mean_return = sum(returns) / len(returns) if returns else 0
    total_articles = sum(articles_list) if articles_list else 0

    accuracy_pct = acc * 100 if acc <= 1 else acc

    return jsonify({
        "dailyData": daily_data,
        "priceSeries": price_series,
        "correlation": round(correlation, 4) if correlation else 0,
        "accuracy": round(accuracy_pct, 1),
        "tradingDays": trading_days if trading_days else len(daily_rows),
        "meanSentiment": round(mean_sentiment, 4),
        "meanReturn": round(mean_return, 6),
        "articles": int(total_articles),
        "isLimited": is_limited,
    })


def _bucket_monthly(rows):
    """Group daily rows into ~monthly buckets for the bar charts."""
    if not rows:
        return []
    buckets = {}
    for r in rows:
        parsed = _parse_date(r["date"])
        if not parsed:
            continue
        y, m, _d = parsed
        ym = f"{y:04d}-{m:02d}"  # "2019-03" — sorts chronologically
        if ym not in buckets:
            buckets[ym] = {"sents": [], "rets": []}
        if r["sentiment"] is not None:
            buckets[ym]["sents"].append(r["sentiment"])
        if r["returnPct"] is not None:
            buckets[ym]["rets"].append(r["returnPct"])

    month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    result = []
    for ym in sorted(buckets.keys()):
        b = buckets[ym]
        sent_avg = sum(b["sents"]) / len(b["sents"]) if b["sents"] else 0
        ret_avg = sum(b["rets"]) / len(b["rets"]) if b["rets"] else 0
        year, month = ym.split("-")
        label = f"{month_names[int(month)]} '{year[2:]}"
        result.append({
            "date": label,
            "sentiment": round(sent_avg, 4),
            "returnPct": round(ret_avg, 4),
        })
    if len(result) > 30:
        step = len(result) // 24
        result = result[::step]
    return result


# ---------------------------------------------------------------------------
# CORRELATIONS
# ---------------------------------------------------------------------------
@app.route("/api/correlations/same-sector")
def same_sector_correlations():
    return jsonify(query_db(
        "SELECT * FROM sector_correlations WHERE sector != %s ORDER BY correlation DESC",
        [EXCLUDE],
    ))


@app.route("/api/correlations/cross-sector")
def cross_sector_correlations():
    min_days = request.args.get("min_days", 0, type=int)
    return jsonify(query_db(
        """SELECT * FROM cross_sector_correlations
           WHERE days >= %s AND sent_sector != %s AND mkt_sector != %s
           ORDER BY ABS(correlation) DESC""",
        [min_days, EXCLUDE, EXCLUDE],
    ))


@app.route("/api/correlations/next-day")
def next_day_correlations():
    return jsonify(query_db(
        "SELECT * FROM next_day_correlations WHERE sector != %s",
        [EXCLUDE],
    ))


# ---------------------------------------------------------------------------
# PREDICTION ACCURACY
# ---------------------------------------------------------------------------
@app.route("/api/accuracy/same-day")
def same_day_accuracy():
    return jsonify(query_db(
        "SELECT * FROM prediction_accuracy WHERE sector != %s ORDER BY accuracy DESC",
        [EXCLUDE],
    ))


@app.route("/api/accuracy/next-day")
def next_day_accuracy():
    return jsonify(query_db(
        "SELECT * FROM next_day_accuracy WHERE sector != %s ORDER BY next_day_accuracy DESC",
        [EXCLUDE],
    ))


@app.route("/api/accuracy/by-source")
def source_accuracy():
    return jsonify(query_db(
        "SELECT * FROM source_accuracy ORDER BY accuracy DESC"
    ))


# ---------------------------------------------------------------------------
# VOLATILITY
# ---------------------------------------------------------------------------
@app.route("/api/volatility")
def volatility():
    try:
        return jsonify(query_db(
            "SELECT * FROM volatility_correlations WHERE sector != %s ORDER BY correlation ASC",
            [EXCLUDE],
        ))
    except Exception:
        return jsonify({"error": "volatility_correlations table not found"}), 404


# ---------------------------------------------------------------------------
# STATS
# ---------------------------------------------------------------------------
@app.route("/api/stats/overview")
def overview_stats():
    joined_count = query_db(
        "SELECT COUNT(*) as n FROM joined_sentiment_market WHERE sector != %s",
        [EXCLUDE], one=True,
    )
    sector_count = query_db(
        "SELECT COUNT(DISTINCT sector) as n FROM joined_sentiment_market WHERE sector != %s",
        [EXCLUDE], one=True,
    )
    overall_corr = query_db(
        "SELECT AVG(correlation) as avg_correlation FROM sector_correlations WHERE sector != %s",
        [EXCLUDE], one=True,
    )
    overall_acc = query_db(
        """SELECT SUM(accuracy * num_days) / SUM(num_days) as weighted_accuracy,
           SUM(num_days) as total_days
           FROM prediction_accuracy WHERE sector != %s""",
        [EXCLUDE], one=True,
    )
    date_range = query_db(
        "SELECT MIN(date) as min_date, MAX(date) as max_date FROM joined_sentiment_market WHERE sector != %s",
        [EXCLUDE], one=True,
    )
    return jsonify({
        "total_matched_days": joined_count["n"],
        "sectors": sector_count["n"],
        "overall_correlation": overall_corr["avg_correlation"],
        "overall_accuracy": overall_acc["weighted_accuracy"],
        "date_range": {"start": date_range["min_date"], "end": date_range["max_date"]},
    })


@app.route("/api/stats/sector/<ticker>")
def sector_detail(ticker):
    ticker = ticker.upper()
    if ticker == EXCLUDE:
        return jsonify({"error": f"{EXCLUDE} excluded due to insufficient sample size"}), 404

    corr = query_db("SELECT * FROM sector_correlations WHERE sector = %s", [ticker], one=True)
    acc = query_db("SELECT * FROM prediction_accuracy WHERE sector = %s", [ticker], one=True)
    next_acc = query_db("SELECT * FROM next_day_accuracy WHERE sector = %s", [ticker], one=True)
    ts_summary = query_db(
        """SELECT COUNT(*) as trading_days, MIN(date) as first_date, MAX(date) as last_date,
           AVG(avg_sentiment) as mean_sentiment, AVG(daily_return_pct) as mean_return
           FROM joined_sentiment_market WHERE sector = %s""",
        [ticker], one=True,
    )
    return jsonify({
        "sector": ticker,
        "correlation": dict(corr) if corr else None,
        "accuracy": dict(acc) if acc else None,
        "next_day_accuracy": dict(next_acc) if next_acc else None,
        "summary": dict(ts_summary) if ts_summary else None,
    })


# ---------------------------------------------------------------------------
# FILTERS
# ---------------------------------------------------------------------------
@app.route("/api/filters")
def filters():
    sectors = query_db(
        "SELECT DISTINCT sector FROM joined_sentiment_market WHERE sector != %s ORDER BY sector",
        [EXCLUDE],
    )
    sources = query_db(
        "SELECT DISTINCT source_name FROM source_accuracy ORDER BY source_name"
    )
    return jsonify({
        "sectors": [r["sector"] for r in sectors],
        "sources": [r["source_name"] for r in sources],
    })


# ===========================================================================
# CHATBOT
# ===========================================================================

# Column reference:
# prediction_accuracy:        sector, accuracy, num_days
# sector_correlations:        sector, correlation, mean_sentiment, mean_return, days
# next_day_accuracy:          sector, next_day_accuracy, days
# source_accuracy:            source_name, accuracy, num_days, mean_sentiment
# cross_sector_correlations:  sent_sector, mkt_sector, correlation, days
# joined_sentiment_market:    date, sector, avg_sentiment, article_count, sentiment_std,
#                             open, close, daily_return_pct, market_direction, volume

CHAT_PATTERNS = [
    # ── Sector accuracy ──
    {
        "patterns": [
            r"(?:which|what).*(?:sector|etf).*(?:most|best|highest).*(?:accura|predict)",
            r"(?:best|top|highest).*(?:predict|accura).*(?:sector|etf)",
            r"most accurate sector",
        ],
        "sql": "SELECT sector, accuracy, num_days FROM prediction_accuracy WHERE sector != 'XLRE' ORDER BY accuracy DESC LIMIT 3",
        "template": "The top sectors by same-day prediction accuracy are:\n{rows}",
        "format": lambda r: f"  • {r['sector']} — {r['accuracy']*100:.1f}% ({r['num_days']} trading days)",
    },
    {
        "patterns": [
            r"(?:which|what).*(?:sector|etf).*(?:worst|lowest|least).*(?:accura|predict)",
            r"worst.*(?:predict|accura)",
        ],
        "sql": "SELECT sector, accuracy, num_days FROM prediction_accuracy WHERE sector != 'XLRE' ORDER BY accuracy ASC LIMIT 3",
        "template": "The worst-performing sectors by prediction accuracy are:\n{rows}",
        "format": lambda r: f"  • {r['sector']} — {r['accuracy']*100:.1f}% ({r['num_days']} trading days)",
    },
    # ── Overall accuracy ──
    {
        "patterns": [
            r"overall.*accura",
            r"(?:total|average|general).*accura",
            r"how accurate",
        ],
        "sql": "SELECT SUM(accuracy * num_days) / SUM(num_days) as accuracy, SUM(num_days) as total_days FROM prediction_accuracy WHERE sector != 'XLRE'",
        "template": "The overall weighted prediction accuracy across all sectors is {accuracy_pct} based on {total_days} trading days. This exceeds the 50% random baseline, though modestly.",
        "single": True,
    },
    # ── Correlations ──
    {
        "patterns": [
            r"(?:which|what).*(?:sector|etf).*(?:highest|strongest|best).*corr",
            r"(?:strongest|highest|best).*corr",
        ],
        "sql": "SELECT sector, correlation, days FROM sector_correlations WHERE sector != 'XLRE' ORDER BY correlation DESC LIMIT 3",
        "template": "The sectors with the strongest sentiment-to-return correlations are:\n{rows}",
        "format": lambda r: f"  • {r['sector']} — r={r['correlation']:.4f} ({r['days']} days)",
    },
    {
        "patterns": [
            r"overall.*corr",
            r"(?:average|general).*corr",
        ],
        "sql": "SELECT AVG(correlation) as avg_corr FROM sector_correlations WHERE sector != 'XLRE'",
        "template": "The overall sentiment-return correlation across all sectors is {avg_corr}. This is very weak, consistent with the efficient market hypothesis — public news sentiment is largely already priced in.",
        "single": True,
    },
    # ── Cross-sector ──
    {
        "patterns": [
            r"cross.?sector",
            r"(?:sector|etf).*(?:predict|affect|influence).*(?:another|other|different)",
        ],
        "sql": "SELECT sent_sector, mkt_sector, correlation, days FROM cross_sector_correlations WHERE days > 50 AND sent_sector != 'XLRE' AND mkt_sector != 'XLRE' ORDER BY ABS(correlation) DESC LIMIT 5",
        "template": "The strongest cross-sector sentiment-to-return correlations (50+ trading days, excluding XLRE) are:\n{rows}",
        "format": lambda r: f"  • {r['sent_sector']} -> {r['mkt_sector']} — r={r['correlation']:.4f} ({r['days']} days)",
    },
    # ── Correlation between two specific sectors ──
    {
        "patterns": [
            r"(?:correlation|relationship|connection|significant|between).*(?:energy|tech|financ|health|real estate|consumer|industrial|defense|communication|leisure|homebuilder|staple|XLK|XLF|XLY|XLI|XLC|XLE|XLP|XLV|XHB|ITA|PEJ)",
        ],
        "handler": "two_sector_lookup",
    },
    # ── News sources ──
    {
        "patterns": [
            r"(?:which|what).*(?:source|outlet|news).*(?:best|most|reliable|accurate)",
            r"(?:best|most reliable|most accurate).*(?:source|outlet|news)",
        ],
        "sql": "SELECT source_name, accuracy, num_days, mean_sentiment FROM source_accuracy ORDER BY accuracy DESC LIMIT 5",
        "template": "The most accurate news sources for market prediction are:\n{rows}\nNote: GlobeNewswire's high accuracy is inflated by extreme positivity bias (mean sentiment 0.93). International Business Times is the most genuinely predictive with balanced sentiment.",
        "format": lambda r: f"  • {r['source_name']} — {r['accuracy']*100:.1f}% ({r['num_days']} days, sentiment {r['mean_sentiment']:.2f})",
    },
    {
        "patterns": [
            r"(?:which|what).*(?:source|outlet|news).*(?:worst|least|unreliable)",
            r"worst.*(?:source|outlet|news)",
        ],
        "sql": "SELECT source_name, accuracy, num_days, mean_sentiment FROM source_accuracy ORDER BY accuracy ASC LIMIT 3",
        "template": "The least accurate news sources are:\n{rows}\nBBC News and ABC News perform below random chance (50%), likely because their negative editorial tone doesn't track market movements well.",
        "format": lambda r: f"  • {r['source_name']} — {r['accuracy']*100:.1f}% ({r['num_days']} days)",
    },
    # ── Next-day / lagged ──
    {
        "patterns": [
            r"next.?day",
            r"lag",
            r"(?:predict|forecast).*(?:tomorrow|next|future)",
        ],
        "sql": """
            SELECT p.sector, p.accuracy as same_day, n.next_day_accuracy as next_day,
                   (n.next_day_accuracy - p.accuracy) as change, p.num_days
            FROM prediction_accuracy p
            JOIN next_day_accuracy n ON p.sector = n.sector
            WHERE p.sector != 'XLRE'
            ORDER BY change DESC LIMIT 5
        """,
        "template": "Sectors where next-day prediction improves over same-day:\n{rows}\nXLY and XLV show improved next-day accuracy, suggesting delayed market effects in consumer and health sectors.",
        "format": lambda r: f"  • {r['sector']} — same-day {r['same_day']*100:.1f}% -> next-day {r['next_day']*100:.1f}% ({'+' if r['change']>0 else ''}{r['change']*100:.1f}%)",
    },
    # ── Specific sector lookup ──
    {
        "patterns": [
            r"(?:tell|show|what about|info|data|how).*\b(XLK|XLF|XLY|XLI|XLC|XLE|XLP|XLV|XHB|ITA|PEJ)\b",
            r"\b(XLK|XLF|XLY|XLI|XLC|XLE|XLP|XLV|XHB|ITA|PEJ)\b.*(?:accuracy|corr|predict|performance|how|doing)",
        ],
        "handler": "sector_lookup",
    },
    # ── Dataset stats ──
    {
        "patterns": [
            r"how (?:much|many).*(?:data|article|record|row)",
            r"(?:dataset|data).*(?:size|count|total)",
            r"how (?:big|large)",
        ],
        "sql": """
            SELECT
                (SELECT COUNT(*) FROM joined_sentiment_market WHERE sector != 'XLRE') as joined_rows,
                (SELECT COUNT(DISTINCT sector) FROM joined_sentiment_market WHERE sector != 'XLRE') as sectors
        """,
        "template": "The dataset contains {joined_rows} matched sentiment-market records across {sectors} sector ETFs (XLRE excluded due to limited sample size). The project analyzed 233,609 articles from 11 news sources, which after sector mapping and market-day matching produced these joined records.",
        "single": True,
    },
    # ── Trading days ──
    {
        "patterns": [
            r"(?:how many|number of).*(?:trading|trade).*days",
            r"trading days",
        ],
        "sql": "SELECT sector, num_days FROM prediction_accuracy WHERE sector != 'XLRE' ORDER BY num_days DESC",
        "template": "Trading days per sector:\n{rows}",
        "format": lambda r: f"  • {r['sector']} — {r['num_days']} days",
    },
    # ── Volatility ──
    {
        "patterns": [
            r"volatilit",
            r"(?:sentiment|news).*(?:magnitude|size|absolute).*(?:return|move)",
        ],
        "static": "The overall sentiment-volatility correlation is r = -0.026 (p = 0.009) — statistically significant but practically meaningless. Most sectors show negligible correlations (|r| < 0.10). Sentiment does not meaningfully predict volatility at the aggregate level, consistent with the efficient market hypothesis.",
    },
    # ── Project overview / greeting ──
    {
        "patterns": [
            r"(?:what|tell).*(?:project|about|overview|summary)",
            r"what (?:is|does) newsalpha",
            r"^(?:hi|hello|hey|help)",
        ],
        "static": "NewsAlpha analyzes the relationship between news sentiment and S&P 500 sector ETF performance. We processed 233,609 articles from 11 news sources using VADER sentiment analysis and Apache Spark, mapping them to 11 market sectors.\n\nKey findings: overall prediction accuracy is 51.7% (above 50% random baseline), with Consumer Discretionary (XLY) and Technology (XLK) performing best at 53-54%.\n\nTry asking me about:\n  • Sector accuracy — 'which sector is most accurate%s'\n  • News sources — 'which news source is best%s'\n  • Correlations — 'strongest correlation%s'\n  • Specific sectors — 'tell me about XLK' or 'how is energy doing%s'\n  • Two sectors — 'correlation between energy and financials'\n  • Next-day predictions — 'next-day accuracy'\n  • Cross-sector effects — 'cross-sector correlations'\n  • Volatility — 'volatility findings'",
    },
]

# Map common names to tickers for natural language queries
NAME_TO_TICKER = {
    "energy": "XLE", "tech": "XLK", "technology": "XLK",
    "financ": "XLF", "financial": "XLF", "financials": "XLF",
    "health": "XLV", "healthcare": "XLV", "health care": "XLV",
    "consumer disc": "XLY", "consumer discretionary": "XLY",
    "industrial": "XLI", "industrials": "XLI",
    "defense": "ITA", "aerospace": "ITA",
    "communication": "XLC", "communications": "XLC", "telecom": "XLC",
    "leisure": "PEJ", "entertainment": "PEJ",
    "homebuilder": "XHB", "homebuilders": "XHB", "housing": "XHB",
    "staple": "XLP", "staples": "XLP", "consumer staples": "XLP",
}

TICKERS = {"XLK", "XLF", "XLY", "XLI", "XLC", "XLE", "XLP", "XLV", "XHB", "ITA", "PEJ"}


def resolve_ticker(text):
    upper = text.upper()
    for t in TICKERS:
        if t in upper:
            return t
    lower = text.lower()
    for name, ticker in sorted(NAME_TO_TICKER.items(), key=lambda x: -len(x[0])):
        if name in lower:
            return ticker
    return None


def resolve_all_tickers(text):
    found = []
    upper = text.upper()
    for t in TICKERS:
        if t in upper and t not in found:
            found.append(t)
    lower = text.lower()
    for name, ticker in sorted(NAME_TO_TICKER.items(), key=lambda x: -len(x[0])):
        if name in lower and ticker not in found:
            found.append(ticker)
    return found


def handle_sector_lookup(question):
    ticker = resolve_ticker(question)
    if not ticker:
        return None

    acc = query_db("SELECT * FROM prediction_accuracy WHERE sector = %s", [ticker], one=True)
    corr = query_db("SELECT * FROM sector_correlations WHERE sector = %s", [ticker], one=True)
    next_acc = query_db("SELECT * FROM next_day_accuracy WHERE sector = %s", [ticker], one=True)
    articles = query_db(
        "SELECT SUM(article_count) as total FROM joined_sentiment_market WHERE sector = %s",
        [ticker], one=True,
    )

    parts = [f"Here's what I have on {ticker}:"]
    if acc:
        parts.append(f"  • Same-day prediction accuracy: {acc['accuracy']*100:.1f}% ({acc['num_days']} trading days)")
    if next_acc:
        parts.append(f"  • Next-day prediction accuracy: {next_acc['next_day_accuracy']*100:.1f}%")
    if corr:
        parts.append(f"  • Sentiment-return correlation: {corr['correlation']:.4f}")
        parts.append(f"  • Mean sentiment: {corr['mean_sentiment']:.4f}")
    if articles and articles.get("total"):
        parts.append(f"  • Total articles contributing: {int(articles['total']):,}")
    return "\n".join(parts)


def handle_two_sector_lookup(question):
    found = resolve_all_tickers(question)
    if len(found) < 2:
        return None

    s1, s2 = found[0], found[1]

    row1 = query_db(
        "SELECT * FROM cross_sector_correlations WHERE sent_sector = %s AND mkt_sector = %s",
        [s1, s2], one=True,
    )
    row2 = query_db(
        "SELECT * FROM cross_sector_correlations WHERE sent_sector = %s AND mkt_sector = %s",
        [s2, s1], one=True,
    )

    parts = [f"Cross-sector relationship between {s1} and {s2}:"]
    if row1:
        parts.append(f"  • {s1} sentiment -> {s2} returns: r={row1['correlation']:.4f} ({row1['days']} days)")
    if row2:
        parts.append(f"  • {s2} sentiment -> {s1} returns: r={row2['correlation']:.4f} ({row2['days']} days)")
    if not row1 and not row2:
        parts.append("  No cross-sector data found for this pair.")
    else:
        max_corr = max(abs(row1['correlation']) if row1 else 0, abs(row2['correlation']) if row2 else 0)
        if max_corr < 0.05:
            parts.append("\nThis is a very weak relationship — essentially no predictive signal.")
        elif max_corr < 0.15:
            parts.append("\nThis is a weak but measurable relationship.")
        else:
            parts.append("\nThis is a notable relationship, though sample size should be considered.")
    return "\n".join(parts)


def process_chat(question):
    question_lower = question.lower().strip()

    # Block XLRE questions
    if "xlre" in question_lower or "real estate" in question_lower:
        return "XLRE (Real Estate) has been excluded from our analysis due to insufficient sample size (only 37 matched trading days). The limited data made results statistically unreliable. Try asking about another sector!"

    for entry in CHAT_PATTERNS:
        matched = False
        for pattern in entry["patterns"]:
            if re.search(pattern, question_lower) or re.search(pattern, question.upper()):
                matched = True
                break
        if not matched:
            continue

        # Static response
        if "static" in entry:
            return entry["static"]

        # Custom handlers
        if entry.get("handler") == "sector_lookup":
            result = handle_sector_lookup(question)
            if result:
                return result
            continue

        if entry.get("handler") == "two_sector_lookup":
            result = handle_two_sector_lookup(question)
            if result:
                return result
            continue

        # SQL query
        if entry.get("sql"):
            if entry.get("single"):
                row = query_db(entry["sql"], one=True)
                if row:
                    formatted = {}
                    for k, v in row.items():
                        if isinstance(v, float):
                            if abs(v) < 1:
                                formatted[k] = f"{v:.4f}"
                            else:
                                formatted[k] = f"{v:,.0f}"
                            formatted[f"{k}_pct"] = f"{v*100:.1f}%"
                        else:
                            formatted[k] = str(v) if v is not None else "N/A"
                    return entry["template"].format(**formatted)
            else:
                rows = query_db(entry["sql"])
                if rows:
                    formatted_rows = "\n".join(entry["format"](r) for r in rows)
                    return entry["template"].format(rows=formatted_rows)

    # ── Fallback: check if they mentioned a sector name we can look up ──
    ticker = resolve_ticker(question)
    if ticker:
        result = handle_sector_lookup(question)
        if result:
            return result

    return (
        "I'm not sure how to answer that. Try asking about:\n"
        "  • Sector prediction accuracy (e.g. 'which sector is most accurate%s')\n"
        "  • News source reliability (e.g. 'which news source is best%s')\n"
        "  • Correlations (e.g. 'strongest correlation%s')\n"
        "  • Specific sectors (e.g. 'tell me about XLK' or 'how is energy doing%s')\n"
        "  • Two-sector relationships (e.g. 'correlation between energy and financials')\n"
        "  • Next-day predictions (e.g. 'next-day accuracy')\n"
        "  • Cross-sector effects (e.g. 'cross-sector correlations')\n"
        "  • Dataset stats (e.g. 'how much data%s')\n"
        "  • Volatility analysis (e.g. 'volatility findings')"
    )


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "question is required"}), 400

    try:
        answer = process_chat(question)
        return jsonify({"question": question, "answer": answer})
    except Exception as e:
        return jsonify({"question": question, "answer": f"Sorry, something went wrong: {str(e)}"}), 500

app.register_blueprint(langchain_bp)          # before the if __name__ block

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"\n  NewsAlpha API")
    print(f"  Database: {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}")
    print(f"  XLRE excluded from all results")
    print(f"  Endpoints:")
    print(f"    GET  /api/health")
    print(f"    GET  /api/sectors")
    print(f"    GET  /api/timeseries?sector=XLK")
    print(f"    GET  /api/analysis?news_sector=XLK&market_sector=XLK&source=all")
    print(f"    GET  /api/correlations/same-sector")
    print(f"    GET  /api/correlations/cross-sector")
    print(f"    GET  /api/accuracy/same-day")
    print(f"    GET  /api/accuracy/next-day")
    print(f"    GET  /api/accuracy/by-source")
    print(f"    GET  /api/volatility")
    print(f"    GET  /api/stats/overview")
    print(f"    GET  /api/stats/sector/XLK")
    print(f"    GET  /api/filters")
    print(f"    POST /api/chat  <- chatbot")
    print()

    app.run(debug=True, host="0.0.0.0", port=5000)