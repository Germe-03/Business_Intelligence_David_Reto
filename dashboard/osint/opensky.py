"""Minimaler OpenSky Network Client.

OpenSky bietet die /states/all Route gedrosselt anonym; mit Account-Login
gibt es laengere Cache-Zeiten und hoehere Limits. Wir cachen das Ergebnis
fuer 30 Sekunden via Streamlit, damit ein Tab-Wechsel keinen neuen Call
ausloest.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import requests
import streamlit as st


_BASE_URL = "https://opensky-network.org/api/states/all"

# Bounding-Box "rund um Zuerich" - knapp 200 km Radius
ZRH_BBOX = dict(lamin=46.0, lamax=48.6, lomin=6.5, lomax=11.0)
ZRH_LAT = 47.4647
ZRH_LON = 8.5492


_STATE_COLUMNS = [
    "icao24", "callsign", "origin_country", "time_position", "last_contact",
    "longitude", "latitude", "baro_altitude_m", "on_ground", "velocity_mps",
    "true_track_deg", "vertical_rate_mps", "sensors", "geo_altitude_m",
    "squawk", "spi", "position_source", "category",
]


@st.cache_data(ttl=30, show_spinner=False)
def fetch_states(bbox: dict | None = None,
                 username: str | None = None,
                 password: str | None = None) -> pd.DataFrame:
    """Holt aktive Flugzeuge aus dem Bounding-Box. Cache: 30 s."""
    params = bbox or ZRH_BBOX
    auth = (username, password) if username and password else None
    response = requests.get(_BASE_URL, params=params, auth=auth, timeout=15)
    response.raise_for_status()
    data = response.json()
    states = data.get("states") or []
    if not states:
        return pd.DataFrame(columns=_STATE_COLUMNS)
    df = pd.DataFrame(states, columns=_STATE_COLUMNS[: len(states[0])])
    if "callsign" in df.columns:
        df["callsign"] = df["callsign"].fillna("").str.strip()
    if "velocity_mps" in df.columns:
        df["velocity_kmh"] = (df["velocity_mps"].astype(float) * 3.6).round(0)
    if "baro_altitude_m" in df.columns:
        df["altitude_ft"] = (df["baro_altitude_m"].astype(float) * 3.28084).round(0)
    df["server_time"] = pd.to_datetime(data.get("time"), unit="s", utc=True)
    return df


@dataclass(frozen=True)
class FlightStats:
    total: int
    on_ground: int
    airborne: int
    countries: int
    avg_altitude_ft: float
    avg_speed_kmh: float
    fetched_at: pd.Timestamp


def summarise(df: pd.DataFrame) -> FlightStats:
    if df.empty:
        return FlightStats(0, 0, 0, 0, 0.0, 0.0, pd.Timestamp.now(tz="UTC"))
    on_ground = int(df["on_ground"].fillna(False).astype(bool).sum())
    return FlightStats(
        total=len(df),
        on_ground=on_ground,
        airborne=len(df) - on_ground,
        countries=int(df["origin_country"].nunique()),
        avg_altitude_ft=float(df["altitude_ft"].dropna().mean() or 0),
        avg_speed_kmh=float(df["velocity_kmh"].dropna().mean() or 0),
        fetched_at=df["server_time"].iloc[0] if "server_time" in df.columns else pd.Timestamp.now(tz="UTC"),
    )
