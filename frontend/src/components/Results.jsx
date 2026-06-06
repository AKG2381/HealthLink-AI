import {
  IconPulse,
  IconStethoscope,
  IconCalendar,
  IconClipboard,
  IconAlert,
  IconCheck,
} from "./Icons.jsx";
import {
  urgencyClass,
  severityClass,
  initials,
  stars,
  formatDateTime,
} from "../lib/format.js";

function UrgencyPill({ level }) {
  return (
    <span className={`urgency-pill ${urgencyClass(level)}`}>
      <span className="pdot" />
      {level || "unknown"}
    </span>
  );
}

export default function Results({ data, onReset }) {
  const symptom = data.symptom_analysis || {};
  const docs = data.doctor_recommendations || {};
  const sched = data.scheduling_options || {};
  const summary = data.health_summary || {};

  const symptoms = symptom.symptoms || [];
  const recommended = docs.recommended_doctors || [];
  const slots = sched.available_slots || [];
  const recommendedSlotId = sched.recommended_slot?.slot_id;

  return (
    <div className="fade-in">
      <div className="results-head">
        <div>
          <h1>Your assessment</h1>
          <div className="meta">
            {data.request_id ? `Reference ${data.request_id.slice(0, 8)} · ` : ""}
            {formatDateTime(data.timestamp)}
          </div>
        </div>
        <button className="btn btn-ghost" onClick={onReset}>
          New assessment
        </button>
      </div>

      <div className="results-grid stagger">
        {/* Symptoms */}
        <div className="card section">
          <div className="section-label">
            <IconPulse className="ico" width={15} height={15} />
            Symptom analysis
          </div>
          {symptom.primary_complaint && (
            <div className="primary-complaint">
              {symptom.primary_complaint}
            </div>
          )}
          <div style={{ marginBottom: 14 }}>
            <UrgencyPill level={symptom.urgency_level} />
          </div>
          <ul className="symptom-list">
            {symptoms.map((s, i) => (
              <li className="symptom-item" key={i}>
                <span className="symptom-name">{s.name}</span>
                <span
                  style={{ display: "flex", gap: 10, alignItems: "center" }}
                >
                  {s.duration && (
                    <span className="symptom-meta">{s.duration}</span>
                  )}
                  <span className={`sev ${severityClass(s.severity)}`}>
                    {s.severity}
                  </span>
                </span>
              </li>
            ))}
            {symptoms.length === 0 && (
              <li className="symptom-meta">No discrete symptoms extracted.</li>
            )}
          </ul>
          {symptom.additional_context && (
            <p className="rationale">{symptom.additional_context}</p>
          )}
        </div>

        {/* Doctors */}
        <div className="card section">
          <div className="section-label">
            <IconStethoscope className="ico" width={15} height={15} />
            Recommended specialists
          </div>
          {recommended.map((d, i) => (
            <div className="doctor" key={i}>
              <div className="avatar">{initials(d.name)}</div>
              <div className="doctor-info">
                <div className="doctor-name">{d.name}</div>
                <div className="doctor-spec">{d.specialty}</div>
                <div className="doctor-line">
                  <span className="stars">{stars(d.rating)}</span>
                  <span>{d.experience_years} yrs exp</span>
                  {d.location && <span>{d.location}</span>}
                </div>
              </div>
            </div>
          ))}
          {recommended.length === 0 && (
            <p className="symptom-meta">No specialist matches returned.</p>
          )}
          {docs.specialty_rationale && (
            <p className="rationale">{docs.specialty_rationale}</p>
          )}
        </div>

        {/* Scheduling */}
        <div className="card section span-2">
          <div className="section-label">
            <IconCalendar className="ico" width={15} height={15} />
            Suggested appointments
          </div>
          <div className="slot-grid">
            {slots.map((s, i) => {
              const isRec =
                recommendedSlotId && s.slot_id === recommendedSlotId;
              return (
                <div
                  className={`slot ${isRec ? "recommended" : ""}`}
                  key={s.slot_id || i}
                >
                  <div className="slot-doc">{s.doctor_name}</div>
                  <div className="slot-when">
                    {s.date} · {s.time}
                  </div>
                  {isRec && <div className="slot-badge">Recommended</div>}
                </div>
              );
            })}
            {slots.length === 0 && (
              <p className="symptom-meta">No slots available right now.</p>
            )}
          </div>
          {sched.scheduling_notes && (
            <p className="rationale">{sched.scheduling_notes}</p>
          )}
        </div>

        {/* Summary */}
        <div className="card section span-2">
          <div className="section-label">
            <IconClipboard className="ico" width={15} height={15} />
            Summary &amp; next steps
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              marginBottom: 14,
              flexWrap: "wrap",
            }}
          >
            <h3 style={{ margin: 0 }}>Overall assessment</h3>
            <UrgencyPill level={summary.urgency_assessment} />
          </div>
          {summary.summary && <p className="summary-text">{summary.summary}</p>}

          <div className="findings">
            {summary.key_findings?.length > 0 && (
              <div>
                <h4>Key findings</h4>
                <ul>
                  {summary.key_findings.map((f, i) => (
                    <li key={i}>
                      <IconPulse className="bullet" width={14} height={14} />
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {summary.recommended_actions?.length > 0 && (
              <div>
                <h4>Recommended actions</h4>
                <ul>
                  {summary.recommended_actions.map((a, i) => (
                    <li key={i}>
                      <IconCheck className="bullet" width={14} height={14} />
                      <span>{a}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {summary.disclaimer && (
            <div className="disclaimer-box">
              <IconAlert width={16} height={16} style={{ flex: "none" }} />
              <span>{summary.disclaimer}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
