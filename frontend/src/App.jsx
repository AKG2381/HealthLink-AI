import { useEffect, useState } from "react";
import { assessHealth, getHealth } from "./lib/api.js";
import IntakeForm from "./components/IntakeForm.jsx";
import Loading from "./components/Loading.jsx";
import Results from "./components/Results.jsx";
import Doctors from "./components/Doctors.jsx";
import { IconShield } from "./components/Icons.jsx";

export default function App() {
  const [view, setView] = useState("assess"); // assess | doctors
  const [phase, setPhase] = useState("form"); // form | loading | results
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [health, setHealth] = useState(null);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch(() => setHealth({ status: "unreachable", services: {} }));
  }, []);

  async function handleSubmit(body) {
    setError("");
    setPhase("loading");
    try {
      const data = await assessHealth(body);
      setResult(data);
      setPhase("results");
    } catch (e) {
      setError(e.message);
      setPhase("form");
    }
  }

  function reset() {
    setResult(null);
    setError("");
    setPhase("form");
  }

  const llmState = health?.services?.llm;
  const statusClass =
    health?.status === "unreachable" || llmState === "unavailable"
      ? "bad"
      : health
      ? "ok"
      : "warn";
  const statusLabel =
    health?.status === "unreachable"
      ? "Server offline"
      : llmState === "unavailable"
      ? "AI unavailable"
      : health
      ? "All systems go"
      : "Checking…";

  return (
    <div className="app">
      <header className="masthead">
        <div className="masthead-inner">
          <div
            className="brand"
            onClick={() => {
              setView("assess");
              reset();
            }}
          >
            <div className="brand-mark">
              <IconShield width={20} height={20} />
            </div>
            <div>
              <div className="brand-name">
                Health<span>Link</span>
              </div>
              <div className="brand-tag">Smart health management</div>
            </div>
          </div>

          <nav className="nav">
            <button
              className={view === "assess" ? "active" : ""}
              onClick={() => setView("assess")}
            >
              Assess
            </button>
            <button
              className={view === "doctors" ? "active" : ""}
              onClick={() => setView("doctors")}
            >
              Doctors
            </button>
            <span className="health-dot" title={JSON.stringify(health?.services || {})}>
              <span className={`dot ${statusClass}`} />
              {statusLabel}
            </span>
          </nav>
        </div>
      </header>

      <main className="main">
        {view === "doctors" ? (
          <Doctors />
        ) : phase === "loading" ? (
          <Loading />
        ) : phase === "results" && result ? (
          <Results data={result} onReset={reset} />
        ) : (
          <IntakeForm onSubmit={handleSubmit} error={error} />
        )}
      </main>

      <footer>
        HealthLink · For information only — not a medical diagnosis. In an
        emergency, contact local emergency services.
      </footer>
    </div>
  );
}
