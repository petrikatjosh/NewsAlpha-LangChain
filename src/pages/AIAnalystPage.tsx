import { useState } from "react";
import { Link } from "react-router-dom";
import { BarChart, Bar, LineChart, Line, PieChart, Pie, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from "recharts";
import "./AIAnalystPage.css";

interface ChartConfig {
  type: "bar" | "line" | "pie" | "scatter" | "none";
  xAxisKey?: string;
  yAxisKey?: string;
}

export default function AIAnalystPage() {
  const [question, setQuestion] = useState("");
  const [loadingSql, setLoadingSql] = useState(false);
  const [sqlQuery, setSqlQuery] = useState<string | null>(null);
  const [sqlError, setSqlError] = useState<string | null>(null);

  const [executing, setExecuting] = useState(false);
  const [formattedAnswer, setFormattedAnswer] = useState<string | null>(null);
  const [rawResult, setRawResult] = useState<any[] | null>(null);
  const [chartConfig, setChartConfig] = useState<ChartConfig | null>(null);
  const [execError, setExecError] = useState<string | null>(null);
  
  const [showRaw, setShowRaw] = useState(false);

  const sampleQueries = [
    "What is the average compound sentiment score for articles about the Technology sector (XLK)?",
    "List the top 5 days with the highest average sentiment score across all sectors.",
    "What was the closing price of the Financials ETF (XLF) on the most recent date?",
    "Which 3 news sectors have the most pessimistic average sentiment?",
    "How many articles contain the word 'market' in their headline?",
    "Drop the articles table."
  ];

  const handleGenerateSql = async () => {
    if (!question.trim()) return;
    
    setLoadingSql(true);
    setSqlQuery(null);
    setSqlError(null);
    setFormattedAnswer(null);
    setRawResult(null);
    setShowRaw(false);

    try {
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question })
      });
      
      let data;
      const contentType = res.headers.get("content-type");
      if (contentType && contentType.indexOf("application/json") !== -1) {
        data = await res.json();
      } else {
        const text = await res.text();
        throw new Error(`Server returned a non-JSON response (${res.status}): ${text || "Empty response"}`);
      }
      
      if (!res.ok) {
        if (data.generated_sql && data.error.includes("SELECT")) {
           throw new Error(data.error + " (Query was: " + data.generated_sql + ")");
        }
        const errorMessage = data.details || data.error || "Failed to generate SQL";
        throw new Error(typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage));
      }
      
      setSqlQuery(data.sql);
    } catch (err: any) {
      setSqlError(err.message);
    } finally {
      setLoadingSql(false);
    }
  };

  const handleExecuteSql = async () => {
    if (!sqlQuery || !question) return;

    setExecuting(true);
    setExecError(null);
    setFormattedAnswer(null);
    setRawResult(null);
    setChartConfig(null);

    try {
      const res = await fetch("/api/execute_sql", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, sql: sqlQuery })
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.error || "Failed to execute SQL");
      }
      
      setFormattedAnswer(data.formattedAnswer);
      setRawResult(data.rawResult);
      if (data.chartConfig) setChartConfig(data.chartConfig);
    } catch (err: any) {
      setExecError(err.message);
    } finally {
      setExecuting(false);
    }
  };

  const renderChart = () => {
    if (!chartConfig || chartConfig.type === "none" || !rawResult || rawResult.length === 0) return null;

    const { type, xAxisKey, yAxisKey } = chartConfig;
    if (!xAxisKey && type !== "pie") return null;

    const data = rawResult.map(row => ({
      ...row,
      [yAxisKey || "value"]: Number(row[yAxisKey || "value"]) || row[yAxisKey || "value"]
    }));

    const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

    return (
      <div className="ap-chart-container ap-fade-in">
        <ResponsiveContainer width="100%" height={400}>
          {type === "bar" ? (
            <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey={xAxisKey} stroke="#888" />
              <YAxis stroke="#888" />
              <Tooltip contentStyle={{ backgroundColor: "#1e1e1e", borderColor: "#333", color: "#fff" }} />
              <Legend />
              <Bar dataKey={yAxisKey!} fill="#3b82f6" />
            </BarChart>
          ) : type === "line" ? (
            <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey={xAxisKey} stroke="#888" />
              <YAxis stroke="#888" />
              <Tooltip contentStyle={{ backgroundColor: "#1e1e1e", borderColor: "#333", color: "#fff" }} />
              <Legend />
              <Line type="monotone" dataKey={yAxisKey!} stroke="#10b981" strokeWidth={2} activeDot={{ r: 8 }} />
            </LineChart>
          ) : type === "scatter" ? (
            <ScatterChart margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey={xAxisKey} name={xAxisKey} stroke="#888" />
              <YAxis dataKey={yAxisKey} name={yAxisKey} stroke="#888" />
              <Tooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={{ backgroundColor: "#1e1e1e", borderColor: "#333", color: "#fff" }} />
              <Legend />
              <Scatter name="Data" data={data} fill="#f59e0b" />
            </ScatterChart>
          ) : type === "pie" && xAxisKey && yAxisKey ? (
            <PieChart>
              <Tooltip contentStyle={{ backgroundColor: "#1e1e1e", borderColor: "#333", color: "#fff" }} />
              <Legend />
              <Pie data={data} dataKey={yAxisKey} nameKey={xAxisKey} cx="50%" cy="50%" outerRadius={120} fill="#8b5cf6" label>
                {data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
            </PieChart>
          ) : <div />}
        </ResponsiveContainer>
      </div>
    );
  };

  return (
    <div className="ap-root">
      {/* ── NAV ── */}
      <nav className="ap-nav">
        <span className="ap-nav__title">NewsAlpha</span>
        <div className="ap-nav__links">
          <Link to="/" className="ap-nav-link">Home</Link>
          <Link to="/analysis" className="ap-nav-link">Analysis</Link>
          <Link to="/paper" className="ap-nav-link">Paper</Link>
          <Link to="/ai-analyst" className="ap-nav-link ap-nav-link--active">AI Analyst</Link>
          <Link to="/about" className="ap-nav-link">About</Link>
        </div>
      </nav>

      {/* ── PAGE HEADER ── */}
      <div className="ap-header ap-fade-in ap-fade-in--d1">
        <p className="ap-header__label">Natural Language to SQL</p>
        <h1 className="ap-header__h1">AI Analyst</h1>
        <p className="ap-header__subtitle">
          Ask questions about the database in plain English. The AI will generate a safe SELECT query to retrieve the answer.
        </p>
      </div>

      <div className="ap-content ap-analyst-container ap-fade-in ap-fade-in--d2">
        <div className="ap-analyst-form">
          <textarea 
            id="ai-analyst-question-input"
            autoFocus
            className="ap-analyst-textarea" 
            placeholder="e.g. Which news source published the most articles?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
          <button 
            id="ai-analyst-generate-btn"
            className="ap-analyst-button" 
            onClick={handleGenerateSql}
            disabled={loadingSql || !question.trim()}
          >
            {loadingSql ? "Generating SQL..." : "Generate SQL"}
          </button>
          
          {sqlError && <div style={{ color: "var(--red)", marginTop: "1rem" }}>{sqlError}</div>}
        </div>

        {sqlQuery && (
          <div className="ap-sql-verification ap-fade-in">
            <h3>Generated SQL for Verification</h3>
            <p className="ap-color-text" style={{ fontSize: "0.9rem", marginBottom: "1rem" }}>
              Please review the query before executing to ensure it is a safe SELECT statement.
            </p>
            <pre>{sqlQuery}</pre>
            <div style={{ marginTop: "1rem" }}>
              <button 
                id="ai-analyst-run-query-btn"
                className="ap-analyst-button" 
                onClick={handleExecuteSql}
                disabled={executing}
                style={{ background: "var(--green)" }}
              >
                {executing ? "Executing..." : "Run Query"}
              </button>
            </div>
            {execError && <div style={{ color: "var(--red)", marginTop: "1rem" }}>{execError}</div>}
          </div>
        )}

        {formattedAnswer && (
          <div className="ap-answer-box ap-fade-in">
            <h3>Answer</h3>
            <p>{formattedAnswer}</p>
          </div>
        )}

        {renderChart()}

        {rawResult && (
          <div className="ap-fade-in">
            <button className="ap-raw-data-toggle" onClick={() => setShowRaw(!showRaw)}>
              {showRaw ? "Hide Raw Data" : "Show Raw Data"}
            </button>
            
            {showRaw && rawResult.length > 0 && (
              <div style={{ overflowX: "auto" }}>
                <table className="ap-raw-data-table">
                  <thead>
                    <tr>
                      {Object.keys(rawResult[0]).map(k => <th key={k}>{k}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {rawResult.map((row, i) => (
                      <tr key={i}>
                        {Object.values(row).map((val: any, j) => <td key={j}>{String(val)}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            
            {showRaw && rawResult.length === 0 && (
              <p>No results found for this query.</p>
            )}
          </div>
        )}

        <div className="ap-sample-queries">
          <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginBottom: "0.5rem" }}>Try a sample query:</p>
          <div>
            {sampleQueries.map((q, i) => (
              <button 
                key={i} 
                id={`ai-analyst-sample-q-${i}`}
                className="ap-sample-query-btn"
                onClick={() => setQuestion(q)}
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
