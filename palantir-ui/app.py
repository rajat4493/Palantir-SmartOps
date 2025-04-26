import streamlit as st
import requests
import pandas as pd

# Backend API URL
API_BASE_URL = "http://127.0.0.1:8000"  # Your FastAPI is running here

st.set_page_config(page_title="SmartOps AI - Manager Dashboard", layout="wide")

st.title("🧠 SmartOps AI Manager Dashboard")
st.markdown("---")

# Sidebar Navigation
page = st.sidebar.selectbox("Select Page", ["Team Overview", "Employee Timeline"])

# Fetch Nudges Data
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

# Fetch Timeline for a specific employee
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

# Page 1: Team Overview
if page == "Team Overview":
    st.header("👥 Team Attendance Insights")

    nudges = fetch_nudges()

    if nudges:
        df = pd.DataFrame(nudges)
        st.dataframe(df[["employee_id", "summary", "nudge_message", "severity"]])

# Page 2: Employee Timeline
elif page == "Employee Timeline":
    st.header("📈 Individual Employee Behavior Timeline")

    employee_id = st.text_input("Enter Employee ID (Example: EMP001)")

    if st.button("Fetch Timeline") and employee_id:
        timeline_data = fetch_timeline(employee_id)

        if timeline_data:
            st.subheader(f"Timeline for {timeline_data['employee_id']}")

            timeline_df = pd.DataFrame(timeline_data["timeline"])
            st.dataframe(timeline_df)

            if not timeline_df.empty:
                st.line_chart(timeline_df.set_index("date")["duration_hours"])
