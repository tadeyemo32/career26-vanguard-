import { useState, useEffect } from "react";
import { api, PersonRow } from "./api";
import "./index.css";

function App() {
  const [health, setHealth] = useState<boolean | null>(null);
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<PersonRow[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api.checkHealth().then(setHealth);
  }, []);

  const runOutreach = async () => {
    setRunning(true);
    setError("");
    setResults([]);

    const { results, error } = await api.outreachRun({
      count: 1,
      max_per_company: 5,
      fetch_metadata: true,
      min_score: 0.8
    });

    if (error) setError(error);
    else setResults(results);

    setRunning(false);
  };

  return (
    <div className="container">
      <header>
        <h1>Vanguard Outreach Pipeline</h1>
        <p className={`status ${health ? 'online' : 'offline'}`}>
          Backend Go API: {health === null ? 'Pinging...' : health ? 'Connected' : 'Disconnected'}
        </p>
      </header>

      <main>
        <div className="card">
          <h2>Asset Manager Pipeline test</h2>
          <p>This will test hitting the Go backend for the rewritten asset management scraping pipeline.</p>
          <button onClick={runOutreach} disabled={running}>
            {running ? "Scanning..." : "Run Test Search"}
          </button>

          {error && <div className="error">{error}</div>}
        </div>

        {results.length > 0 && (
          <div className="card results">
            <h2>Results</h2>
            <div className="grid">
              {results.map((r, i) => (
                <div key={i} className="row">
                  <div className="avatar">{r.name.charAt(0)}</div>
                  <div className="info">
                    <strong>{r.name} - {r.title}</strong>
                    <span>{r.company} | {r.company_size} req: {r.target_roles}</span>
                    <span className="email">{r.email} ({r.confidence * 100}%)</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
