"""
LangChain SQL Agent for CS 179G Part 3
--------------------------------------
Adds the /api/ask endpoint to your Flask backend.
Uses your existing SQLite database (cs179g_project.db).

SETUP:
    pip install langchain langchain-community langchain-google-genai

API KEY (free):
    1. Go to https://aistudio.google.com/apikey
    2. Click "Create API Key"
    3. export GOOGLE_API_KEY="AIzaSy..."
"""

import os
from flask import Blueprint, request, jsonify
from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain

# ─── LLM SETUP ───────────────────────────────────────────────────────

# Google Gemini (FREE tier)
from langchain_google_genai import ChatGoogleGenerativeAI
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)

# Alternative: OpenAI (uncomment below, comment out Gemini above)
# pip install langchain-openai
# export OPENAI_API_KEY="sk-..."
# from langchain_openai import ChatOpenAI
# llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# ─── DATABASE CONNECTION (SQLite) ────────────────────────────────────

# Sits right next to app.py in your backend/ folder
DB_PATH = os.path.join(os.path.dirname(__file__), "cs179g_project.db")

db = SQLDatabase.from_uri(
    f"sqlite:///{DB_PATH}",
    include_tables=[
        "joined_sentiment_market",
        "sector_correlations",
        "cross_sector_correlations",
        "prediction_accuracy",
        "next_day_accuracy",
        "next_day_correlations",
        "source_accuracy",
    ],
    custom_table_info={
        "joined_sentiment_market": "Core dataset with 10,080 rows. Each row is one trading day for one sector. Columns: date, sector (ETF ticker like XLK, XLF, ITA), avg_sentiment (VADER score -1 to 1), article_count, market_direction (green/red), daily_return_pct.",
        "sector_correlations": "12 rows, one per sector. Columns: sector, correlation (Pearson r between sentiment and return), mean_sentiment, mean_return, days (number of matched trading days).",
        "cross_sector_correlations": "144 rows (12x12 sector pairs). Columns: sent_sector (sentiment source), mkt_sector (market return), correlation, days.",
        "prediction_accuracy": "12 rows. Same-day binary prediction accuracy per sector. Columns: sector, accuracy, days.",
        "next_day_accuracy": "12 rows. Next-day (lagged) prediction accuracy. Columns: sector, same_day_accuracy, next_day_accuracy, change, days.",
        "next_day_correlations": "12 rows. Next-day Pearson correlations. Columns: sector, correlation, days.",
        "source_accuracy": "11 rows. Prediction accuracy per news outlet. Columns: source_name, accuracy, days, mean_sentiment.",
    },
)

# ─── CREATE THE CHAIN ────────────────────────────────────────────────

chain = create_sql_query_chain(llm, db)

# ─── FLASK BLUEPRINT ─────────────────────────────────────────────────

langchain_bp = Blueprint("langchain", __name__)


@langchain_bp.route("/api/ask", methods=["POST"])
def ask():
    question = ""
    generated_sql = ""
    try:
        question = request.json.get("question", "")
        if not question:
            return jsonify({"error": "No question provided"}), 400

        # Step 1: LLM generates SQL from the question
        generated_sql = chain.invoke({"question": question})

        # Clean up markdown backticks the LLM sometimes adds
        sql_clean = generated_sql.strip()
        if sql_clean.startswith("```"):
            sql_clean = sql_clean.split("\n", 1)[-1]
            sql_clean = sql_clean.rsplit("```", 1)[0]
        sql_clean = sql_clean.strip()

        # Safety: only allow SELECT queries
        if not sql_clean.upper().startswith("SELECT"):
            return jsonify({
                "question": question,
                "sql": sql_clean,
                "answer": "I can only run SELECT queries for safety.",
                "error": "non-select-query",
            })

        # Step 2: Execute the SQL against SQLite
        result = db.run(sql_clean)

        # Step 3: Use LLM to format a human-readable answer
        format_prompt = f"""Given this question: "{question}"
The SQL query returned: {result}
Write a clear, concise answer in 1-3 sentences. Include specific numbers."""

        formatted = llm.invoke(format_prompt)
        answer_text = formatted.content if hasattr(formatted, "content") else str(formatted)

        return jsonify({
            "question": question,
            "sql": sql_clean,
            "answer": answer_text,
            "raw_result": str(result),
            "error": None,
        })

    except Exception as e:
        return jsonify({
            "question": question,
            "sql": generated_sql if generated_sql else None,
            "answer": "Sorry, I couldn't process that question.",
            "error": str(e),
        }), 500


# ─── STANDALONE TEST ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing LangChain + SQLite connection...")
    print(f"Database: {DB_PATH}")
    print(f"Tables found: {db.get_usable_table_names()}")

    test_q = "Which sector has the highest prediction accuracy?"
    print(f"\nQuestion: {test_q}")
    sql = chain.invoke({"question": test_q})
    print(f"Generated SQL: {sql}")
    result = db.run(sql)
    print(f"Result: {result}")
