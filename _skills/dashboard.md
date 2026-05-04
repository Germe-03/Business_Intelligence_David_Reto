# Skill: Dashboard (Streamlit)

## Zweck
Entscheidungsunterstützendes Dashboard mit Streamlit aufbauen und erweitern.

## Starten
```bash
streamlit run dashboard/app.py
```

## Seitenstruktur
```
dashboard/
├── app.py              # Hauptdatei (Navigation)
└── pages/
    ├── 1_overview.py       # KPIs & Gesamtübersicht
    ├── 2_routes.py         # Routen-Karte & Auslastung
    ├── 3_delays.py         # Verspätungsanalyse
    ├── 4_passengers.py     # Passagierherkunft & Segmente
    └── 5_prediction.py     # ML-Vorhersage-Interface
```

## Grundgerüst app.py
```python
import streamlit as st

st.set_page_config(page_title="Flughafen BI Dashboard", layout="wide")
st.title("Flughafen Zürich – Business Intelligence Dashboard")
st.sidebar.success("Seite auswählen")
```

## Wichtige Streamlit-Patterns

### Datenbankverbindung cachen
```python
@st.cache_resource
def get_engine():
    from sqlalchemy import create_engine
    return create_engine("mysql+pymysql://root:password@localhost/flughafendb_large")
```

### Abfragen cachen
```python
@st.cache_data(ttl=600)
def load_kpis():
    return pd.read_sql("SELECT COUNT(*) FROM flight", get_engine())
```

### Plotly-Chart einbinden
```python
import plotly.express as px
fig = px.bar(df, x="airlinename", y="revenue", title="Umsatz pro Airline")
st.plotly_chart(fig, use_container_width=True)
```

### Karte (Routen)
```python
fig = px.scatter_geo(df, lat="latitude", lon="longitude",
                     hover_name="city", size="bookings")
st.plotly_chart(fig, use_container_width=True)
```

## Design-Prinzipien
- KPIs immer oben als `st.metric()` Kacheln
- Filter (Airline, Zeitraum, Route) in `st.sidebar`
- Tabellen nur bei Bedarf expandierbar (`st.expander`)
- Mobile-Kompatibilität durch `layout="wide"`
