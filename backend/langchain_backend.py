"""
LangChain AI Analyst — Flask Blueprint
---------------------------------------
Adds /api/ask and /api/execute_sql endpoints to app.py.
Uses your existing MySQL database (same connection as the rest of the app).

SETUP:
    pip install langchain langchain-community langchain-google-genai

API KEY (free):
    1. Go to https://aistudio.google.com/apikey
    2. Click "Create API Key"
    3. Set env var:  export GOOGLE_API_KEY="AIzaSy..."
"""

import os
import json
import pymysql
from flask import Blueprint, request, jsonify, g
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ─── BLUEPRINT ────────────────────────────────────────────────────────

langchain_bp = Blueprint("langchain", __name__)

# ─── LLM SETUP ───────────────────────────────────────────────────────

llm = None


def get_llm():
    global llm
    if llm is None:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GOOGLE_API_KEY not set. Get a free key at https://aistudio.google.com/apikey"
            )
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0,
        )
    return llm


# ─── SCHEMA DESCRIPTION ──────────────────────────────────────────────
# This tells the LLM exactly what tables/columns exist so it can
# generate accurate SQL.  Matches your MySQL database.

SCHEMA = """
Tables (MySQL database):

1. joined_sentiment_market (10,080 rows)
   Core dataset — one row per trading day per sector.
   Columns: date (TEXT, format varies), sector (TEXT, ETF ticker like XLK/XLF/ITA),
   avg_sentiment (REAL, VADER score -1 to 1), article_count (INTEGER),
   sentiment_std (REAL), open (REAL), close (REAL),
   daily_return_pct (REAL, percent), market_direction (TEXT, 'green'/'red'),
   volume (INTEGER).
   NOTE: Exclude sector='XLRE' from all queries (insufficient data, only 37 days).

2. sector_correlations (12 rows, use 11 excluding XLRE)
   Same-sector Pearson correlation between sentiment and return.
   Columns: sector (TEXT), correlation (REAL), mean_sentiment (REAL),
   mean_return (REAL), days (INTEGER).

3. prediction_accuracy (12 rows, use 11 excluding XLRE)
   Same-day binary prediction accuracy per sector.
   Columns: sector (TEXT), accuracy (REAL, 0-1 scale), num_days (INTEGER).

4. next_day_accuracy (12 rows, use 11 excluding XLRE)
   Next-day (lagged) prediction accuracy.
   Columns: sector (TEXT), next_day_accuracy (REAL, 0-1 scale), days (INTEGER).

5. next_day_correlations (12 rows)
   Next-day Pearson correlations.
   Columns: sector (TEXT), next_day_corr (REAL).

6. cross_sector_correlations (132 rows)
   Sentiment from one sector vs. returns of another.
   Columns: sent_sector (TEXT), mkt_sector (TEXT), correlation (REAL), days (INTEGER).

7. source_accuracy (11 rows)
   Prediction accuracy per news outlet.
   Columns: source_name (TEXT), accuracy (REAL, 0-1 scale),
   num_days (INTEGER), mean_sentiment (REAL).

8. volatility_correlations (12 rows)
   Sentiment-volatility correlation per sector.
   Columns: sector (TEXT), correlation (REAL), mean_abs_return (REAL), days (INTEGER).

IMPORTANT RULES:
- Always exclude XLRE: add WHERE sector != 'XLRE' (or sent_sector/mkt_sector != 'XLRE')
- accuracy values are 0-1 decimals (multiply by 100 for percentages)
- Use standard SQL (MySQL compatible). Do NOT use SQLite-specific syntax.
- Only generate SELECT queries.
"""


# ─── DATABASE HELPER ──────────────────────────────────────────────────


def _query(sql, args=()):
    """Run a SELECT query using the app's existing MySQL connection."""
    # Import the get_db and MYSQL_CONFIG from the parent app at runtime
    from app import get_db

    conn = get_db()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute(sql, args)
    rows = cur.fetchall()
    cur.close()
    return rows


# ─── ENDPOINT 1: Generate SQL ─────────────────────────────────────────


@langchain_bp.route("/api/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json()
        question = data.get("question", "").strip()
        if not question:
            return jsonify({"error": "question is required"}), 400

        model = get_llm()

        prompt = PromptTemplate.from_template(
            """You are an expert SQL generator for a MySQL database. Given this schema:
{schema}

Write a valid MySQL SELECT query that answers the user's question.

CHARTING HINT: If the question implies aggregation (averages, sums, counts),
include BOTH the grouping column AND the numeric result in SELECT
(e.g. SELECT sector, AVG(accuracy) ... GROUP BY sector).

If they ask for a correlation, fetch the relevant columns so the frontend can chart it.

Output ONLY the raw SQL query. No markdown, no backticks, no explanation.

Question: {question}
SQL Query:"""
        )

        chain = prompt | model | StrOutputParser()

        sql = chain.invoke({"schema": SCHEMA, "question": question})

        # Clean up any markdown the LLM might have added
        sql = sql.strip()
        if sql.startswith("```"):
            sql = sql.split("\n", 1)[-1]
            sql = sql.rsplit("```", 1)[0]
        sql = sql.strip().rstrip(";")

        # Safety: only SELECT queries
        if not sql.upper().lstrip().startswith("SELECT"):
            return (
                jsonify(
                    {
                        "error": "Generated query was not a SELECT statement for safety.",
                        "generated_sql": sql,
                    }
                ),
                403,
            )

        return jsonify({"sql": sql})

    except Exception as e:
        print(f"[LangChain] SQL generation error: {e}")
        return (
            jsonify(
                {"error": "Failed to generate SQL", "details": str(e)}
            ),
            500,
        )


# ─── ENDPOINT 2: Execute SQL + Format Answer ──────────────────────────


@langchain_bp.route("/api/execute_sql", methods=["POST"])
def execute_sql():
    try:
        data = request.get_json()
        sql = data.get("sql", "").strip()
        question = data.get("question", "").strip()

        if not sql or not question:
            return jsonify({"error": "sql and question are required"}), 400

        # Safety check
        if not sql.upper().lstrip().startswith("SELECT"):
            return jsonify({"error": "Only SELECT queries are allowed"}), 403

        # Execute
        try:
            raw_result = _query(sql)
        except Exception as db_err:
            return (
                jsonify({"error": "SQL Execution Error", "details": str(db_err)}),
                400,
            )

        # Use LLM to format the answer + suggest chart type
        model = get_llm()

        format_prompt = PromptTemplate.from_template(
            """Given the user's original question: "{question}"
And the SQL query executed: "{sql}"
And the JSON result from the database: "{result}"

Provide a concise, natural language answer based STRICTLY on the result.
Do not mention the SQL query. Just answer directly.
If the result is empty, say no results were found.

OUTPUT FORMAT:
Return a valid JSON object matching this schema exactly.
No markdown, no backticks — raw JSON only.
{{
  "answer": "Concise natural language answer here...",
  "chartConfig": {{
     "type": "bar" | "line" | "pie" | "scatter" | "none",
     "xAxisKey": "column name for x-axis (label/category/date), empty if none",
     "yAxisKey": "column name for y-axis (numeric value), empty if none"
  }}
}}

If the data is a single number or cannot be charted, set type to "none".
For correlation data, use "scatter". For time series, use "line".
For comparisons across categories, use "bar"."""
        )

        format_chain = format_prompt | model | StrOutputParser()

        llm_response = format_chain.invoke(
            {
                "question": question,
                "sql": sql,
                "result": json.dumps(raw_result, default=str),
            }
        )

        # Clean up markdown
        llm_response = llm_response.strip()
        if llm_response.startswith("```"):
            llm_response = llm_response.split("\n", 1)[-1]
            llm_response = llm_response.rsplit("```", 1)[0]
        llm_response = llm_response.strip()

        try:
            parsed = json.loads(llm_response)
        except json.JSONDecodeError:
            parsed = {"answer": llm_response, "chartConfig": {"type": "none"}}

        # Convert any Decimal types to float for JSON serialization
        clean_result = []
        for row in raw_result:
            clean_row = {}
            for k, v in row.items():
                if hasattr(v, "__float__"):
                    clean_row[k] = float(v)
                else:
                    clean_row[k] = v
            clean_result.append(clean_row)

        return jsonify(
            {
                "rawResult": clean_result,
                "formattedAnswer": parsed.get("answer", llm_response),
                "chartConfig": parsed.get("chartConfig", {"type": "none"}),
            }
        )

    except Exception as e:
        print(f"[LangChain] Execution error: {e}")
        return (
            jsonify({"error": "Error formatting answer", "details": str(e)}),
            500,
        )
