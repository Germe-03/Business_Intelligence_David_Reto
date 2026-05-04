# SKILL: Dashboard (Streamlit)

## Trigger
Wenn das Dashboard gebaut oder erweitert wird.

## Starten
```bash
streamlit run dashboard/app.py
```

## Seitenstruktur
```
dashboard/
├── app.py
└── pages/
    ├── 1_runway_recommendation.py   # Hauptseite: Wetter → Piste
    ├── 2_weather_analysis.py        # Wetterkorrelation mit Runways
    └── 3_flight_overview.py         # Flugübersicht & KPIs
```

## Patterns
```python
@st.cache_resource
def get_engine():
    from sqlalchemy import create_engine
    return create_engine("mysql+pymysql://root:password@localhost/flughafendb_large")

@st.cache_data(ttl=600)
def load_data(query): 
    return pd.read_sql(query, get_engine())
```

## Design
- KPIs oben als `st.metric()`
- Filter in `st.sidebar`
- Plotly für Charts (`st.plotly_chart(fig, use_container_width=True)`)
- `layout="wide"`
