export function urgencyClass(level = "") {
  const l = level.toLowerCase();
  if (l.includes("emerg")) return "u-emergency";
  if (l.includes("high")) return "u-high";
  if (l.includes("med")) return "u-medium";
  return "u-low";
}

export function severityClass(sev = "") {
  const s = sev.toLowerCase();
  if (s.includes("severe")) return "sev-severe";
  if (s.includes("mod")) return "sev-moderate";
  return "sev-mild";
}

export function initials(name = "") {
  return name
    .replace(/^Dr\.?\s*/i, "")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join("");
}

export function stars(rating = 0) {
  const full = Math.round(rating);
  return "★".repeat(Math.max(0, Math.min(5, full))) +
    "☆".repeat(Math.max(0, 5 - full));
}

export function formatDateTime(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}
