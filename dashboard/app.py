import streamlit as st

from dashboard.runway_view import render_runway_recommendation_page


st.set_page_config(
    page_title="Runway Entscheidung",
    layout="wide",
)

render_runway_recommendation_page()
