import { useEffect, useState } from "react";
import { listDoctors, listSpecialties } from "../lib/api.js";
import { initials, stars } from "../lib/format.js";

export default function Doctors() {
  const [specialties, setSpecialties] = useState([]);
  const [specialty, setSpecialty] = useState("");
  const [doctors, setDoctors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    listSpecialties()
      .then((s) => setSpecialties(Array.isArray(s) ? s : []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    setError("");
    listDoctors({ specialty: specialty || undefined, limit: 60 })
      .then((d) => setDoctors(Array.isArray(d) ? d : []))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [specialty]);

  return (
    <div className="fade-in">
      <div className="dir-head">
        <h1>Doctor directory</h1>
        <p>Browse specialists available through HealthLink.</p>
      </div>

      <div className="filter-bar">
        <select
          value={specialty}
          onChange={(e) => setSpecialty(e.target.value)}
        >
          <option value="">All specialties</option>
          {specialties.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {loading ? (
        <div className="empty">
          <p>Loading doctors…</p>
        </div>
      ) : doctors.length === 0 ? (
        <div className="empty">
          <h3>No doctors found</h3>
          <p>Try a different specialty.</p>
        </div>
      ) : (
        <div className="dir-grid stagger">
          {doctors.map((d) => (
            <div className="card dir-card" key={d.id}>
              <div className="doctor" style={{ border: "none", padding: 0, margin: 0 }}>
                <div className="avatar">{initials(d.name)}</div>
                <div className="doctor-info">
                  <div className="doctor-name">{d.name}</div>
                  <div className="doctor-spec">{d.specialty}</div>
                  <div className="doctor-line">
                    <span className="stars">{stars(d.rating)}</span>
                    <span>{d.rating?.toFixed?.(1)}</span>
                  </div>
                  <div className="doctor-line">
                    <span>{d.experience_years} yrs experience</span>
                  </div>
                  {d.location && (
                    <div className="doctor-line">
                      <span>{d.location}</span>
                    </div>
                  )}
                  {d.availability && (
                    <div className="doctor-line">
                      <span>Available: {d.availability}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
