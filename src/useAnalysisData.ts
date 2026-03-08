/**
 * Example: Replace mock data in AnalysisPage with real API calls
 * ===============================================================
 * This shows the pattern. Adapt it to match your actual component state.
 */

import { useState, useEffect } from "react";
import { api, TimeSeriesRow, Filters } from "./api";

export function useAnalysisData() {
  const [sector, setSector] = useState("XLK");
  const [timeSeries, setTimeSeries] = useState<TimeSeriesRow[]>([]);
  const [filters, setFilters] = useState<Filters>({ sectors: [], sources: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load available filter options once on mount
  useEffect(() => {
    api.getFilters().then(setFilters).catch(console.error);
  }, []);

  // Fetch time series whenever the selected sector changes
  useEffect(() => {
    setLoading(true);
    setError(null);

    api
      .getTimeSeries(sector)
      .then((data) => {
        setTimeSeries(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [sector]);

  return {
    sector,
    setSector,
    timeSeries,
    filters,
    loading,
    error,
  };
}

/*
  Then in your AnalysisPage.tsx, replace the mock data section with:

  import { useAnalysisData } from './useAnalysisData';

  function AnalysisPage() {
    const { sector, setSector, timeSeries, filters, loading, error } = useAnalysisData();

    // Your existing dropdown becomes:
    <select value={sector} onChange={(e) => setSector(e.target.value)}>
      {filters.sectors.map(s => (
        <option key={s} value={s}>{s}</option>
      ))}
    </select>

    // Your chart data comes from timeSeries instead of MOCK_DATA:
    const chartData = timeSeries.map(row => ({
      date: row.date,
      sentiment: row.avg_sentiment,
      return: row.daily_return_pct,
      direction: row.market_direction,
    }));

    // ... rest of your component
  }
*/
