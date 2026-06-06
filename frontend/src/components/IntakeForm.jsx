import { useState } from "react";
import { IconPulse, IconCheck, IconShield, IconLock } from "./Icons.jsx";

const EXAMPLES = [
  "I've had a throbbing headache and mild fever for the past two days.",
  "Sharp chest discomfort when I climb stairs, plus shortness of breath.",
  "Persistent dry cough and a sore throat for about a week.",
  "Lower back pain that gets worse when I sit for long periods.",
];

const ASSURANCES = [
  "Symptoms analyzed by a multi-agent AI assistant",
  "Matched to relevant specialists from our directory",
  "Suggested appointment slots and clear next steps",
];

export default function IntakeForm({ onSubmit, error }) {
  const [userInput, setUserInput] = useState("");
  const [preferredDate, setPreferredDate] = useState("");
  const [preferredLocation, setPreferredLocation] = useState("");

  const tooShort = userInput.trim().length > 0 && userInput.trim().length < 10;
  const canSubmit = userInput.trim().length >= 10;

  function submit() {
    if (!canSubmit) return;
    onSubmit({
      user_input: userInput.trim(),
      preferred_date: preferredDate || undefined,
      preferred_location: preferredLocation || undefined,
    });
  }

  return (
    <section className="hero fade-in">
      <div className="hero-copy">
        <div className="eyebrow">AI-assisted triage</div>
        <h1 className="hero-title">
          Describe how you feel.<br />
          We'll help you find <em>the right care</em>.
        </h1>
        <p className="hero-sub">
          Tell HealthLink about your symptoms in plain words. It analyzes them,
          suggests the right kind of specialist, and proposes when to see them.
        </p>
        <div className="assurance">
          <ul>
            {ASSURANCES.map((a) => (
              <li key={a}>
                <IconCheck className="tick" width={17} height={17} />
                <span>{a}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="card intake-card">
        <h2>What's bothering you?</h2>
        <p className="hint">
          Be as specific as you can — symptoms, how long, and how severe.
        </p>

        {error && <div className="error-banner">{error}</div>}

        <div className="field">
          <label htmlFor="symptoms">Your symptoms</label>
          <textarea
            id="symptoms"
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            placeholder="e.g. I've had a sore throat and mild fever since yesterday…"
          />
          <div className="char-count">
            {tooShort
              ? `${10 - userInput.trim().length} more characters needed`
              : `${userInput.length} characters`}
          </div>
        </div>

        <div className="field-row">
          <div className="field">
            <label htmlFor="date">Preferred date (optional)</label>
            <input
              id="date"
              type="date"
              value={preferredDate}
              onChange={(e) => setPreferredDate(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="loc">Preferred location (optional)</label>
            <input
              id="loc"
              type="text"
              value={preferredLocation}
              onChange={(e) => setPreferredLocation(e.target.value)}
              placeholder="e.g. Pune"
            />
          </div>
        </div>

        <button
          className="btn btn-primary"
          onClick={submit}
          disabled={!canSubmit}
        >
          <IconPulse width={19} height={19} />
          Analyze my symptoms
        </button>

        <div className="examples">
          <div className="examples-label">Try an example</div>
          <div className="chips">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                className="chip"
                onClick={() => setUserInput(ex)}
              >
                {ex.length > 42 ? ex.slice(0, 40) + "…" : ex}
              </button>
            ))}
          </div>
        </div>

        <div className="disclaimer-strip">
          <IconLock width={15} height={15} style={{ flex: "none" }} />
          <span>
            HealthLink does not provide a medical diagnosis and is not a
            substitute for professional care. In an emergency, contact local
            emergency services.
          </span>
        </div>
      </div>
    </section>
  );
}
