"""DuckDB-Layer ueber die zstd-komprimierten TSV-Dumps.

DuckDB liest .tsv.zst direkt (read_csv mit compression='zstd'), aggregiert
die 24 Booking-Chunks (~54 Mio Zeilen) on the fly und vermeidet das Laden
der Daten in Pandas. Conn ist Streamlit-cached und wird ueber alle Tabs
geteilt.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Mapping

import pandas as pd
import streamlit as st

try:
    import duckdb
except ModuleNotFoundError:
    duckdb = None


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "Data" / "flughafendb_large"
ZRH_AIRPORT_ID = 13591


_COLUMN_TYPES: Mapping[str, Mapping[str, str]] = {
    "airline": {
        "airline_id": "INTEGER",
        "iata": "VARCHAR",
        "airlinename": "VARCHAR",
        "base_airport": "INTEGER",
    },
    "airplane": {
        "airplane_id": "INTEGER",
        "capacity": "INTEGER",
        "type_id": "INTEGER",
        "airline_id": "INTEGER",
    },
    "airplane_type": {
        "type_id": "INTEGER",
        "identifier": "VARCHAR",
        "description": "VARCHAR",
    },
    "airport": {
        "airport_id": "INTEGER",
        "iata": "VARCHAR",
        "icao": "VARCHAR",
        "name": "VARCHAR",
    },
    "airport_geo": {
        "airport_id": "INTEGER",
        "name": "VARCHAR",
        "city": "VARCHAR",
        "country": "VARCHAR",
        "latitude": "DOUBLE",
        "longitude": "DOUBLE",
        "geolocation": "VARCHAR",
    },
    "airport_reachable": {
        "airport_id": "INTEGER",
        "hops": "INTEGER",
    },
    "booking": {
        "booking_id": "BIGINT",
        "flight_id": "INTEGER",
        "seat": "VARCHAR",
        "passenger_id": "INTEGER",
        "price": "DOUBLE",
    },
    "employee": {
        "employee_id": "INTEGER",
        "firstname": "VARCHAR",
        "lastname": "VARCHAR",
        "birthdate": "DATE",
        "sex": "VARCHAR",
        "street": "VARCHAR",
        "city": "VARCHAR",
        "zip": "INTEGER",
        "country": "VARCHAR",
        "emailaddress": "VARCHAR",
        "telephoneno": "VARCHAR",
        "salary": "DOUBLE",
        "department": "VARCHAR",
        "username": "VARCHAR",
        "password": "VARCHAR",
    },
    "flight": {
        "flight_id": "INTEGER",
        "flightno": "VARCHAR",
        "from_id": "INTEGER",
        "to_id": "INTEGER",
        "departure": "TIMESTAMP",
        "arrival": "TIMESTAMP",
        "airline_id": "INTEGER",
        "airplane_id": "INTEGER",
    },
    "flight_log": {
        "log_date": "TIMESTAMP",
        "user_name": "VARCHAR",
        "flight_id": "INTEGER",
        "flightno_old": "VARCHAR",
        "flightno_new": "VARCHAR",
        "from_old": "INTEGER",
        "to_old": "INTEGER",
        "from_new": "INTEGER",
        "to_new": "INTEGER",
        "departure_old": "TIMESTAMP",
        "arrival_old": "TIMESTAMP",
        "departure_new": "TIMESTAMP",
        "arrival_new": "TIMESTAMP",
        "airplane_id_old": "INTEGER",
        "airplane_id_new": "INTEGER",
        "airline_id_old": "INTEGER",
        "airline_id_new": "INTEGER",
        "comment": "VARCHAR",
    },
    "flightschedule": {
        "flightno": "VARCHAR",
        "from_id": "INTEGER",
        "to_id": "INTEGER",
        "departure": "TIME",
        "arrival": "TIME",
        "airline_id": "INTEGER",
        "monday": "TINYINT",
        "tuesday": "TINYINT",
        "wednesday": "TINYINT",
        "thursday": "TINYINT",
        "friday": "TINYINT",
        "saturday": "TINYINT",
        "sunday": "TINYINT",
    },
    "passenger": {
        "passenger_id": "INTEGER",
        "passportno": "VARCHAR",
        "firstname": "VARCHAR",
        "lastname": "VARCHAR",
    },
    "passengerdetails": {
        "passenger_id": "INTEGER",
        "birthdate": "DATE",
        "sex": "VARCHAR",
        "street": "VARCHAR",
        "city": "VARCHAR",
        "zip": "INTEGER",
        "country": "VARCHAR",
        "emailaddress": "VARCHAR",
        "telephoneno": "VARCHAR",
    },
    "weatherdata": {
        "log_date": "DATE",
        "obs_time": "TIME",
        "station": "INTEGER",
        "temp": "DOUBLE",
        "humidity": "DOUBLE",
        "airpressure": "DOUBLE",
        "wind": "DOUBLE",
        "weather": "VARCHAR",
        "winddirection": "INTEGER",
    },
}


_TABLE_GLOBS: Mapping[str, str] = {
    "airline": "flughafendb_large@airline@@0.tsv.zst",
    "airplane": "flughafendb_large@airplane@@0.tsv.zst",
    "airplane_type": "flughafendb_large@airplane_type@@0.tsv.zst",
    "airport": "flughafendb_large@airport@@0.tsv.zst",
    "airport_geo": "flughafendb_large@airport_geo.tsv.zst",
    "airport_reachable": "flughafendb_large@airport_reachable.tsv.zst",
    "booking": "flughafendb_large@booking@*.tsv.zst",
    "employee": "flughafendb_large@employee@@0.tsv.zst",
    "flight": "flughafendb_large@flight@@0.tsv.zst",
    "flight_log": "flughafendb_large@flight_log.tsv.zst",
    "flightschedule": "flughafendb_large@flightschedule@@0.tsv.zst",
    "passenger": "flughafendb_large@passenger@@0.tsv.zst",
    "passengerdetails": "flughafendb_large@passengerdetails@@0.tsv.zst",
    "weatherdata": "flughafendb_large@weatherdata@@0.tsv.zst",
}


def _columns_sql(table: str) -> str:
    parts = ", ".join(f"'{col}': '{ctype}'" for col, ctype in _COLUMN_TYPES[table].items())
    return "{" + parts + "}"


def _view_sql(table: str) -> str:
    pattern = (DATA_DIR / _TABLE_GLOBS[table]).as_posix()
    return (
        f"CREATE OR REPLACE VIEW {table} AS "
        f"SELECT * FROM read_csv("
        f"'{pattern}', delim='\\t', header=False, compression='zstd', "
        f"columns={_columns_sql(table)}, nullstr='\\N')"
    )


def _empty_view_sql(table: str) -> str:
    parts = ", ".join(
        f"CAST(NULL AS {ctype}) AS {col}" for col, ctype in _COLUMN_TYPES[table].items()
    )
    return f"CREATE OR REPLACE VIEW {table} AS SELECT {parts} WHERE 1=0"


def _table_has_data(table: str) -> bool:
    """Heuristik: zstd-Empty-Frames sind <= 20 Bytes; echte Datenfiles deutlich groesser."""
    pattern = _TABLE_GLOBS[table]
    matches = sorted(DATA_DIR.glob(pattern))
    return any(p.stat().st_size > 20 for p in matches)


@st.cache_resource(show_spinner="Initialisiere DuckDB-Views ...")
def get_connection() -> duckdb.DuckDBPyConnection:
    if duckdb is None:
        _show_missing_duckdb()
    con = duckdb.connect(database=":memory:")
    con.execute("PRAGMA threads=4")
    for table in _TABLE_GLOBS:
        if _table_has_data(table):
            try:
                con.execute(_view_sql(table))
            except duckdb.Error:
                con.execute(_empty_view_sql(table))
        else:
            con.execute(_empty_view_sql(table))
    return con


def schema_overview() -> dict[str, list[str]]:
    return {table: list(cols.keys()) for table, cols in _COLUMN_TYPES.items()}


@st.cache_data(show_spinner=False)
def query_df(sql: str, params: tuple = ()) -> pd.DataFrame:
    con = get_connection()
    if params:
        return con.execute(sql, params).df()
    return con.execute(sql).df()


@st.cache_data(show_spinner=False)
def flight_date_bounds() -> tuple[pd.Timestamp, pd.Timestamp]:
    df = query_df("SELECT MIN(departure) AS min_dt, MAX(departure) AS max_dt FROM flight")
    return pd.to_datetime(df["min_dt"].iloc[0]), pd.to_datetime(df["max_dt"].iloc[0])


@st.cache_data(show_spinner=False)
def airlines_lookup() -> pd.DataFrame:
    return query_df("SELECT airline_id, iata, airlinename FROM airline ORDER BY airlinename")


@st.cache_data(show_spinner=False)
def airports_lookup() -> pd.DataFrame:
    return query_df(
        """
        SELECT a.airport_id, a.iata, a.name,
               g.city, g.country, g.latitude, g.longitude
        FROM airport AS a
        LEFT JOIN airport_geo AS g USING (airport_id)
        ORDER BY a.iata NULLS LAST
        """
    )


@st.cache_data(show_spinner=False)
def aircraft_types_lookup() -> pd.DataFrame:
    return query_df(
        """
        SELECT t.type_id, t.identifier, COUNT(p.airplane_id) AS aircraft_count,
               AVG(p.capacity)::INTEGER AS avg_capacity
        FROM airplane_type AS t
        LEFT JOIN airplane AS p USING (type_id)
        GROUP BY t.type_id, t.identifier
        ORDER BY aircraft_count DESC
        """
    )


def project_root() -> Path:
    return PROJECT_ROOT


def _show_missing_duckdb() -> None:
    st.error(
        "Das BI-Datenmodul kann nicht gestartet werden, weil das Paket "
        "`duckdb` in dieser Python-Umgebung fehlt."
    )
    st.info("Installiere die Projekt-Abhaengigkeiten und starte Streamlit danach neu.")
    st.code("pip install -r requirements.txt", language="bash")
    st.stop()
