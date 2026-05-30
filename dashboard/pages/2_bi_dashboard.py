import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.bi.filters import filter_summary_caption, render_filters
from dashboard.bi.views import (
    render_analytics,
    render_operations,
    render_overview,
    render_revenue,
    render_weather,
)


st.set_page_config(
    page_title="BI Dashboard - Demo-Flugdaten",
    layout="wide",
)

st.title("BI-Dashboard")
st.caption(
    "Analyse von Flugbetrieb, Buchungen, Umsatz und Wetter auf Basis einer"
    " öffentlichen Demo-Flugdatenbank (rund 13'500 Flughäfen weltweit, nicht"
    " Zürich-spezifisch). Links unter 'Datenquelle' auf Abflüge ab Zürich"
    " einschränkbar. Filter wirken auf alle Tabs (ausser Wetter, das nur auf"
    " Datum reagiert)."
)

filt = render_filters()
st.markdown(f"**Aktive Filter:** {filter_summary_caption(filt)}")

overview_tab, operations_tab, revenue_tab, weather_tab, analytics_tab = st.tabs(
    [
        "Übersicht",
        "Betrieb",
        "Umsatz",
        "Wetter",
        "Analyse",
    ]
)

with overview_tab:
    render_overview(filt)

with operations_tab:
    render_operations(filt)

with revenue_tab:
    render_revenue(filt)

with weather_tab:
    render_weather(filt)

with analytics_tab:
    render_analytics(filt)
