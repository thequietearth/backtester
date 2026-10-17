"""Streamlit entry point. Run with: streamlit run app.py"""
import streamlit as st

st.set_page_config(page_title="Backtester", layout="wide")

st.title("Backtester")
st.write(
    "What if you had bought last year's best-performing S&P 500 stock every January "
    "since 1996? This app will answer that honestly, side by side with SPY."
)
st.info("Under construction. Progress and milestones are in PLAN.md.")
