/**
 * NewsAlpha API Client
 * ====================
 * Drop this into your src/ folder.
 * Replace mock data in your pages with these fetch calls.
 *
 * Usage:
 *   import { api } from './api';
 *   const sectors = await api.getSectors();
 */

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${path}`);
  }
  return res.json();
}

// ─── Types ───────────────────────────────────────────────────────────────────

export interface SectorSummary {
  sector: string;
  accuracy: number;
  days: number;
  correlation: number;
  mean_sentiment: number;
  total_articles: number;
}

export interface TimeSeriesRow {
  date: string;
  sector: string;
  avg_sentiment: number;
  article_count: number;
  daily_return_pct: number;
  market_direction: string;
  [key: string]: unknown; // extra columns like sentiment_std, open, close
}

export interface CorrelationRow {
  sector: string;
  correlation: number;
  mean_sentiment: number;
  days: number;
}

export interface CrossSectorRow {
  sent_sector: string;
  mkt_sector: string;
  correlation: number;
  days: number;
}

export interface AccuracyRow {
  sector: string;
  accuracy: number;
  days: number;
}

export interface SourceAccuracyRow {
  source_name: string;
  accuracy: number;
  num_days: number;
  mean_sentiment: number;
}

export interface OverviewStats {
  total_matched_days: number;
  sectors: number;
  overall_correlation: number;
  overall_accuracy: number;
  date_range: { start: string; end: string };
}

export interface Filters {
  sectors: string[];
  sources: string[];
}

// ─── API Methods ─────────────────────────────────────────────────────────────

export const api = {
  // Health
  health: () => fetchJSON<{ status: string; tables: string[] }>("/api/health"),

  // Home page
  getSectors: () => fetchJSON<SectorSummary[]>("/api/sectors"),

  // Analysis page — time series for one sector
  getTimeSeries: (sector: string, start?: string, end?: string) => {
    const params = new URLSearchParams({ sector });
    if (start) params.set("start", start);
    if (end) params.set("end", end);
    return fetchJSON<TimeSeriesRow[]>(`/api/timeseries?${params}`);
  },

  // Correlations
  getSameSectorCorrelations: () =>
    fetchJSON<CorrelationRow[]>("/api/correlations/same-sector"),

  getCrossSectorCorrelations: (minDays = 0) =>
    fetchJSON<CrossSectorRow[]>(
      `/api/correlations/cross-sector?min_days=${minDays}`
    ),

  getNextDayCorrelations: () =>
    fetchJSON<CorrelationRow[]>("/api/correlations/next-day"),

  // Prediction accuracy
  getSameDayAccuracy: () =>
    fetchJSON<AccuracyRow[]>("/api/accuracy/same-day"),

  getNextDayAccuracy: () =>
    fetchJSON<AccuracyRow[]>("/api/accuracy/next-day"),

  getSourceAccuracy: () =>
    fetchJSON<SourceAccuracyRow[]>("/api/accuracy/by-source"),

  // Volatility
  getVolatility: () => fetchJSON<CorrelationRow[]>("/api/volatility"),

  // Stats
  getOverviewStats: () => fetchJSON<OverviewStats>("/api/stats/overview"),

  getSectorDetail: (ticker: string) =>
    fetchJSON<{
      sector: string;
      correlation: CorrelationRow | null;
      accuracy: AccuracyRow | null;
      next_day_accuracy: AccuracyRow | null;
      summary: {
        trading_days: number;
        first_date: string;
        last_date: string;
        mean_sentiment: number;
        mean_return: number;
      } | null;
    }>(`/api/stats/sector/${ticker}`),

  // Dropdowns
  getFilters: () => fetchJSON<Filters>("/api/filters"),
};
