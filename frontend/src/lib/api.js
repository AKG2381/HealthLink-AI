// API client for the HealthLink FastAPI backend.
//
// Base URL resolution:
//   - In dev, leave VITE_API_BASE unset; Vite proxies "/api" to the backend.
//   - In production, set VITE_API_BASE at build time to the deployed backend,
//     e.g. VITE_API_BASE=https://healthlink-xxxx.run.app
const RAW_BASE = import.meta.env.VITE_API_BASE || "";
const API_BASE = `${RAW_BASE.replace(/\/$/, "")}/api/v1`;

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch (networkErr) {
    throw new Error(
      "Could not reach the HealthLink server. Is the backend running?"
    );
  }

  let payload = null;
  const text = await res.text();
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = { message: text };
    }
  }

  if (!res.ok) {
    const detail =
      payload?.detail || payload?.message || payload?.error || res.statusText;
    const message =
      typeof detail === "string" ? detail : JSON.stringify(detail);
    throw new Error(message || `Request failed (${res.status})`);
  }

  return payload;
}

export function getHealth() {
  return request("/health");
}

// request: { user_input, user_id?, preferred_date?, preferred_location? }
export function assessHealth(body) {
  return request("/assess", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function listDoctors({ specialty, limit } = {}) {
  const params = new URLSearchParams();
  if (specialty) params.set("specialty", specialty);
  if (limit) params.set("limit", String(limit));
  const qs = params.toString();
  return request(`/doctors${qs ? `?${qs}` : ""}`);
}

export function listSpecialties() {
  return request("/specialties");
}
