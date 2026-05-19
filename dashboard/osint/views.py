"""Render-Funktionen fuer die OSINT-Erweiterungen."""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st

try:
    import folium
    from folium.plugins import MarkerCluster
    from streamlit_folium import st_folium
except ModuleNotFoundError:
    folium = None
    MarkerCluster = None
    st_folium = None

from dashboard.bi.data_layer import ZRH_AIRPORT_ID, query_df
from dashboard.osint.opensky import (
    ZRH_BBOX,
    ZRH_LAT,
    ZRH_LON,
    fetch_states,
    summarise,
)


def _format_age(server_time: pd.Timestamp) -> str:
    if pd.isna(server_time):
        return "?"
    now = datetime.now(timezone.utc)
    delta = now - server_time.to_pydatetime()
    seconds = max(int(delta.total_seconds()), 0)
    if seconds < 60:
        return f"vor {seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"vor {minutes} min"
    return f"vor {minutes // 60} h"


# ---------------------------------------------------------------------------
# OpenSky Live
# ---------------------------------------------------------------------------
def render_opensky_live() -> None:
    st.title("Live-Flugverkehr rund um Zuerich")
    st.caption(
        "Quelle: OpenSky Network. Die Karte zeigt aktuelle Flugzeuge im"
        " gewaehlten Radius um ZRH."
    )
    if not _folium_available():
        return

    with st.sidebar:
        st.subheader("OpenSky Konfiguration")
        if st.button("Eingaben zuruecksetzen", use_container_width=True):
            for key in ("opensky_radius_km", "opensky_user", "opensky_pw"):
                st.session_state.pop(key, None)
            st.rerun()
        radius_km = st.slider(
            "Radius um ZRH (km)",
            50,
            500,
            200,
            25,
            key="opensky_radius_km",
        )
        username = st.text_input("OpenSky-Benutzername (optional)", key="opensky_user")
        password = st.text_input(
            "OpenSky-Passwort (optional)", type="password", key="opensky_pw"
        )

    bbox = _bbox_for_radius(radius_km)

    try:
        with st.spinner("Hole Flugzeug-Positionen ..."):
            df = fetch_states(
                bbox=bbox,
                username=username or None,
                password=password or None,
            )
    except Exception as exc:
        st.error(
            "OpenSky ist gerade nicht erreichbar oder lehnt die Anfrage ab. "
            "Bitte pruefe deine Zugangsdaten oder versuche es mit einem kleineren Radius erneut."
        )
        return

    stats = summarise(df)
    cols = st.columns(5)
    cols[0].metric("Flugzeuge im Radius", stats.total)
    cols[1].metric("In der Luft", stats.airborne)
    cols[2].metric("Am Boden", stats.on_ground)
    cols[3].metric("Laender", stats.countries)
    cols[4].metric("Durchschnittshoehe (ft)", f"{stats.avg_altitude_ft:,.0f}".replace(",", "'"))
    st.caption(
        f"Server-Zeit: {stats.fetched_at:%Y-%m-%d %H:%M:%S} UTC ({_format_age(stats.fetched_at)})"
    )

    if df.empty:
        st.info("Keine aktiven Flugzeuge im gewaehlten Radius.")
        return

    map_df = df.dropna(subset=["latitude", "longitude"]).copy()
    fmap = folium.Map(location=[ZRH_LAT, ZRH_LON], zoom_start=7,
                      tiles="CartoDB positron")
    folium.Marker(
        location=[ZRH_LAT, ZRH_LON],
        popup="Flughafen Zuerich (ZRH)",
        icon=folium.Icon(color="red", icon="plane", prefix="fa"),
    ).add_to(fmap)

    for row in map_df.itertuples(index=False):
        track = float(row.true_track_deg) if not pd.isna(row.true_track_deg) else 0.0
        altitude = float(row.altitude_ft) if not pd.isna(row.altitude_ft) else 0.0
        speed = float(row.velocity_kmh) if not pd.isna(row.velocity_kmh) else 0.0
        color = "#1565C0" if not row.on_ground else "#9E9E9E"
        aircraft_label = row.callsign or "Unbekanntes Flugzeug"
        popup_html = (
            f"<b>{aircraft_label}</b><br>"
            f"{row.origin_country}<br>"
            f"Hoehe: {altitude:,.0f} ft<br>"
            f"Geschwindigkeit: {speed:,.0f} km/h<br>"
            f"Kurs: {track:.0f} Grad"
        )
        folium.RegularPolygonMarker(
            location=[row.latitude, row.longitude],
            number_of_sides=3,
            rotation=track - 90,
            radius=6, fill_color=color, color=color, fill_opacity=0.9,
            popup=folium.Popup(popup_html, max_width=220),
        ).add_to(fmap)

    st_folium(fmap, height=560, use_container_width=True, returned_objects=[])

    st.markdown("##### Top-Laender")
    top_country = (
        df.groupby("origin_country").size().rename("Flugzeuge").reset_index()
        .sort_values("Flugzeuge", ascending=False).head(10)
    )
    st.dataframe(top_country, use_container_width=True, hide_index=True)


def _bbox_for_radius(radius_km: int) -> dict:
    # ZRH ist Mittelpunkt, 1 Grad lat ~= 111 km, 1 Grad lon ~ 75 km bei 47°
    dlat = radius_km / 111.0
    dlon = radius_km / 75.0
    return dict(
        lamin=ZRH_LAT - dlat,
        lamax=ZRH_LAT + dlat,
        lomin=ZRH_LON - dlon,
        lomax=ZRH_LON + dlon,
    )


# ---------------------------------------------------------------------------
# Folium - DB-Routen + optional OpenSky-Overlay
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _top_routes(min_flights: int, limit: int = 250) -> pd.DataFrame:
    """Top-Routen weltweit aus dem DB-Dump (Sommer 2015).

    Hinweis: Die Demo-DB hat keine ausgepraegte Hub-Struktur (jeder Airport
    hat in 3 Monaten ~50-360 Departures). Daher zeigen wir global die
    flugreichsten Routen statt nur ZRH.
    """
    return query_df(
        """
        SELECT
            af.iata AS from_iata, af.name AS from_name,
            gf.latitude AS from_lat, gf.longitude AS from_lon,
            ato.iata AS to_iata, ato.name AS to_name,
            gt.city AS to_city, gt.country AS to_country,
            gt.latitude AS to_lat, gt.longitude AS to_lon,
            COUNT(*) AS flights
        FROM flight AS f
        LEFT JOIN airport AS af ON af.airport_id = f.from_id
        LEFT JOIN airport_geo AS gf ON gf.airport_id = f.from_id
        LEFT JOIN airport AS ato ON ato.airport_id = f.to_id
        LEFT JOIN airport_geo AS gt ON gt.airport_id = f.to_id
        WHERE gf.latitude IS NOT NULL AND gt.latitude IS NOT NULL
        GROUP BY af.iata, af.name, gf.latitude, gf.longitude,
                 ato.iata, ato.name, gt.city, gt.country, gt.latitude, gt.longitude
        HAVING flights >= ?
        ORDER BY flights DESC
        LIMIT ?
        """,
        (min_flights, limit),
    )


def render_folium_routes() -> None:
    st.title("Routen-Karte mit Live-Overlay")
    st.caption(
        "Die Karte zeigt die flugreichsten Routen aus dem Sommer-2015-Datensatz"
        " und optional aktuelle Flugzeuge rund um ZRH."
    )
    if not _folium_available():
        return

    with st.sidebar:
        st.subheader("Filter")
        if st.button("Filter zuruecksetzen", use_container_width=True):
            for key in ("route_min_flights", "route_max_routes", "route_show_live"):
                st.session_state.pop(key, None)
            st.rerun()
        min_flights = st.slider(
            "Mindestanzahl Fluege pro Route",
            10,
            200,
            50,
            10,
            key="route_min_flights",
        )
        max_routes = st.slider(
            "Anzahl angezeigte Routen",
            25,
            500,
            150,
            25,
            key="route_max_routes",
        )
        show_live = st.toggle(
            "Live-Flugzeuge rund um ZRH anzeigen",
            value=True,
            key="route_show_live",
        )

    routes = _top_routes(min_flights, max_routes)
    fmap = folium.Map(location=[ZRH_LAT, ZRH_LON], zoom_start=3,
                      tiles="OpenStreetMap")

    db_layer = folium.FeatureGroup(name="DB-Routen (Sommer 2015)", show=True)
    cluster = MarkerCluster(name="Airports").add_to(db_layer)

    folium.Marker(
        location=[ZRH_LAT, ZRH_LON],
        popup="Flughafen Zuerich (ZRH)",
        icon=folium.Icon(color="red", icon="plane", prefix="fa"),
    ).add_to(db_layer)

    if routes.empty:
        st.warning("Keine Routen im Filter - reduziere die Min-Anzahl.")
    else:
        max_flights = int(routes["flights"].max() or 1)
        airports_seen: set[str] = set()
        for row in routes.itertuples(index=False):
            weight = 1 + 3 * (row.flights / max_flights)
            folium.PolyLine(
                locations=[[row.from_lat, row.from_lon],
                           [row.to_lat, row.to_lon]],
                color="#1565C0", weight=weight, opacity=0.45,
                tooltip=f"{row.from_iata} - {row.to_iata}: {int(row.flights)} Fluege",
            ).add_to(db_layer)
            for code, lat, lon, name, sub in [
                (row.from_iata, row.from_lat, row.from_lon, row.from_name, ""),
                (row.to_iata, row.to_lat, row.to_lon, row.to_name,
                 f"{row.to_city}, {row.to_country}" if row.to_city else ""),
            ]:
                key = f"{code}-{lat:.2f}-{lon:.2f}"
                if key in airports_seen:
                    continue
                airports_seen.add(key)
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=4, color="#0D47A1", fill=True,
                    fill_color="#1565C0", fill_opacity=0.8,
                    popup=folium.Popup(
                        f"<b>{code} - {name}</b><br>{sub}", max_width=240
                    ),
                ).add_to(cluster)

    db_layer.add_to(fmap)

    if show_live:
        live_layer = folium.FeatureGroup(name="OpenSky live", show=True)
        try:
            live = fetch_states()
            for row in live.dropna(subset=["latitude", "longitude"]).itertuples(index=False):
                folium.CircleMarker(
                    location=[row.latitude, row.longitude],
                    radius=3, color="#C62828", fill=True, fill_color="#C62828",
                    fill_opacity=0.9,
                    popup=f"{row.callsign or 'Unbekanntes Flugzeug'} ({row.origin_country})",
                ).add_to(live_layer)
        except Exception as exc:
            st.warning("OpenSky-Overlay ist gerade nicht verfuegbar. Die Routenkarte bleibt nutzbar.")
        live_layer.add_to(fmap)

    folium.LayerControl(position="topright", collapsed=False).add_to(fmap)
    st_folium(fmap, height=620, use_container_width=True, returned_objects=[])

    if not routes.empty:
        st.markdown(
            f"**{len(routes)} Routen** | Top: "
            f"{routes.iloc[0]['from_iata']} - {routes.iloc[0]['to_iata']} "
            f"({int(routes.iloc[0]['flights'])} Fluege)"
        )


# ---------------------------------------------------------------------------
# Kepler.gl
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _kepler_arcs(limit: int = 400) -> pd.DataFrame:
    return query_df(
        """
        SELECT
            af.iata AS from_iata,
            gf.latitude AS from_lat,
            gf.longitude AS from_lon,
            ato.iata AS to_iata,
            gt.latitude AS to_lat,
            gt.longitude AS to_lon,
            COUNT(*) AS flights
        FROM flight AS f
        LEFT JOIN airport AS af ON af.airport_id = f.from_id
        LEFT JOIN airport_geo AS gf ON gf.airport_id = f.from_id
        LEFT JOIN airport AS ato ON ato.airport_id = f.to_id
        LEFT JOIN airport_geo AS gt ON gt.airport_id = f.to_id
        WHERE f.from_id = ?
          AND gf.latitude IS NOT NULL
          AND gt.latitude IS NOT NULL
        GROUP BY from_iata, from_lat, from_lon, to_iata, to_lat, to_lon
        HAVING flights > 0
        ORDER BY flights DESC
        LIMIT ?
        """,
        (ZRH_AIRPORT_ID, limit),
    )


@st.cache_data(show_spinner=False)
def _kepler_heat() -> pd.DataFrame:
    """Buchungs-Heatmap-Punkte (Tag x Ziel-Flughafen)."""
    return query_df(
        """
        SELECT date_trunc('day', f.departure) AS ts,
               g.latitude AS lat,
               g.longitude AS lon,
               COUNT(b.booking_id) AS bookings
        FROM flight AS f
        LEFT JOIN airport_geo AS g ON g.airport_id = f.to_id
        LEFT JOIN booking AS b ON b.flight_id = f.flight_id
        WHERE f.from_id = ?
          AND g.latitude IS NOT NULL
        GROUP BY ts, lat, lon
        HAVING bookings > 0
        ORDER BY bookings DESC
        LIMIT 5000
        """,
        (ZRH_AIRPORT_ID,),
    )


def render_kepler_heatmap() -> None:
    st.title("ZRH-Routen und Buchungs-Heatmap")
    st.caption(
        "Interaktive Karte fuer Abfluege ab ZRH im Sommer 2015."
        " Layer und Zeitsteuerung sind im Kartenpanel verfuegbar."
    )

    try:
        from keplergl import KeplerGl
        from streamlit_keplergl import keplergl_static
    except Exception as exc:
        st.warning("Kepler.gl ist nicht verfuegbar. Es wird eine einfache Ersatzkarte angezeigt.")
        _render_pydeck_fallback()
        return

    arcs = _kepler_arcs()
    heat = _kepler_heat()

    if arcs.empty:
        st.info("Keine Routen verfuegbar.")
        return

    config = {
        "version": "v1",
        "config": {
            "visState": {
                "layers": [
                    {
                        "id": "arcs",
                        "type": "arc",
                        "config": {
                            "dataId": "routes",
                            "label": "ZRH Routen",
                            "color": [21, 101, 192],
                            "highlightColor": [255, 122, 89, 255],
                            "columns": {
                                "lat0": "from_lat", "lng0": "from_lon",
                                "lat1": "to_lat", "lng1": "to_lon",
                            },
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.6, "thickness": 2,
                                "sizeRange": [0, 8],
                                "targetColor": [198, 40, 40],
                            },
                        },
                        "visualChannels": {
                            "sizeField": {"name": "flights", "type": "integer"},
                            "sizeScale": "linear",
                        },
                    },
                    {
                        "id": "heat",
                        "type": "heatmap",
                        "config": {
                            "dataId": "heat",
                            "label": "Buchungs-Heatmap",
                            "columns": {"lat": "lat", "lng": "lon"},
                            "isVisible": True,
                            "visConfig": {"opacity": 0.7, "radius": 30},
                        },
                        "visualChannels": {
                            "weightField": {"name": "bookings", "type": "integer"},
                        },
                    },
                ]
            },
            "mapState": {
                "latitude": ZRH_LAT,
                "longitude": ZRH_LON,
                "zoom": 3.5,
                "pitch": 35,
                "bearing": 0,
            },
        },
    }

    map_obj = KeplerGl(height=620, config=config)
    map_obj.add_data(data=arcs, name="routes")
    if not heat.empty:
        map_obj.add_data(data=heat, name="heat")
    keplergl_static(map_obj, height=620)

    st.caption(
        f"{len(arcs)} Routen | {len(heat):,}".replace(",", "'")
        + " Heatmap-Punkte"
    )


def _render_pydeck_fallback() -> None:
    """Wird verwendet, wenn streamlit-keplergl nicht geladen werden kann."""
    import pydeck as pdk

    arcs = _kepler_arcs()
    if arcs.empty:
        st.info("Keine Daten verfuegbar.")
        return

    max_flights = int(arcs["flights"].max() or 1)
    arcs["weight"] = arcs["flights"] / max_flights

    arc_layer = pdk.Layer(
        "ArcLayer",
        data=arcs,
        get_source_position=["from_lon", "from_lat"],
        get_target_position=["to_lon", "to_lat"],
        get_width="weight * 6 + 1",
        get_source_color=[21, 101, 192],
        get_target_color=[198, 40, 40],
        pickable=True,
    )
    view = pdk.ViewState(latitude=ZRH_LAT, longitude=ZRH_LON, zoom=3, pitch=40)
    deck = pdk.Deck(layers=[arc_layer], initial_view_state=view,
                    map_style=None,
                    tooltip={"text": "ZRH - {to_iata}: {flights} Fluege"})
    st.pydeck_chart(deck)


def _folium_available() -> bool:
    if folium is not None and MarkerCluster is not None and st_folium is not None:
        return True
    st.error(
        "Die Kartenansicht kann nicht gestartet werden, weil Folium oder "
        "streamlit-folium in dieser Python-Umgebung fehlt."
    )
    st.info("Installiere die Projekt-Abhaengigkeiten und starte Streamlit danach neu.")
    st.code("pip install -r requirements.txt", language="bash")
    return False
