import streamlit as st
import requests
import pandas as pd

API_BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="SmartOps AI - Manager Dashboard", layout="wide")

st.title("🧠 SmartOps AI Manager Dashboard")
st.markdown("---")

# Sidebar Navigation
page = st.sidebar.selectbox("Select Page", ["🏠 Overview", "📊 Nudges", "📈 Employee Timeline", "📅 Forecast Capacity", "🚨 Risk Radar"])

# --------------------------------------
# UTILITY FUNCTIONS
def fetch_nudges():
    try:
        response = requests.get(f"{API_BASE_URL}/nudges")
        if response.status_code == 200:
            return response.json()["nudges"]
    except Exception as e:
        st.error(f"Error fetching nudges: {e}")
    return []

def fetch_timeline(employee_id):
    try:
        response = requests.get(f"{API_BASE_URL}/timeline/" + employee_id)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Error fetching timeline: {e}")
    return None

def fetch_forecast(employees, country="IN", region="MH"):
    try:
        params = [("employees", emp) for emp in employees]
        params += [("country", country), ("region", region)]
        response = requests.get(f"{API_BASE_URL}/forecast", params=params)
        if response.status_code == 200:
            return response.json()["forecast"]
    except Exception as e:
        st.error(f"Error fetching forecast: {e}")
    return []

def fetch_risks(employees):
    try:
        params = [("employees", emp) for emp in employees]
        response = requests.get(f"{API_BASE_URL}/risk-radar", params=params)
        if response.status_code == 200:
            return response.json()["risks"]
    except Exception as e:
        st.error(f"Error fetching risks: {e}")
    return []

# --------------------------------------
# 🏠 Overview
if page == "🏠 Overview":
    st.header("🏠 SmartOps Overview")
    st.write("This page can show total check-ins, late % trends, etc.")

# 📊 Nudges
elif page == "📊 Nudges":
    st.header("📊 Behavior Nudges")
    nudges = fetch_nudges()
    if nudges:
        employee_ids = sorted(set(n["employee_id"] for n in nudges))
        selected_emp = st.selectbox("Select Employee", ["All"] + employee_ids)
        for nudge in nudges:
            if selected_emp != "All" and nudge["employee_id"] != selected_emp:
                continue
            st.markdown(f"""
                <div style='background:#fff3cd; padding:1rem; border-radius:8px;'>
                    <strong>👤 {nudge['employee_id']}</strong><br>
                    <b>{nudge['summary']}:</b> {nudge['nudge_message']}<br>
                    <b>Severity:</b> {nudge['severity']}
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No nudges found.")

# 📈 Timeline
elif page == "📈 Employee Timeline":
    st.header("📈 Employee Timeline")
    employee_id = st.text_input("Enter Employee ID (e.g. EMP001)")
    if st.button("Fetch Timeline") and employee_id:
        timeline_data = fetch_timeline(employee_id)
        if timeline_data:
            df = pd.DataFrame(timeline_data["timeline"])
            st.dataframe(df)
            if not df.empty:
                st.line_chart(df.set_index("date")["duration_hours"])

# 📅 Forecast
elif page == "📅 Forecast Capacity":
    st.header("📅 Forecast Capacity Planner")
    employee_ids = st.text_input("Enter comma-separated employee IDs", value="EMP001,EMP002")
    country = st.text_input("Country Code (e.g. IN, US)", value="IN")
    region = st.text_input("Region Code (e.g. MH, CA)", value="MH")
    if st.button("Generate Forecast"):
        employees = [e.strip() for e in employee_ids.split(",") if e.strip()]
        forecast = fetch_forecast(employees, country, region)
        if forecast:
            df = pd.DataFrame(forecast)
            st.dataframe(df)
            total = df["forecast_hours"].sum()
            st.success(f"Total Forecasted Hours: {total} hrs")

# 🚨 Risk Radar
elif page == "🚨 Risk Radar":
    st.header("🚨 Risk Radar - Behavioral Risk Detection")
    employee_ids = st.text_input("Enter comma-separated employee IDs to assess risk", value="EMP001,EMP002")
    if st.button("Run Risk Analysis"):
        employees = [e.strip() for e in employee_ids.split(",") if e.strip()]
        risks = fetch_risks(employees)
        if risks:
            for risk in risks:
                color = {
                    "low": "#e2f0d9",
                    "medium": "#fff3cd",
                    "high": "#f8d7da"
                }.get(risk.get("severity", "low"), "#f0f0f0")

                st.markdown(f"""
                    <div style='background:{color}; padding:1rem; border-radius:8px; margin-bottom: 1rem;'>
                        <strong>👤 {risk['employee_id']}</strong><br>
                        <b>Type:</b> {risk['risk_type']}<br>
                        <b>Signal:</b> {risk['signal']}<br>
                        <b>Recommendation:</b> {risk['recommendation']}<br>
                        <b>Severity:</b> {risk['severity'].capitalize()}
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No risks detected.")
