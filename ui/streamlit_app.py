"""
HealthLink Streamlit UI
User-friendly interface for the health assessment system.

Talks to the FastAPI backend over HTTP. Configure the backend with the
API_BASE_URL env var, e.g.
    API_BASE_URL=https://healthlink-xxxx.asia-south1.run.app/api/v1
Defaults to http://localhost:8000/api/v1 for local development.
"""
import streamlit as st
import requests
import json
import os
from datetime import datetime, timedelta


# Configuration. Accept the base URL with or without a trailing /api/v1.
_raw_base = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1").rstrip("/")
API_BASE_URL = _raw_base if _raw_base.endswith("/api/v1") else f"{_raw_base}/api/v1"

REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "120"))


st.set_page_config(
    page_title="HealthLink - Smart Health Management",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .main-header { font-size: 2.5rem; color: #0f766e; text-align: center; margin-bottom: 0.25rem; }
    .symptom-box { background-color: #f0f2f6; padding: 0.75rem 1rem; border-radius: 0.5rem; margin: 0.4rem 0; }
    .doctor-card { background-color: #ffffff; padding: 1.25rem; border-radius: 0.5rem; border: 1px solid #e0e0e0; margin: 0.75rem 0; }
    .urgency-emergency, .urgency-high { color: #b3261e; font-weight: bold; }
    .urgency-medium { color: #c7902a; font-weight: bold; }
    .urgency-low { color: #2f8f6b; font-weight: bold; }
</style>
""",
    unsafe_allow_html=True,
)


def get_api_health():
    """Return the backend health payload, or None if unreachable."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=8)
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.RequestException:
        pass
    return None


def urgency_class(urgency_level):
    mapping = {
        "emergency": "urgency-emergency",
        "high": "urgency-high",
        "medium": "urgency-medium",
        "low": "urgency-low",
    }
    return mapping.get(str(urgency_level).lower(), "urgency-medium")


def clean_doctor_name(name):
    """Avoid double 'Dr.' since the data already includes the prefix."""
    name = (name or "").strip()
    return name if name.lower().startswith("dr") else f"Dr. {name}"


def display_symptom_analysis(symptom_data):
    st.subheader("📋 Symptom Analysis")

    if symptom_data.get("primary_complaint"):
        st.markdown(f"**Primary Complaint:** {symptom_data['primary_complaint']}")

    urgency = symptom_data.get("urgency_level", "unknown")
    st.markdown(
        f"**Urgency Level:** <span class='{urgency_class(urgency)}'>{str(urgency).upper()}</span>",
        unsafe_allow_html=True,
    )

    symptoms = symptom_data.get("symptoms") or []
    if symptoms:
        st.markdown("**Identified Symptoms:**")
        for symptom in symptoms:
            duration = symptom.get("duration")
            duration_text = f" (Duration: {duration})" if duration else ""
            st.markdown(
                f"<div class='symptom-box'>• <strong>{symptom.get('name', 'Unknown')}</strong>"
                f" — Severity: {symptom.get('severity', 'n/a')}{duration_text}</div>",
                unsafe_allow_html=True,
            )

    if symptom_data.get("additional_context"):
        st.info(f"ℹ️ {symptom_data['additional_context']}")


def display_doctor_recommendations(doctor_data):
    st.subheader("👨‍⚕️ Recommended Doctors")

    if doctor_data.get("specialty_rationale"):
        st.markdown(f"**Specialty Rationale:** {doctor_data['specialty_rationale']}")
    if doctor_data.get("match_score") is not None:
        st.markdown(f"**Match Confidence:** {doctor_data['match_score']:.0%}")

    doctors = doctor_data.get("recommended_doctors") or []
    if not doctors:
        st.warning("No doctors available at this time.")
        return

    for doctor in doctors:
        location = doctor.get("location")
        location_html = (
            f"<p><strong>Location:</strong> {location}</p>" if location else ""
        )
        st.markdown(
            f"""
            <div class='doctor-card'>
                <h4>{clean_doctor_name(doctor.get('name'))}</h4>
                <p><strong>Specialty:</strong> {doctor.get('specialty', 'n/a')}</p>
                <p><strong>Experience:</strong> {doctor.get('experience_years', 'n/a')} years</p>
                <p><strong>Rating:</strong> ⭐ {doctor.get('rating', 'n/a')}/5.0</p>
                <p><strong>Availability:</strong> {doctor.get('availability', 'n/a')}</p>
                {location_html}
            </div>
            """,
            unsafe_allow_html=True,
        )


def display_scheduling(scheduling_data):
    st.subheader("📅 Appointment Scheduling")

    if scheduling_data.get("scheduling_notes"):
        st.info(scheduling_data["scheduling_notes"])

    recommended = scheduling_data.get("recommended_slot")
    if recommended:
        st.success(
            f"**Recommended Appointment:** {recommended.get('doctor_name', '')} on "
            f"{recommended.get('date', '')} at {recommended.get('time', '')} "
            f"({recommended.get('duration_minutes', 30)} minutes)"
        )

    slots = scheduling_data.get("available_slots") or []
    if slots:
        st.markdown("**Other Available Slots:**")
        slots_by_doctor = {}
        for slot in slots[:20]:
            slots_by_doctor.setdefault(slot.get("doctor_name", "Unknown"), []).append(slot)

        for doctor, doc_slots in slots_by_doctor.items():
            with st.expander(f"📅 {doctor}"):
                for slot in doc_slots[:5]:
                    st.write(f"• {slot.get('date', '')} at {slot.get('time', '')}")
    elif not recommended:
        st.write("No appointment slots are available right now.")


def display_health_summary(summary_data):
    st.subheader("📝 Health Summary")

    if summary_data.get("summary"):
        st.markdown("**Assessment Summary:**")
        st.write(summary_data["summary"])

    findings = summary_data.get("key_findings") or []
    if findings:
        st.markdown("**Key Findings:**")
        for finding in findings:
            st.markdown(f"• {finding}")

    actions = summary_data.get("recommended_actions") or []
    if actions:
        st.markdown("**Recommended Actions:**")
        for action in actions:
            st.markdown(f"✓ {action}")

    if summary_data.get("urgency_assessment"):
        st.markdown(f"**Overall Urgency:** {str(summary_data['urgency_assessment']).upper()}")

    if summary_data.get("disclaimer"):
        st.warning(f"⚠️ **Disclaimer:** {summary_data['disclaimer']}")


def render_status_sidebar(health):
    """Show backend service status so missing keys are visible."""
    st.subheader("System status")
    if not health:
        st.error("Backend unreachable")
        return
    services = health.get("services", {})
    labels = {
        "healthy": "🟢",
        "unavailable": "🔴",
        "disabled": "⚪",
        "degraded": "🟡",
    }
    for name in ("llm", "database", "rag"):
        state = services.get(name, "unknown")
        st.write(f"{labels.get(state, '⚪')} {name.upper()}: {state}")
    if services.get("llm") == "unavailable":
        st.caption("AI features need ANTHROPIC_API_KEY set on the backend.")


def main():
    st.markdown("<h1 class='main-header'>🏥 HealthLink</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align: center; color: #666;'>Smart Health Management System</p>",
        unsafe_allow_html=True,
    )

    health = get_api_health()
    if not health:
        st.error("⚠️ Cannot connect to the HealthLink API.")
        st.info(f"Expected backend at: `{API_BASE_URL}`")
        st.caption("Start it locally with `uvicorn main:app --reload`, or set API_BASE_URL to your deployed backend.")
        return

    with st.sidebar:
        st.header("About HealthLink")
        st.write(
            "HealthLink uses AI to analyze your symptoms and recommend "
            "appropriate healthcare providers."
        )
        st.markdown("---")
        render_status_sidebar(health)
        st.markdown("---")
        st.subheader("How it works")
        st.write("1. Describe your symptoms")
        st.write("2. Get AI-powered analysis")
        st.write("3. Receive doctor recommendations")
        st.write("4. Review appointment options")
        st.markdown("---")
        st.caption("⚠️ Not a substitute for professional medical advice.")

    st.markdown("### Tell us about your health concern")

    with st.form("assessment_form"):
        user_input = st.text_area(
            "Describe your symptoms in detail:",
            placeholder="Example: I have had a severe headache for 3 days, along with fever and sensitivity to light...",
            height=150,
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            user_id = st.text_input("Your ID (optional):", placeholder="user123")
        with col2:
            preferred_date = st.date_input(
                "Preferred date (optional):",
                value=datetime.now() + timedelta(days=1),
            )
        with col3:
            preferred_location = st.text_input(
                "Preferred location (optional):", placeholder="e.g. Pune"
            )

        submit_button = st.form_submit_button("Get Assessment", use_container_width=True)

    if not submit_button:
        return

    if len(user_input.strip()) < 10:
        st.error("Please provide more details about your symptoms (at least 10 characters).")
        return

    with st.spinner("Analyzing your symptoms... This may take a moment."):
        request_data = {
            "user_input": user_input.strip(),
            "user_id": user_id or None,
            "preferred_date": preferred_date.strftime("%Y-%m-%d") if preferred_date else None,
            "preferred_location": preferred_location or None,
        }

        try:
            response = requests.post(
                f"{API_BASE_URL}/assess", json=request_data, timeout=REQUEST_TIMEOUT
            )
        except requests.exceptions.Timeout:
            st.error("Request timed out. The system might be under heavy load. Please try again.")
            return
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to the server. Please ensure the API is running.")
            return
        except requests.exceptions.RequestException as e:
            st.error(f"An unexpected error occurred: {e}")
            return

    if response.status_code != 200:
        try:
            detail = response.json().get("detail") or response.json().get("message")
        except Exception:
            detail = response.text
        st.error(f"Error ({response.status_code}): {detail or 'Unknown error'}")
        return

    result = response.json()
    st.success("✅ Assessment completed successfully!")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["📋 Symptoms", "👨‍⚕️ Doctors", "📅 Scheduling", "📝 Summary"]
    )
    with tab1:
        display_symptom_analysis(result.get("symptom_analysis", {}))
    with tab2:
        display_doctor_recommendations(result.get("doctor_recommendations", {}))
    with tab3:
        display_scheduling(result.get("scheduling_options", {}))
    with tab4:
        display_health_summary(result.get("health_summary", {}))

    st.markdown("---")
    st.download_button(
        label="📥 Download Full Assessment",
        data=json.dumps(result, indent=2),
        file_name=f"health_assessment_{result.get('request_id', 'result')}.json",
        mime="application/json",
    )


if __name__ == "__main__":
    main()  