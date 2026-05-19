import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.bi.ai_agent import render_ai_agent


st.set_page_config(
    page_title="KI Analyst - Flughafen DB",
    layout="wide",
)

render_ai_agent()
