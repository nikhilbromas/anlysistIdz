"""
Restaurant Management ML + Visualization Dashboard.
Entry point:  streamlit run app.py
"""
import streamlit as st

st.set_page_config(
    page_title="Restaurant Management Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Restaurant Management Dashboard")
st.markdown(
    """
    **ML-based analytics for your restaurant POS data.**
    Use the sidebar to navigate:
    - **Dashboard** — Sales KPIs, trends, service-charge analysis, payment modes
    - **ML Insights** — Sales forecasting, ingredient demand prediction
    """
)

# Quick connection check
try:
    from db.connection import get_connection
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
    st.success("Connected to MSSQL database successfully.")
except Exception as e:
    st.error(f"Database connection failed: {e}")
    st.info("Check `.env` credentials and ODBC driver. The dashboard pages will show errors until the connection works.")
