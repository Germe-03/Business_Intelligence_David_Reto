"""Sidebar-Filter fuer das BI-Dashboard.

Liefert ein BIFilter-Objekt + die SQL-WHERE-Fragmente, damit jede Tab-Funktion
die gleichen Selektionen anwenden kann.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd
import streamlit as st

from dashboard.bi.data_layer import (
    aircraft_types_lookup,
    airlines_lookup,
    airports_lookup,
    flight_date_bounds,
)


ALL_AIRLINES = "Alle Airlines"
ALL_AIRCRAFT = "Alle Flugzeugtypen"
ALL_DESTINATIONS = "Alle Destinationen"

FILTER_STATE_KEYS = (
    "bi_date_range",
    "bi_airline_choice",
    "bi_aircraft_choice",
    "bi_destination_choice",
)


@dataclass(frozen=True)
class BIFilter:
    date_from: date
    date_to: date
    airline_id: int | None
    airline_label: str
    aircraft_type_id: int | None
    aircraft_label: str
    destination_airport_id: int | None
    destination_label: str

    def flight_where_clause(self) -> tuple[str, list]:
        clauses = [
            "f.departure >= ?",
            "f.departure < ?",
        ]
        params: list = [
            pd.Timestamp(self.date_from).to_pydatetime(),
            (pd.Timestamp(self.date_to) + pd.Timedelta(days=1)).to_pydatetime(),
        ]
        if self.airline_id is not None:
            clauses.append("f.airline_id = ?")
            params.append(self.airline_id)
        if self.aircraft_type_id is not None:
            clauses.append("p.type_id = ?")
            params.append(self.aircraft_type_id)
        if self.destination_airport_id is not None:
            clauses.append("f.to_id = ?")
            params.append(self.destination_airport_id)
        return " AND ".join(clauses), params


def render_filters() -> BIFilter:
    min_dt, max_dt = flight_date_bounds()
    default_from = max(min_dt.date(), (max_dt - pd.Timedelta(days=30)).date())
    default_to = max_dt.date()

    st.sidebar.header("Filter")
    if st.sidebar.button("Filter zuruecksetzen", use_container_width=True):
        for key in FILTER_STATE_KEYS:
            st.session_state.pop(key, None)
        st.rerun()

    date_range = st.sidebar.date_input(
        "Datumsbereich (Abflug)",
        value=(default_from, default_to),
        min_value=min_dt.date(),
        max_value=max_dt.date(),
        format="DD.MM.YYYY",
        key="bi_date_range",
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        date_from, date_to = date_range
    else:
        date_from = default_from
        date_to = default_to

    airlines = airlines_lookup()
    airline_options = [ALL_AIRLINES] + [
        f"{row.iata or '??'} - {row.airlinename}" for row in airlines.itertuples(index=False)
    ]
    _ensure_choice("bi_airline_choice", airline_options, ALL_AIRLINES)
    airline_choice = st.sidebar.selectbox(
        "Airline",
        airline_options,
        index=airline_options.index(st.session_state.bi_airline_choice),
        key="bi_airline_choice",
    )
    if airline_choice == ALL_AIRLINES:
        airline_id = None
    else:
        airline_iata = airline_choice.split(" - ", 1)[0]
        row = airlines.loc[airlines["iata"].eq(airline_iata)].head(1)
        airline_id = int(row["airline_id"].iloc[0]) if not row.empty else None

    aircraft = aircraft_types_lookup()
    aircraft_options = [ALL_AIRCRAFT] + [
        f"{row.identifier or 'Unbekannt'} ({int(row.aircraft_count)} Flz.)"
        for row in aircraft.itertuples(index=False)
    ]
    _ensure_choice("bi_aircraft_choice", aircraft_options, ALL_AIRCRAFT)
    aircraft_choice = st.sidebar.selectbox(
        "Flugzeugtyp",
        aircraft_options,
        index=aircraft_options.index(st.session_state.bi_aircraft_choice),
        key="bi_aircraft_choice",
    )
    if aircraft_choice == ALL_AIRCRAFT:
        aircraft_type_id = None
        aircraft_label = ALL_AIRCRAFT
    else:
        identifier = aircraft_choice.split(" (", 1)[0]
        row = aircraft.loc[aircraft["identifier"].eq(identifier)].head(1)
        aircraft_type_id = int(row["type_id"].iloc[0]) if not row.empty else None
        aircraft_label = identifier

    airports = airports_lookup()
    destinations = airports.dropna(subset=["iata"]).head(200)
    dest_options = [ALL_DESTINATIONS] + [
        f"{row.iata} - {row['name']}" for _, row in destinations.iterrows()
    ]
    _ensure_choice("bi_destination_choice", dest_options, ALL_DESTINATIONS)
    dest_choice = st.sidebar.selectbox(
        "Ziel-Flughafen (Top 200)",
        dest_options,
        index=dest_options.index(st.session_state.bi_destination_choice),
        key="bi_destination_choice",
    )
    if dest_choice == ALL_DESTINATIONS:
        destination_airport_id = None
        destination_label = ALL_DESTINATIONS
    else:
        iata = dest_choice.split(" - ", 1)[0]
        row = destinations.loc[destinations["iata"].eq(iata)].head(1)
        destination_airport_id = int(row["airport_id"].iloc[0]) if not row.empty else None
        destination_label = dest_choice

    return BIFilter(
        date_from=date_from,
        date_to=date_to,
        airline_id=airline_id,
        airline_label=airline_choice,
        aircraft_type_id=aircraft_type_id,
        aircraft_label=aircraft_label,
        destination_airport_id=destination_airport_id,
        destination_label=destination_label,
    )


def filter_summary_caption(filt: BIFilter) -> str:
    parts = [
        f"{filt.date_from:%d.%m.%Y} - {filt.date_to:%d.%m.%Y}",
        filt.airline_label,
        filt.aircraft_label,
        filt.destination_label,
    ]
    return " | ".join(parts)


def _ensure_choice(key: str, options: list[str], default: str) -> None:
    if st.session_state.get(key) not in options:
        st.session_state[key] = default
