import { useEffect, useState } from "react";

const STEPS = [
  "Reading and extracting your symptoms",
  "Assessing urgency and likely specialty",
  "Matching specialists from the directory",
  "Preparing appointment options and summary",
];

export default function Loading() {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const t = setInterval(() => {
      setActive((a) => Math.min(a + 1, STEPS.length - 1));
    }, 2600);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="loading fade-in">
      <div className="pulse-ring" />
      <h3>Working through your assessment</h3>
      <p>This usually takes a few moments.</p>
      <div className="loading-steps">
        {STEPS.map((s, i) => (
          <div
            key={s}
            className={`loading-step ${i <= active ? "active" : ""}`}
          >
            <span className="num">{i + 1}</span>
            <span>{s}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
