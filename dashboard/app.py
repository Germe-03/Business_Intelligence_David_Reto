import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.runway_view import render_runway_recommendation_page


st.set_page_config(
    page_title="Runway Entscheidung",
    layout="wide",
)

render_runway_recommendation_page()
