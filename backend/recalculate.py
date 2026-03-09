"""
Run this in your backend/ folder:
    python recalculate.py

Prints updated tables for the Part 2 report with XLRE removed.
Copy-paste these into your report.
"""

import sqlite3

conn = sqlite3.connect("cs179g_project.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()

EX = "XLRE"

print("=" * 70)
print("UPDATED REPORT TABLES — XLRE EXCLUDED")
print("=" * 70)

# ── Dataset overview ──
print("\n--- Dataset Row Counts ---\n")

tables = [
    "joined_sentiment_market",
    "sector_correlations",
    "cross_sector_correlations",
    "prediction_accuracy",
    "next_day_accuracy",
    "next_day_correlations",
    "source_accuracy",
]

for t in tables:
    c.execute(f"SELECT COUNT(*) FROM {t}")
    total = c.fetchone()[0]

    try:
        if t == "cross_sector_correlations":
            c.execute(f"SELECT COUNT(*) FROM {t} WHERE sent_sector = ? OR mkt_sector = ?", [EX, EX])
        elif t == "source_accuracy":
            xlre_count = 0
            print(f"  {t:<35} {total:>6} total rows  |  no XLRE column  |  {total:>6} rows used")
            continue
        else:
            c.execute(f"SELECT COUNT(*) FROM {t} WHERE sector = ?", [EX])
        xlre_count = c.fetchone()[0]
        remaining = total - xlre_count
        print(f"  {t:<35} {total:>6} total rows  |  {xlre_count:>4} XLRE rows removed  |  {remaining:>6} rows used")
    except Exception:
        print(f"  {t:<35} {total:>6} total rows")

# Total articles in joined data
c.execute("SELECT SUM(article_count) FROM joined_sentiment_market")
total_articles = c.fetchone()[0]
c.execute("SELECT SUM(article_count) FROM joined_sentiment_market WHERE sector != ?", [EX])
articles_no_xlre = c.fetchone()[0]
c.execute("SELECT SUM(article_count) FROM joined_sentiment_market WHERE sector = ?", [EX])
xlre_articles = c.fetchone()[0]

print(f"\n  Total articles (via article_count sum):  {int(total_articles):>10,}")
print(f"  XLRE articles removed:                   {int(xlre_articles):>10,}")
print(f"  Articles used (excl. XLRE):              {int(articles_no_xlre):>10,}")

c.execute("SELECT COUNT(DISTINCT sector) FROM joined_sentiment_market WHERE sector != ?", [EX])
num_sectors = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM joined_sentiment_market WHERE sector != ?", [EX])
joined_rows = c.fetchone()[0]

print(f"\n  Sectors analyzed:                        {num_sectors:>10}")
print(f"  Matched trading day records (excl XLRE): {joined_rows:>10,}")


# ── 4.1 Same-Sector Correlation ──
print("\n\n--- Section 4.1: Same-Sector Correlation (Sentiment vs. Return) ---\n")
c.execute("SELECT * FROM sector_correlations WHERE sector != ? ORDER BY correlation DESC", [EX])
rows = [dict(r) for r in c.fetchall()]
print(f"{'Sector':<10} {'Correlation':>12} {'Mean Sentiment':>16} {'Mean Return':>13} {'Days':>6}")
for r in rows:
    print(f"{r['sector']:<10} {r['correlation']:>12.4f} {r['mean_sentiment']:>16.4f} {r['mean_return']:>13.4f} {r['days']:>6}")

# Calculate overall correlation in Python
c.execute("SELECT avg_sentiment, daily_return_pct FROM joined_sentiment_market WHERE sector != ?", [EX])
data = c.fetchall()
sents = [r[0] for r in data]
rets = [r[1] for r in data]
n = len(sents)
mean_s = sum(sents) / n
mean_r = sum(rets) / n
num = sum((s - mean_s) * (r - mean_r) for s, r in zip(sents, rets))
den_s = sum((s - mean_s) ** 2 for s in sents) ** 0.5
den_r = sum((r - mean_r) ** 2 for r in rets) ** 0.5
overall_corr = num / (den_s * den_r) if den_s * den_r != 0 else 0
print(f"\nOverall sentiment-return correlation (excl. XLRE): {overall_corr:.4f}")


# ── 4.2 Same-Day Prediction Accuracy ──
print("\n\n--- Section 4.2: Same-Day Prediction Accuracy ---\n")
c.execute("SELECT * FROM prediction_accuracy WHERE sector != ? ORDER BY accuracy DESC", [EX])
rows = [dict(r) for r in c.fetchall()]
print(f"{'Sector':<10} {'Accuracy':>10} {'Trading Days':>14}")
for r in rows:
    print(f"{r['sector']:<10} {r['accuracy']*100:>9.1f}% {r['num_days']:>14}")

c.execute("""
    SELECT SUM(accuracy * num_days) / SUM(num_days) as acc, SUM(num_days) as total
    FROM prediction_accuracy WHERE sector != ?
""", [EX])
oa = dict(c.fetchone())
print(f"\nOverall prediction accuracy (excl. XLRE): {oa['acc']*100:.1f}% ({int(oa['total'])} trading days)")


# ── 4.3 Next-Day Prediction ──
print("\n\n--- Section 4.3: Next-Day Prediction Accuracy ---\n")
c.execute("""
    SELECT p.sector, p.accuracy as same_day, n.next_day_accuracy as next_day,
           (n.next_day_accuracy - p.accuracy) as change, n.days
    FROM prediction_accuracy p
    JOIN next_day_accuracy n ON p.sector = n.sector
    WHERE p.sector != ?
    ORDER BY p.accuracy DESC
""", [EX])
rows = [dict(r) for r in c.fetchall()]
print(f"{'Sector':<10} {'Same-Day':>10} {'Next-Day':>10} {'Change':>10} {'Days':>6}")
for r in rows:
    change_str = f"{'+' if r['change']>0 else ''}{r['change']*100:.1f}%"
    print(f"{r['sector']:<10} {r['same_day']*100:>9.1f}% {r['next_day']*100:>9.1f}% {change_str:>10} {r['days']:>6}")

c.execute("""
    SELECT SUM(next_day_accuracy * days) / SUM(days) as acc
    FROM next_day_accuracy WHERE sector != ?
""", [EX])
next_overall = c.fetchone()[0]
print(f"\nOverall next-day accuracy (excl. XLRE): {next_overall*100:.1f}%")


# ── 4.1b Cross-Sector Correlations (top 20, no XLRE) ──
print("\n\n--- Section 4.1b: Cross-Sector Sentiment-to-Return Correlations ---\n")
c.execute("""
    SELECT * FROM cross_sector_correlations
    WHERE sent_sector != ? AND mkt_sector != ?
    ORDER BY ABS(correlation) DESC LIMIT 20
""", [EX, EX])
rows = [dict(r) for r in c.fetchall()]
print(f"{'Sent Sector':<14} {'Mkt Sector':<14} {'Correlation':>12} {'Days':>6}")
for r in rows:
    print(f"{r['sent_sector']:<14} {r['mkt_sector']:<14} {r['correlation']:>12.4f} {r['days']:>6}")


# ── 4.4 Cross-Sector Sentiment Correlation ──
print("\n\n--- Section 4.4: Cross-Sector Sentiment Correlation (sentiment-to-sentiment) ---")
print("(This comes from the Spark pipeline, not a separate table.)")
print("Remove any rows involving XLRE from the existing table.\n")


# ── 4.5 Source Accuracy (unchanged) ──
print("\n--- Section 4.5: Prediction Accuracy by News Source (unchanged) ---\n")
c.execute("SELECT * FROM source_accuracy ORDER BY accuracy DESC")
rows = [dict(r) for r in c.fetchall()]
print(f"{'Source':<25} {'Accuracy':>10} {'Days':>6} {'Mean Sent.':>12}")
for r in rows:
    print(f"{r['source_name']:<25} {r['accuracy']*100:>9.1f}% {r['num_days']:>6} {r['mean_sentiment']:>12.3f}")


# ── Final summary ──
print("\n\n" + "=" * 70)
print("SUMMARY — Numbers to update in your report")
print("=" * 70)
print(f"""
  OLD: 12 sector ETFs          NEW: {num_sectors} sector ETFs
  OLD: 10,080 matched days     NEW: {joined_rows:,} matched days
  OLD: Overall accuracy 51.7%  NEW: Overall accuracy {oa['acc']*100:.1f}%
  OLD: Overall corr 0.0143     NEW: Overall corr {overall_corr:.4f}
  OLD: Next-day acc 51.1%      NEW: Next-day acc {next_overall*100:.1f}%

  Find-replace in report:
    "12 sectors"     -> "11 sectors"
    "12 sector ETFs" -> "11 sector ETFs"
    "10,080"         -> "{joined_rows:,}"
    Remove all XLRE footnotes and caveats.
""")

conn.close()