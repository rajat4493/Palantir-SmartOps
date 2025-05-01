import streamlit as st
import requests
import pandas as pd
from fastapi import APIRouter

router = APIRouter()

API_BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="SmartOps AI - Manager Dashboard", layout="wide")

st.title("🧠 SmartOps AI Manager Dashboard")
st.markdown("---")

# Sidebar Navigation
page = st.sidebar.selectbox("Select Page", ["🏠 Overview", "📊 Nudges", "📈 Employee Timeline", "📅 Forecast Capacity"])

# --------------------------------------
# UTILITY: Fetch Nudges
def fetch_nudges():
    try:
        response = requests.get(f"{API_BASE_URL}/nudges")
        if response.status_code == 200:
            return response.json()["nudges"]
        else:
            st.error("Failed to fetch nudges.")
            return []
    except Exception as e:
        st.error(f"Error fetching nudges: {e}")
        return []

# UTILITY: Fetch Timeline
def fetch_timeline(employee_id):
    try:
        response = requests.get(f"{API_BASE_URL}/timeline/" + employee_id)
        if response.status_code == 200:
            return response.json()
        else:
            st.error("Failed to fetch timeline.")
            return None
    except Exception as e:
        st.error(f"Error fetching timeline: {e}")
        return None

# UTILITY: Fetch Forecast
def fetch_forecast(employees, country="IN", region="MH"):
    try:
        params = [("employees", emp) for emp in employees]
        params += [("country", country), ("region", region)]
        response = requests.get(f"{API_BASE_URL}/forecast", params=params)
        if response.status_code == 200:
            return response.json()["forecast"]
        else:
            st.error("Failed to fetch forecast.")
            return []
    except Exception as e:
        st.error(f"Error fetching forecast: {e}")
        return []

# --------------------------------------
# 🏠 Overview
if page == "🏠 Overview":
    st.header("🏠 SmartOps Overview")
    st.write("This page can show total check-ins, late % trends, etc.")

# --------------------------------------
# 📊 Nudges View
elif page == "📊 Nudges":
    st.header("📊 Behavior Nudges")

    nudges = fetch_nudges()

    if not nudges:
        st.info("No nudges right now.")
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

# --------------------------------------
# 📈 Timeline View
elif page == "📈 Employee Timeline":
    st.header("📈 Employee Timeline")

    employee_id = st.text_input("Enter Employee ID (e.g. EMP001)")

    if st.button("Fetch Timeline") and employee_id:
        timeline_data = fetch_timeline(employee_id)

        if timeline_data:
            st.subheader(f"Timeline for {timeline_data['employee_id']}")
            timeline_df = pd.DataFrame(timeline_data["timeline"])
            st.dataframe(timeline_df)

            if not timeline_df.empty:
                st.line_chart(timeline_df.set_index("date")["duration_hours"])

# --------------------------------------
# 📅 Forecast Capacity
elif page == "📅 Forecast Capacity":
    st.header("📅 Forecast Capacity Planner")

    employee_ids = st.text_input("Enter comma-separated employee IDs", value="EMP001,EMP002")
    country = st.text_input("Country Code (e.g. IN, US)", value="IN")
    region = st.text_input("Region Code (e.g. MH, CA)", value="MH")

    if st.button("Generate Forecast"):
        employee_list = [e.strip() for e in employee_ids.split(",") if e.strip()]
        forecast_data = fetch_forecast(employee_list, country, region)

        if forecast_data:
            forecast_df = pd.DataFrame(forecast_data)
            st.subheader("Forecast Results")
            st.dataframe(forecast_df)

            total_hours = forecast_df["forecast_hours"].sum()
            st.success(f"Total Team Forecasted Hours: {total_hours} hrs")
