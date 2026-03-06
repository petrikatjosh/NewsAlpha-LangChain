import { useState, useMemo, useRef } from "react";
import { Link } from "react-router-dom";
import "./AnalysisPage.css";

/*
 *  AnalysisPage.tsx
 *  ─────────────────────────────────────────────
 *  Senior Design – Sentiment × Market Analysis Dashboard
 *
 *  All data below is MOCK. The component exposes a clean data
 *  contract so the backend can be swapped in later:
 *
 *    type AnalysisResult = {
 *      dailyData:   { date: string; sentiment: number; returnPct: number }[];
 *      correlation: number;
 *      accuracy:    number;
 *      tradingDays: number;
 *      meanSentiment: number;
 *      meanReturn:    number;
 *      articles:      number;
 *    };
 *
 *  Replace the `useMockData` hook with a real fetch when ready.
 */

/* ════════════════════ STATIC OPTION LISTS ════════════════════ */

const NEWS_SOURCES = [
  { value: "all",              label: "All Sources" },
  { value: "guardian",         label: "The Guardian" },
  { value: "cnn_dailymail",   label: "CNN-DailyMail" },
  { value: "ibt",             label: "Intl Business Times" },
  { value: "globenewswire",   label: "GlobeNewswire" },
  { value: "times_of_india",  label: "Times of India" },
  { value: "bbc",             label: "BBC News" },
  { value: "npr",             label: "NPR" },
  { value: "boing_boing",     label: "Boing Boing" },
  { value: "business_insider", label: "Business Insider" },
  { value: "globalsecurity",  label: "Globalsecurity.org" },
  { value: "abc",             label: "ABC News" },
];

const NEWS_SECTORS = [
  { value: "ITA",  label: "Aerospace & Defense" },
  { value: "XLF",  label: "Financials" },
  { value: "XLC",  label: "Communication Svcs" },
  { value: "PEJ",  label: "Leisure & Entertainment" },
  { value: "XLY",  label: "Consumer Discretionary" },
  { value: "XLI",  label: "Industrials" },
  { value: "XLK",  label: "Technology" },
  { value: "XLE",  label: "Energy" },
  { value: "XLV",  label: "Health Care" },
  { value: "XLP",  label: "Consumer Staples" },
  { value: "XLRE", label: "Real Estate" },
  { value: "XHB",  label: "Homebuilders" },
];

const MARKET_SECTORS = [...NEWS_SECTORS]; // same ETFs for market side

/* ════════════════════ SECTOR COLOURS ════════════════════ */

const SECTOR_COLORS: Record<string, string> = {
  ITA:  "#ef4444",
  XLF:  "#f59e0b",
  XLC:  "#06b6d4",
  PEJ:  "#ec4899",
  XLY:  "#06b6d4",
  XLI:  "#8b5cf6",
  XLK:  "#3b82f6",
  XLE:  "#f97316",
  XLV:  "#22c55e",
  XLP:  "#14b8a6",
  XLRE: "#a855f7",
  XHB:  "#ec4899",
};

/* ════════════════════ MOCK DATA GENERATOR ════════════════════ */

/*  Deterministic pseudo-random from a string seed so that the
    same dropdown combination always produces the same chart.    */
function seededRandom(seed: string) {
  let h = 0;
  for (let i = 0; i < seed.length; i++) {
    h = (Math.imul(31, h) + seed.charCodeAt(i)) | 0;
  }
  return () => {
    h ^= h << 13; h ^= h >> 17; h ^= h << 5;
    return ((h >>> 0) / 4294967296);
  };
}

interface DailyDatum {
  date: string;
  sentiment: number;
  returnPct: number;
}

interface PriceDatum {
  date: string;
  price: number;
  sentiment: number | null;   // null = no sentiment data for this day
  returnPct: number;          // daily return %
  predicted: boolean | null;  // true = sentiment correctly predicted direction, null = no sentiment
}

interface AnalysisResult {
  dailyData: DailyDatum[];
  priceSeries: PriceDatum[];
  correlation: number;
  accuracy: number;
  tradingDays: number;
  meanSentiment: number;
  meanReturn: number;
  articles: number;
}

function generateMockData(source: string, newsSector: string, mktSector: string): AnalysisResult {
  const seed = `${source}-${newsSector}-${mktSector}`;
  const rand = seededRandom(seed);

  const months = [
    "Jan '19","Apr '19","Jul '19","Oct '19",
    "Jan '20","Apr '20","Jul '20","Oct '20",
    "Jan '21","Apr '21","Jul '21","Oct '21",
    "Jan '22","Apr '22","Jul '22","Oct '22",
    "Jan '23","Apr '23","Jul '23","Oct '23",
    "Jan '24","Apr '24","Jul '24","Oct '24",
  ];

  const dailyData: DailyDatum[] = months.map((m) => ({
    date: m,
    sentiment: (rand() * 2 - 1) * 0.6 + 0.1,
    returnPct: (rand() * 2 - 1) * 2.5,
  }));

  /* price series — more granular, monthly from 2012–2024.
     Some months have matching sentiment data, others don't. */
  const priceMonths: string[] = [];
  for (let y = 2012; y <= 2024; y++) {
    for (const m of ["Jan", "Mar", "May", "Jul", "Sep", "Nov"]) {
      priceMonths.push(`${m} '${String(y).slice(2)}`);
    }
  }

  let price = 30 + rand() * 40; // starting price
  const priceSeries: PriceDatum[] = priceMonths.map((date) => {
    const returnPct = (rand() - 0.47) * 8;
    price = price * (1 + returnPct / 100);
    price = Math.max(price, 5);

    // ~40% of price points have sentiment coverage
    const hasSentiment = rand() > 0.6;
    const sentiment = hasSentiment ? (rand() * 2 - 1) * 0.7 : null;

    // prediction correct if sentiment sign matches return sign
    const predicted = sentiment !== null
      ? (sentiment >= 0 && returnPct >= 0) || (sentiment < 0 && returnPct < 0)
      : null;

    return { date, price: +price.toFixed(2), sentiment, returnPct: +returnPct.toFixed(2), predicted };
  });

  const correlation = +(rand() * 0.24 - 0.04).toFixed(4);
  const accuracy = +(48 + rand() * 10).toFixed(1);
  const tradingDays = Math.round(200 + rand() * 1400);
  const meanSentiment = +(rand() * 1.2 - 0.4).toFixed(3);
  const meanReturn = +((rand() - 0.45) * 0.12).toFixed(4);
  const articles = Math.round(800 + rand() * 60000);

  return { dailyData, priceSeries, correlation, accuracy, tradingDays, meanSentiment, meanReturn, articles };
}

/* ════════════════════ TINY COMPONENTS ════════════════════ */

function StatCard({
  label, value, detail, colorClass, delay,
}: {
  label: string; value: string; detail: string; colorClass: string; delay: string;
}) {
  return (
    <div className={`ap-stat-card ap-fade-in ${delay}`}>
      <div className="ap-stat-card__label">{label}</div>
      <div className={`ap-stat-card__value ${colorClass}`}>{value}</div>
      <div className="ap-stat-card__detail">{detail}</div>
    </div>
  );
}

/* ════════════════════ TOOLTIP POSITIONING HELPER ════════════════════ */

const TOOLTIP_W = 170; // approximate tooltip width in px

function tooltipStyle(x: number, y: number, containerW: number) {
  const overflowsRight = x + TOOLTIP_W + 12 > containerW;
  return {
    top: Math.max(y, 0),
    ...(overflowsRight
      ? { right: containerW - x + 8, left: "auto" as const }
      : { left: x + 8 }),
  };
}

/* ════════════════════ PRICE + PREDICTION OVERLAY + SENTIMENT SUB-CHART ════════════════════ */

function PriceChart({
  data,
}: {
  data: PriceDatum[];
}) {
  const chartRef = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip] = useState<{
    x: number; y: number; datum: PriceDatum;
  } | null>(null);

  const prices = data.map((d) => d.price);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const priceRange = maxPrice - minPrice || 1;

  const sentPoints = data.filter((d) => d.sentiment !== null);
  const maxReturn = Math.max(...sentPoints.map((d) => Math.abs(d.returnPct)), 0.01);

  /* ── price chart geometry ── */
  const priceH = 260;
  const padLeft = 54;
  const padRight = 10;
  const padTop = 12;
  const padBottom = 8;
  const plotH = priceH - padTop - padBottom;

  /* ── sentiment sub-chart geometry ── */
  const sentH = 80;
  const sentPadTop = 4;
  const sentPadBottom = 4;
  const sentPlotH = sentH - sentPadTop - sentPadBottom;

  /* build SVG polyline for price */
  const pointCoords = data.map((d, i) => {
    const x = (i / (data.length - 1)) * 100;
    const y = padTop + (1 - (d.price - minPrice) / priceRange) * plotH;
    return { x, y };
  });
  const polyline = pointCoords.map((p) => `${p.x},${p.y}`).join(" ");
  const areaPoints = [
    `0,${padTop + plotH}`,
    ...pointCoords.map((p) => `${p.x},${p.y}`),
    `100,${padTop + plotH}`,
  ].join(" ");

  /* y-axis labels */
  const yTicks = Array.from({ length: 5 }, (_, i) => {
    const val = minPrice + (priceRange * (4 - i)) / 4;
    return { label: `$${val.toFixed(0)}`, top: padTop + (i / 4) * plotH };
  });

  const step = Math.ceil(data.length / 8);

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1 }}>
      {/* ═══ PRICE CHART ═══ */}
      <div
        ref={chartRef}
        className="ap-chart-body"
        style={{ minHeight: priceH, position: "relative" }}
      >
        {/* grid lines */}
        <div className="ap-chart-grid">
          {yTicks.map((_, i) => (
            <div key={i} className="ap-chart-grid__line" />
          ))}
        </div>

        {/* y-axis labels */}
        <div style={{ position: "absolute", top: 0, bottom: 0, left: 0, width: padLeft, pointerEvents: "none" }}>
          {yTicks.map((t, i) => (
            <span
              key={i}
              className="ap-chart-y-label"
              style={{ position: "absolute", top: t.top, right: 8, transform: "translateY(-50%)" }}
            >
              {t.label}
            </span>
          ))}
        </div>

        {/* prediction bars — colour = correct/incorrect, height = return magnitude */}
        <div
          style={{
            position: "absolute",
            left: padLeft,
            right: padRight,
            top: padTop,
            bottom: padBottom,
            pointerEvents: "none",
          }}
        >
          {data.map((d, i) => {
            if (d.sentiment === null) return null;
            const barH = (Math.abs(d.returnPct) / maxReturn) * plotH * 0.85;
            const correct = d.predicted === true;
            return (
              <div
                key={i}
                style={{
                  position: "absolute",
                  left: `${(i / data.length) * 100}%`,
                  width: `${Math.max((1 / data.length) * 100, 0.8)}%`,
                  bottom: 0,
                  height: barH,
                  background: correct
                    ? "rgba(34, 197, 94, 0.16)"
                    : "rgba(239, 68, 68, 0.16)",
                  borderTop: `2px solid ${correct ? "var(--green)" : "var(--red)"}`,
                  borderRadius: "2px 2px 0 0",
                  pointerEvents: "auto",
                  cursor: "pointer",
                }}
                onMouseEnter={(e) => {
                  const rect = e.currentTarget.parentElement!.parentElement!.getBoundingClientRect();
                  setTooltip({ x: e.clientX - rect.left, y: e.clientY - rect.top - 90, datum: d });
                }}
                onMouseLeave={() => setTooltip(null)}
              />
            );
          })}
        </div>

        {/* SVG line + area */}
        <svg
          viewBox={`0 0 100 ${priceH}`}
          preserveAspectRatio="none"
          style={{
            position: "absolute",
            left: padLeft,
            right: padRight,
            top: 0,
            bottom: 0,
            width: `calc(100% - ${padLeft + padRight}px)`,
            height: "100%",
            pointerEvents: "none",
          }}
        >
          <defs>
            <linearGradient id="priceAreaGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.15" />
              <stop offset="100%" stopColor="var(--accent)" stopOpacity="0.01" />
            </linearGradient>
          </defs>
          <polygon points={areaPoints} fill="url(#priceAreaGrad)" />
          <polyline
            points={polyline}
            fill="none"
            stroke="var(--accent)"
            strokeWidth="0.5"
            vectorEffect="non-scaling-stroke"
            style={{ filter: "drop-shadow(0 0 3px rgba(59,130,246,0.4))" }}
          />
        </svg>

        {/* invisible hover zones */}
        <div
          style={{
            position: "absolute",
            left: padLeft,
            right: padRight,
            top: 0,
            bottom: 0,
            display: "flex",
          }}
        >
          {data.map((d, i) => (
            <div
              key={i}
              style={{ flex: 1, cursor: "crosshair" }}
              onMouseEnter={(e) => {
                const rect = e.currentTarget.parentElement!.parentElement!.getBoundingClientRect();
                setTooltip({ x: e.clientX - rect.left, y: e.clientY - rect.top - 90, datum: d });
              }}
              onMouseLeave={() => setTooltip(null)}
            />
          ))}
        </div>

        {/* tooltip */}
        {tooltip && (
          <div
            className="ap-chart-tooltip ap-chart-tooltip--visible"
            style={tooltipStyle(tooltip.x, Math.max(tooltip.y, 0), chartRef.current?.offsetWidth ?? 999)}
          >
            <div className="ap-chart-tooltip__title">{tooltip.datum.date}</div>
            <div className="ap-chart-tooltip__row">
              <span className="ap-chart-tooltip__label">Price</span>
              <span className="ap-chart-tooltip__value">${tooltip.datum.price.toFixed(2)}</span>
            </div>
            <div className="ap-chart-tooltip__row">
              <span className="ap-chart-tooltip__label">Return</span>
              <span
                className="ap-chart-tooltip__value"
                style={{ color: tooltip.datum.returnPct >= 0 ? "var(--green)" : "var(--red)" }}
              >
                {tooltip.datum.returnPct >= 0 ? "+" : ""}{tooltip.datum.returnPct.toFixed(2)}%
              </span>
            </div>
            {tooltip.datum.sentiment !== null && (
              <>
                <div className="ap-chart-tooltip__row">
                  <span className="ap-chart-tooltip__label">Sentiment</span>
                  <span
                    className="ap-chart-tooltip__value"
                    style={{ color: tooltip.datum.sentiment >= 0 ? "var(--green)" : "var(--red)" }}
                  >
                    {tooltip.datum.sentiment >= 0 ? "+" : ""}
                    {tooltip.datum.sentiment.toFixed(3)}
                  </span>
                </div>
                <div className="ap-chart-tooltip__row">
                  <span className="ap-chart-tooltip__label">Prediction</span>
                  <span
                    className="ap-chart-tooltip__value"
                    style={{ color: tooltip.datum.predicted ? "var(--green)" : "var(--red)" }}
                  >
                    {tooltip.datum.predicted ? "✓ Correct" : "✗ Incorrect"}
                  </span>
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* ═══ SENTIMENT SUB-CHART (RSI-style) ═══ */}
      <div className="ap-sent-sub">
        <div className="ap-sent-sub__label-area" style={{ width: padLeft }}>
          <span className="ap-chart-y-label" style={{ position: "absolute", top: sentPadTop, right: 8 }}>+1</span>
          <span className="ap-chart-y-label" style={{ position: "absolute", top: sentPadTop + sentPlotH / 2, right: 8 }}>0</span>
          <span className="ap-chart-y-label" style={{ position: "absolute", bottom: sentPadBottom, right: 8 }}>−1</span>
        </div>
        <div className="ap-sent-sub__plot" style={{ left: padLeft, right: padRight }}>
          {/* zero line */}
          <div className="ap-sent-sub__zero" style={{ top: sentPadTop + sentPlotH / 2 }} />
          {/* sentiment bars */}
          {data.map((d, i) => {
            if (d.sentiment === null) return null;
            const sent = d.sentiment;
            const barH = (Math.abs(sent) / 1) * (sentPlotH / 2);
            const isPos = sent >= 0;
            const top = isPos ? sentPadTop + sentPlotH / 2 - barH : sentPadTop + sentPlotH / 2;
            return (
              <div
                key={i}
                style={{
                  position: "absolute",
                  left: `${(i / data.length) * 100}%`,
                  width: `${Math.max((1 / data.length) * 100, 0.8)}%`,
                  top,
                  height: barH,
                  background: isPos ? "var(--green)" : "var(--red)",
                  opacity: 0.6,
                  borderRadius: isPos ? "2px 2px 0 0" : "0 0 2px 2px",
                }}
              />
            );
          })}
        </div>
      </div>

      {/* x-axis */}
      <div className="ap-chart-x-axis" style={{ paddingLeft: padLeft }}>
        {data.map((d, i) =>
          i % step === 0 ? (
            <span key={i} className="ap-chart-x-label">{d.date}</span>
          ) : null
        )}
      </div>
    </div>
  );
}

/* ════════════════════ SINGLE-METRIC BAR CHART ════════════════════ */

function SingleBarChart({
  data,
  dataKey,
  color,
  unit,
  formatValue,
}: {
  data: DailyDatum[];
  dataKey: "sentiment" | "returnPct";
  color: string;
  unit: string;
  formatValue: (v: number) => string;
}) {
  const chartRef = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip] = useState<{
    x: number; y: number; datum: DailyDatum;
  } | null>(null);

  const values = data.map((d) => d[dataKey]);
  const maxAbs = Math.max(...values.map(Math.abs), 0.01);

  const yLabels = [
    `+${dataKey === "sentiment" ? maxAbs.toFixed(2) : maxAbs.toFixed(1) + "%"}`,
    "",
    "0",
    "",
    `−${dataKey === "sentiment" ? maxAbs.toFixed(2) : maxAbs.toFixed(1) + "%"}`,
  ];

  const step = Math.ceil(data.length / 8);

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1 }}>
      <div ref={chartRef} className="ap-chart-body" style={{ minHeight: 180 }}>
        {/* grid lines */}
        <div className="ap-chart-grid">
          {yLabels.map((_, i) => (
            <div key={i} className="ap-chart-grid__line" />
          ))}
        </div>

        {/* y-axis */}
        <div className="ap-chart-y-axis" style={{ width: 44 }}>
          {yLabels.map((l, i) => (
            <span key={i} className="ap-chart-y-label">{l}</span>
          ))}
        </div>

        {/* bars */}
        <div className="ap-chart-bars" style={{ left: 44 }}>
          {data.map((d, i) => {
            const val = d[dataKey];
            const h = (Math.abs(val) / maxAbs) * 45;
            const bottom = val >= 0 ? 50 : 50 - h;

            return (
              <div
                key={i}
                className="ap-chart-bar"
                style={{
                  position: "absolute",
                  left: `${(i / data.length) * 100 + 0.4}%`,
                  width: `${(1 / data.length) * 100 - 1}%`,
                  bottom: `${bottom}%`,
                  height: `${h}%`,
                  background: color,
                  borderRadius: "3px 3px 0 0",
                }}
                onMouseEnter={(e) => {
                  const rect = e.currentTarget.parentElement!.getBoundingClientRect();
                  setTooltip({
                    x: e.clientX - rect.left,
                    y: e.clientY - rect.top - 50,
                    datum: d,
                  });
                }}
                onMouseLeave={() => setTooltip(null)}
              />
            );
          })}
        </div>

        {/* center zero line */}
        <div
          style={{
            position: "absolute",
            left: 44,
            right: 0,
            top: "50%",
            height: 1,
            background: "var(--border-light)",
            pointerEvents: "none",
          }}
        />

        {/* tooltip */}
        {tooltip && (
          <div
            className="ap-chart-tooltip ap-chart-tooltip--visible"
            style={tooltipStyle(tooltip.x, tooltip.y, chartRef.current?.offsetWidth ?? 999)}
          >
            <div className="ap-chart-tooltip__title">{tooltip.datum.date}</div>
            <div className="ap-chart-tooltip__row">
              <span className="ap-chart-tooltip__label">{unit}</span>
              <span className="ap-chart-tooltip__value">
                {formatValue(tooltip.datum[dataKey])}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* x-axis */}
      <div className="ap-chart-x-axis" style={{ paddingLeft: 44 }}>
        {data.map((d, i) =>
          i % step === 0 ? (
            <span key={i} className="ap-chart-x-label">{d.date}</span>
          ) : null
        )}
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════
   MAIN PAGE
   ════════════════════════════════════════════════════════════════ */
export default function AnalysisPage() {
  const [source, setSource] = useState("all");
  const [newsSector, setNewsSector] = useState("XLK");
  const [mktSector, setMktSector] = useState("XLK");

  const data = useMemo(
    () => generateMockData(source, newsSector, mktSector),
    [source, newsSector, mktSector]
  );

  const sentColor = SECTOR_COLORS[newsSector] || "var(--accent)";
  const retColor = SECTOR_COLORS[mktSector] || "var(--cyan)";

  const newsLabel = NEWS_SECTORS.find((s) => s.value === newsSector)?.label ?? newsSector;
  const mktLabel = MARKET_SECTORS.find((s) => s.value === mktSector)?.label ?? mktSector;
  const sourceLabel = NEWS_SOURCES.find((s) => s.value === source)?.label ?? source;

  /* accuracy colour helper */
  const accClass =
    data.accuracy >= 53 ? "ap-color-green" : data.accuracy >= 50 ? "ap-color-text" : "ap-color-red";
  const corrClass =
    data.correlation > 0.05 ? "ap-color-green" : data.correlation < -0.05 ? "ap-color-red" : "ap-color-text";

  return (
    <div className="ap-root">
      {/* ── NAV ── */}
      <nav className="ap-nav">
        <span className="ap-nav__title">NewsAlpha</span>
        <div className="ap-nav__links">
          <Link to="/" className="ap-nav-link">Home</Link>
          <Link to="/analysis" className="ap-nav-link ap-nav-link--active">Analysis</Link>
          <Link to="/paper" className="ap-nav-link">Paper</Link>
          <Link to="/about" className="ap-nav-link">About</Link>
        </div>
      </nav>

      {/* ── PAGE HEADER ── */}
      <div className="ap-header ap-fade-in ap-fade-in--d1">
        <p className="ap-header__label">Interactive Analysis</p>
        <h1 className="ap-header__h1">Sentiment vs. Market Performance</h1>
        <p className="ap-header__subtitle">
          Compare news sentiment from any source and sector against ETF returns.
          Select a combination below to explore the relationship.
        </p>
      </div>

      {/* ── CONTROLS ── */}
      <div className="ap-controls ap-fade-in ap-fade-in--d2">
        <div className="ap-control-group">
          <label className="ap-control-group__label">News Source</label>
          <select
            className="ap-select"
            value={source}
            onChange={(e) => setSource(e.target.value)}
          >
            {NEWS_SOURCES.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>

        <div className="ap-control-group">
          <label className="ap-control-group__label">News Sector (Sentiment)</label>
          <select
            className="ap-select"
            value={newsSector}
            onChange={(e) => setNewsSector(e.target.value)}
          >
            {NEWS_SECTORS.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>

        <div className="ap-controls__arrow">→</div>

        <div className="ap-control-group">
          <label className="ap-control-group__label">Market Sector (ETF Return)</label>
          <select
            className="ap-select"
            value={mktSector}
            onChange={(e) => setMktSector(e.target.value)}
          >
            {MARKET_SECTORS.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* ── MAIN CONTENT ── */}
      <div className="ap-content">
        {/* charts column */}
        <div className="ap-charts-stack">
          {/* price + sentiment overlay chart */}
          <div className="ap-chart-panel ap-fade-in ap-fade-in--d3">
            <div className="ap-chart-panel__header">
              <div>
                <h2 className="ap-chart-panel__title">
                  {mktLabel} ETF Price History
                </h2>
                <p className="ap-chart-panel__desc">
                  {mktSector} price with prediction accuracy overlay · bar height = return magnitude · sentiment indicator below
                </p>
              </div>
              <div className="ap-chart-panel__legend">
                <div className="ap-legend-item">
                  <span className="ap-legend-dot" style={{ background: "var(--accent)" }} />
                  Price
                </div>
                <div className="ap-legend-item">
                  <span className="ap-legend-dot" style={{ background: "var(--green)" }} />
                  Correct
                </div>
                <div className="ap-legend-item">
                  <span className="ap-legend-dot" style={{ background: "var(--red)" }} />
                  Incorrect
                </div>
              </div>
            </div>
            <PriceChart data={data.priceSeries} />
          </div>

          {/* sentiment chart */}
          <div className="ap-chart-panel ap-fade-in ap-fade-in--d4">
            <div className="ap-chart-panel__header">
              <div>
                <h2 className="ap-chart-panel__title">
                  {newsLabel} News Sentiment
                </h2>
                <p className="ap-chart-panel__desc">
                  Source: {sourceLabel} · Average daily VADER compound score
                </p>
              </div>
              <div className="ap-chart-panel__legend">
                <div className="ap-legend-item">
                  <span className="ap-legend-dot" style={{ background: sentColor }} />
                  Sentiment
                </div>
              </div>
            </div>
            <SingleBarChart
              data={data.dailyData}
              dataKey="sentiment"
              color={sentColor}
              unit="Sentiment"
              formatValue={(v) => `${v >= 0 ? "+" : ""}${v.toFixed(3)}`}
            />
          </div>

          {/* return chart */}
          <div className="ap-chart-panel ap-fade-in ap-fade-in--d5">
            <div className="ap-chart-panel__header">
              <div>
                <h2 className="ap-chart-panel__title">
                  {mktLabel} ETF Return
                </h2>
                <p className="ap-chart-panel__desc">
                  {mktSector} daily return percentage · {data.tradingDays.toLocaleString()} trading days
                </p>
              </div>
              <div className="ap-chart-panel__legend">
                <div className="ap-legend-item">
                  <span className="ap-legend-dot" style={{ background: retColor }} />
                  Return %
                </div>
              </div>
            </div>
            <SingleBarChart
              data={data.dailyData}
              dataKey="returnPct"
              color={retColor}
              unit="Return"
              formatValue={(v) => `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`}
            />
          </div>
        </div>

        {/* sidebar */}
        <div className="ap-sidebar">
          <StatCard
            label="Prediction Accuracy"
            value={`${data.accuracy}%`}
            detail={`${data.accuracy >= 50 ? "Above" : "Below"} 50% random baseline`}
            colorClass={accClass}
            delay="ap-fade-in--d4"
          />
          <StatCard
            label="Pearson Correlation"
            value={`${data.correlation >= 0 ? "+" : ""}${data.correlation.toFixed(4)}`}
            detail={
              Math.abs(data.correlation) < 0.05
                ? "Negligible linear relationship"
                : data.correlation > 0
                ? "Weak positive association"
                : "Weak negative association"
            }
            colorClass={corrClass}
            delay="ap-fade-in--d5"
          />

          {/* detail card */}
          <div className="ap-source-card ap-fade-in ap-fade-in--d6">
            <div className="ap-source-card__header">Dataset Details</div>
            <div className="ap-source-card__row">
              <span className="ap-source-card__key">Articles</span>
              <span className="ap-source-card__val">{data.articles.toLocaleString()}</span>
            </div>
            <div className="ap-source-card__row">
              <span className="ap-source-card__key">Trading Days</span>
              <span className="ap-source-card__val">{data.tradingDays.toLocaleString()}</span>
            </div>
            <div className="ap-source-card__row">
              <span className="ap-source-card__key">Mean Sentiment</span>
              <span className="ap-source-card__val">
                {data.meanSentiment >= 0 ? "+" : ""}{data.meanSentiment.toFixed(3)}
              </span>
            </div>
            <div className="ap-source-card__row">
              <span className="ap-source-card__key">Mean Return</span>
              <span className="ap-source-card__val">
                {data.meanReturn >= 0 ? "+" : ""}{(data.meanReturn * 100).toFixed(2)}%
              </span>
            </div>
          </div>

          {/* backend notice */}
          <div className="ap-notice ap-fade-in ap-fade-in--d7">
            <span className="ap-notice__icon">🔌</span>
            <span className="ap-notice__text">
              <strong>Mock data.</strong> This dashboard is using generated placeholder data.
              Connect the cluster database to populate with real analysis results.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
