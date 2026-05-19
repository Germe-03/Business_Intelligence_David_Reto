import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.osint.views import render_opensky_live


st.set_page_config(
    page_title="OSINT Live (OpenSky)",
    layout="wide",
)

render_opensky_live()
