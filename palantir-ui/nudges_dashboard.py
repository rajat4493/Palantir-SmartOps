import streamlit as st
import requests

st.set_page_config(page_title="SmartOps Dashboard", layout="wide")

st.title("📊 SmartOps Nudges Dashboard")

API_URL = "http://127.0.0.1:8000/nudges"

with st.spinner("Loading nudges..."):
    try:
        response = requests.get(API_URL)
        data = response.json()
        nudges = data.get("nudges", [])
    except Exception as e:
        st.error(f"Failed to load nudges: {e}")
        nudges = []

if not nudges:
    st.info("No nudges to show right now. Everything looks good ✅")
else:
    employee_ids = sorted(set(n["employee_id"] for n in nudges))
    selected_emp = st.selectbox("Select Employee", ["All"] + employee_ids)

    for nudge in nudges:
        if selected_emp != "All" and nudge["employee_id"] != selected_emp:
            continue

        severity_color = {
            "low": "#d4edda",
            "yellow": "#fff3cd",
            "medium": "#ffeeba",
            "high": "#f8d7da"
        }.get(nudge.get("severity", "low"), "#f0f0f0")

        with st.container():
            st.markdown(f"""
                <div style='background-color:{severity_color}; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;'>
                    <h4>👤 {nudge['employee_id']}</h4>
                    <b>Summary:</b> {nudge['summary']}<br>
                    <b>Insight:</b> {nudge['nudge_message']}<br>
                    <b>Severity:</b> <span style='color:darkred;'>{nudge['severity'].capitalize()}</span>
                </div>
            """, unsafe_allow_html=True)

