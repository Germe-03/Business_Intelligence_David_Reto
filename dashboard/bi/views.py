"""Render-Funktionen fuer die fuenf Tabs des BI-Dashboards."""
from __future__ import annotations

import math

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.bi.data_layer import (
    ZRH_AIRPORT_ID,
    airports_lookup,
    query_df,
)
from dashboard.bi.filters import BIFilter


_BASE_FLIGHTS_CTE = """
WITH base_flights AS (
    SELECT
        f.flight_id,
        f.flightno,
        f.from_id,
        f.to_id,
        f.departure,
        f.arrival,
        f.airline_id,
        f.airplane_id,
        p.capacity,
        p.type_id,
        t.identifier AS aircraft_type,
        a.airlinename,
        a.iata AS airline_iata
    FROM flight AS f
    LEFT JOIN airplane AS p USING (airplane_id)
    LEFT JOIN airplane_type AS t USING (type_id)
    LEFT JOIN airline AS a ON a.airline_id = f.airline_id
    WHERE {where}
)
"""


def _flights_cte(filt: BIFilter) -> tuple[str, list]:
    where, params = filt.flight_where_clause()
    return _BASE_FLIGHTS_CTE.format(where=where), params


# ---------------------------------------------------------------------------
# Tab 1 - Overview
# ---------------------------------------------------------------------------
def render_overview(filt: BIFilter) -> None:
    st.subheader("Management-Uebersicht")
    st.caption(
        "Schneller Ueberblick fuer Management. KPIs beziehen sich auf den oben"
        " gesetzten Filter."
    )

    cte, params = _flights_cte(filt)

    kpi_flights = query_df(
        cte + "SELECT COUNT(*) AS n FROM base_flights",
        tuple(params),
    )
    n_flights = int(kpi_flights["n"].iloc[0])

    bookings_df = query_df(
        cte
        + """
        SELECT
            COUNT(*) AS bookings,
            SUM(b.price) AS revenue,
            AVG(b.price) AS avg_price,
            COUNT(DISTINCT b.flight_id) AS booked_flights
        FROM booking AS b
        WHERE b.flight_id IN (SELECT flight_id FROM base_flights)
        """,
        tuple(params),
    )
    bookings = int(bookings_df["bookings"].iloc[0])
    revenue = float(bookings_df["revenue"].iloc[0] or 0)
    avg_price = float(bookings_df["avg_price"].iloc[0] or 0)

    load_df = query_df(
        cte
        + """
        SELECT AVG(load_factor) AS avg_lf, AVG(bookings_per_flight) AS avg_bpf
        FROM (
            SELECT
                bf.flight_id,
                LEAST(COUNT(b.booking_id) * 100.0 / NULLIF(bf.capacity, 0), 100) AS load_factor,
                COUNT(b.booking_id) AS bookings_per_flight
            FROM base_flights AS bf
            LEFT JOIN booking AS b ON b.flight_id = bf.flight_id
            GROUP BY bf.flight_id, bf.capacity
        )
        """,
        tuple(params),
    )
    avg_lf = float(load_df["avg_lf"].iloc[0] or 0)
    avg_bpf = float(load_df["avg_bpf"].iloc[0] or 0)

    cols = st.columns(5)
    cols[0].metric("Fluege", f"{n_flights:,}".replace(",", "'"))
    cols[1].metric("Buchungen", f"{bookings:,}".replace(",", "'"))
    cols[2].metric("Umsatz", f"CHF {revenue/1e6:,.2f} Mio".replace(",", "'"))
    cols[3].metric("Ticketpreis im Schnitt", f"CHF {avg_price:,.2f}".replace(",", "'"))
    cols[4].metric("Auslastung im Schnitt", f"{avg_lf:.1f} %")

    st.caption(f"Buchungen pro Flug im Schnitt: {avg_bpf:.1f}")

    st.markdown("##### Fluege pro Tag")
    trend = query_df(
        cte
        + """
        SELECT date_trunc('day', departure)::DATE AS day,
               COUNT(*) AS flights,
               COUNT(DISTINCT airline_id) AS airlines
        FROM base_flights
        GROUP BY day
        ORDER BY day
        """,
        tuple(params),
    )
    if trend.empty:
        st.info("Keine Daten im gewaehlten Filter.")
        return
    fig = px.area(
        trend, x="day", y="flights",
        labels={"day": "Datum", "flights": "Anzahl Fluege"},
        color_discrete_sequence=["#2E7D32"],
    )
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, use_container_width=True)

    bookings_trend = query_df(
        cte
        + """
        SELECT date_trunc('day', f.departure)::DATE AS day,
               COUNT(b.booking_id) AS bookings,
               COALESCE(SUM(b.price), 0) AS revenue
        FROM base_flights AS f
        LEFT JOIN booking AS b ON b.flight_id = f.flight_id
        GROUP BY day
        ORDER BY day
        """,
        tuple(params),
    )
    if not bookings_trend.empty:
        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("##### Buchungen pro Tag")
            f1 = px.bar(
                bookings_trend,
                x="day",
                y="bookings",
                labels={"day": "Datum", "bookings": "Buchungen"},
                color_discrete_sequence=["#1565C0"],
            )
            f1.update_layout(height=300, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(f1, use_container_width=True)
        with col_r:
            st.markdown("##### Umsatz pro Tag (CHF)")
            f2 = px.line(
                bookings_trend,
                x="day",
                y="revenue",
                markers=True,
                labels={"day": "Datum", "revenue": "Umsatz (CHF)"},
                color_discrete_sequence=["#EF6C00"],
            )
            f2.update_layout(height=300, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(f2, use_container_width=True)


# ---------------------------------------------------------------------------
# Tab 2 - Operations
# ---------------------------------------------------------------------------
def render_operations(filt: BIFilter) -> None:
    st.subheader("Flugbetrieb")
    st.caption("Wo gibt es Verkehrsspitzen, welche Routen sind dominant?")

    cte, params = _flights_cte(filt)

    top_dest = query_df(
        cte
        + """
        SELECT a.iata, a.name AS airport,
               g.country, COUNT(*) AS flights
        FROM base_flights AS bf
        LEFT JOIN airport AS a ON a.airport_id = bf.to_id
        LEFT JOIN airport_geo AS g ON g.airport_id = bf.to_id
        GROUP BY a.iata, a.name, g.country
        ORDER BY flights DESC
        LIMIT 15
        """,
        tuple(params),
    )

    heatmap = query_df(
        cte
        + """
        SELECT EXTRACT(dow FROM departure)::INTEGER AS dow,
               EXTRACT(hour FROM departure)::INTEGER AS hour,
               COUNT(*) AS flights
        FROM base_flights
        GROUP BY dow, hour
        ORDER BY dow, hour
        """,
        tuple(params),
    )

    left, right = st.columns([3, 2])
    with left:
        st.markdown("##### Top 15 Destinationen (Fluege)")
        if top_dest.empty:
            st.info("Keine Daten.")
        else:
            fig = px.bar(
                top_dest, x="flights", y="iata", orientation="h",
                hover_data=["airport", "country"],
                color="flights", color_continuous_scale="Greens",
            )
            fig.update_layout(height=480, yaxis={"categoryorder": "total ascending"},
                              margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("##### Heatmap Wochentag x Stunde")
        if heatmap.empty:
            st.info("Keine Daten.")
        else:
            days = ["So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"]
            heatmap["weekday"] = heatmap["dow"].map(lambda d: days[int(d) % 7])
            pivot = heatmap.pivot(index="weekday", columns="hour", values="flights").fillna(0)
            pivot = pivot.reindex(["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"])
            fig = px.imshow(
                pivot, color_continuous_scale="Blues", aspect="auto",
                labels=dict(color="Fluege"),
            )
            fig.update_layout(height=480, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("##### Route-Karte (Top 25 Destinationen ab Auswahl)")
    geo = query_df(
        cte
        + """
        SELECT a.iata, a.name, g.city, g.country, g.latitude, g.longitude,
               COUNT(*) AS flights,
               (SELECT g0.latitude FROM airport_geo g0 WHERE g0.airport_id = bf.from_id LIMIT 1) AS from_lat,
               (SELECT g0.longitude FROM airport_geo g0 WHERE g0.airport_id = bf.from_id LIMIT 1) AS from_lon
        FROM base_flights AS bf
        LEFT JOIN airport AS a ON a.airport_id = bf.to_id
        LEFT JOIN airport_geo AS g ON g.airport_id = bf.to_id
        WHERE g.latitude IS NOT NULL AND g.longitude IS NOT NULL
        GROUP BY a.iata, a.name, g.city, g.country, g.latitude, g.longitude, bf.from_id
        ORDER BY flights DESC
        LIMIT 25
        """,
        tuple(params),
    )
    if geo.empty:
        st.info("Keine geocodierten Destinationen im Filter.")
    else:
        fig = go.Figure()
        for _, row in geo.iterrows():
            fig.add_trace(go.Scattergeo(
                lon=[row["from_lon"], row["longitude"]],
                lat=[row["from_lat"], row["latitude"]],
                mode="lines",
                line=dict(width=1 + math.log10(max(row["flights"], 1)), color="#1565C0"),
                opacity=0.5, showlegend=False, hoverinfo="skip",
            ))
        fig.add_trace(go.Scattergeo(
            lon=geo["longitude"], lat=geo["latitude"],
            text=geo.apply(lambda r: f"{r['iata']} - {r['city']} ({int(r['flights'])} Fluege)", axis=1),
            mode="markers",
            marker=dict(
                size=8 + (geo["flights"] / geo["flights"].max() * 20),
                color="#C62828", line=dict(width=0.5, color="white"),
            ),
            name="Destinationen",
        ))
        fig.update_layout(
            geo=dict(showland=True, landcolor="#F5F5F5",
                     showocean=True, oceancolor="#E3F2FD",
                     projection_type="natural earth"),
            height=520, margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Tab 3 - Revenue & Bookings
# ---------------------------------------------------------------------------
def render_revenue(filt: BIFilter) -> None:
    st.subheader("Buchungen & Umsatz")
    st.caption("Wer bringt das Geld, woher kommen die Passagiere?")

    cte, params = _flights_cte(filt)

    rev_by_airline = query_df(
        cte
        + """
        SELECT bf.airlinename AS airline, bf.airline_iata AS iata,
               COUNT(b.booking_id) AS bookings,
               COALESCE(SUM(b.price), 0) AS revenue,
               COALESCE(AVG(b.price), 0) AS avg_price
        FROM base_flights AS bf
        LEFT JOIN booking AS b ON b.flight_id = bf.flight_id
        GROUP BY airline, iata
        ORDER BY revenue DESC
        LIMIT 15
        """,
        tuple(params),
    )

    left, right = st.columns(2)
    with left:
        st.markdown("##### Top 15 Airlines nach Umsatz")
        if rev_by_airline.empty:
            st.info("Keine Daten.")
        else:
            fig = px.bar(rev_by_airline, x="revenue", y="iata", orientation="h",
                         hover_data=["airline", "bookings", "avg_price"],
                         color="revenue", color_continuous_scale="Oranges")
            fig.update_layout(height=420, yaxis={"categoryorder": "total ascending"},
                              margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("##### Top 15 Routen nach Umsatz")
        rev_by_route = query_df(
            cte
            + """
            SELECT a.iata AS dest, COUNT(b.booking_id) AS bookings,
                   COALESCE(SUM(b.price), 0) AS revenue
            FROM base_flights AS bf
            LEFT JOIN booking AS b ON b.flight_id = bf.flight_id
            LEFT JOIN airport AS a ON a.airport_id = bf.to_id
            GROUP BY dest
            ORDER BY revenue DESC
            LIMIT 15
            """,
            tuple(params),
        )
        if rev_by_route.empty:
            st.info("Keine Daten.")
        else:
            fig = px.bar(rev_by_route, x="dest", y="revenue",
                         color="bookings", color_continuous_scale="Blues")
            fig.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("##### Passenger-Demografie")

    demo = query_df(
        cte
        + """
        SELECT pd.country,
               COUNT(*) AS bookings,
               COALESCE(AVG(EXTRACT(YEAR FROM AGE(CAST(bf.departure AS DATE), pd.birthdate))), 0) AS avg_age,
               SUM(CASE WHEN pd.sex = 'm' THEN 1 ELSE 0 END) AS male,
               SUM(CASE WHEN pd.sex = 'f' THEN 1 ELSE 0 END) AS female,
               SUM(CASE WHEN pd.sex IS NULL OR pd.sex NOT IN ('m','f') THEN 1 ELSE 0 END) AS other
        FROM base_flights AS bf
        JOIN booking AS b ON b.flight_id = bf.flight_id
        JOIN passengerdetails AS pd ON pd.passenger_id = b.passenger_id
        GROUP BY pd.country
        ORDER BY bookings DESC
        LIMIT 20
        """,
        tuple(params),
    )
    if demo.empty:
        st.info("Keine Passenger-Daten im Filter.")
        return

    c1, c2 = st.columns([2, 1])
    with c1:
        fig = px.bar(demo, x="bookings", y="country", orientation="h",
                     hover_data=["avg_age"], color="avg_age",
                     color_continuous_scale="Viridis",
                     labels={"avg_age": "Ø Alter"})
        fig.update_layout(height=520, yaxis={"categoryorder": "total ascending"},
                          margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        gender_totals = pd.DataFrame({
            "Geschlecht": ["Maennlich", "Weiblich", "Sonstige/Unbekannt"],
            "Buchungen": [int(demo["male"].sum()), int(demo["female"].sum()), int(demo["other"].sum())],
        })
        fig = px.pie(gender_totals, names="Geschlecht", values="Buchungen",
                     color_discrete_sequence=["#1565C0", "#C62828", "#9E9E9E"], hole=0.4)
        fig.update_layout(height=520, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Tab 4 - Weather & Runway-Recommendation
# ---------------------------------------------------------------------------
def render_weather(filt: BIFilter) -> None:
    st.subheader("Wetter & Runway-Empfehlung")
    st.caption(
        "Wetterhistorie aus weatherdata. Fuer die operative Pisten-Empfehlung"
        " bitte die Seite 'Runway Empfehlung' nutzen."
    )

    weather = query_df(
        """
        SELECT
            weather,
            COUNT(*) AS observations,
            ROUND(AVG(temp), 1) AS avg_temp,
            ROUND(AVG(wind), 1) AS avg_wind,
            ROUND(AVG(humidity), 1) AS avg_humidity
        FROM weatherdata
        WHERE log_date BETWEEN ? AND ?
        GROUP BY weather
        ORDER BY observations DESC
        """,
        (filt.date_from, filt.date_to),
    )
    wind_rose = query_df(
        """
        SELECT
            CAST(FLOOR(winddirection / 22.5) AS INTEGER) AS sector_idx,
            CASE
                WHEN wind < 10 THEN '<10 km/h'
                WHEN wind < 20 THEN '10-20 km/h'
                WHEN wind < 30 THEN '20-30 km/h'
                WHEN wind < 40 THEN '30-40 km/h'
                ELSE '>=40 km/h'
            END AS speed_bucket,
            COUNT(*) AS observations
        FROM weatherdata
        WHERE log_date BETWEEN ? AND ?
        GROUP BY sector_idx, speed_bucket
        ORDER BY sector_idx, speed_bucket
        """,
        (filt.date_from, filt.date_to),
    )

    cols = st.columns(2)
    with cols[0]:
        st.markdown("##### Wetterlagen-Haeufigkeit")
        if weather.empty:
            st.info("Keine Wetterdaten im Datumsbereich.")
        else:
            weather_display = weather.copy()
            weather_display["weather"] = weather_display["weather"].fillna("Keine Angabe")
            fig = px.bar(weather_display, x="weather", y="observations",
                         hover_data=["avg_temp", "avg_wind", "avg_humidity"],
                         labels={
                             "weather": "Wetterlage",
                             "observations": "Beobachtungen",
                             "avg_temp": "Temperatur im Schnitt (Grad C)",
                             "avg_wind": "Wind im Schnitt (km/h)",
                             "avg_humidity": "Luftfeuchtigkeit im Schnitt (%)",
                         },
                         color="observations", color_continuous_scale="Cividis")
            fig.update_layout(height=380, margin=dict(l=10, r=10, t=20, b=10),
                              xaxis_tickangle=-30)
            st.plotly_chart(fig, use_container_width=True)

    with cols[1]:
        st.markdown("##### Windrose")
        if wind_rose.empty:
            st.info("Keine Winddaten.")
        else:
            directions = [
                "N", "NNO", "NO", "ONO", "O", "OSO", "SO", "SSO",
                "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
            ]
            wind_rose["direction"] = wind_rose["sector_idx"].map(
                lambda i: directions[int(i) % 16]
            )
            fig = px.bar_polar(
                wind_rose, r="observations", theta="direction",
                color="speed_bucket",
                color_discrete_map={
                    "<10 km/h": "#A5D6A7",
                    "10-20 km/h": "#66BB6A",
                    "20-30 km/h": "#43A047",
                    "30-40 km/h": "#2E7D32",
                    ">=40 km/h": "#1B5E20",
                },
            )
            fig.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=10),
                              legend_title="Wind")
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("##### Temperatur / Wind Trend (Tagesmittel)")
    daily = query_df(
        """
        SELECT log_date AS day,
               ROUND(AVG(temp), 1) AS temp_c,
               ROUND(AVG(wind), 1) AS wind_kmh,
               ROUND(AVG(humidity), 1) AS humidity_pct
        FROM weatherdata
        WHERE log_date BETWEEN ? AND ?
        GROUP BY day
        ORDER BY day
        """,
        (filt.date_from, filt.date_to),
    )
    if daily.empty:
        st.info("Keine Tagesmittel verfuegbar.")
    else:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=daily["day"], y=daily["temp_c"],
                                 name="Temperatur (Grad C)", line=dict(color="#EF6C00")))
        fig.add_trace(go.Scatter(x=daily["day"], y=daily["wind_kmh"],
                                 name="Wind (km/h)", yaxis="y2",
                                 line=dict(color="#1565C0")))
        fig.update_layout(
            height=360, margin=dict(l=10, r=10, t=20, b=10),
            yaxis=dict(title="Temperatur (Grad C)"),
            yaxis2=dict(title="Wind (km/h)", overlaying="y", side="right"),
            xaxis=dict(title="Datum"),
            legend=dict(orientation="h", y=-0.2),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.info(
        "Fuer einen konkreten Vorschlag pro Wind/Wetter-Kombination und Flugzeugtyp"
        " den Seitenmenuepunkt **Runway Empfehlung** oeffnen."
    )


# ---------------------------------------------------------------------------
# Tab 5 - Analytics & Drill-Down
# ---------------------------------------------------------------------------
def render_analytics(filt: BIFilter) -> None:
    st.subheader("Analyse & Drill-down")
    st.caption("Auslastung nach Flugzeugtyp, Saisonalitaet, Flotten-Treemap.")

    cte, params = _flights_cte(filt)

    cte_analytics = cte.rstrip().rstrip(")") + """),
        flight_load AS (
            SELECT bf.flight_id, bf.aircraft_type, bf.capacity,
                   COUNT(b.booking_id) AS bookings_per_flight
            FROM base_flights AS bf
            LEFT JOIN booking AS b ON b.flight_id = bf.flight_id
            GROUP BY bf.flight_id, bf.aircraft_type, bf.capacity
        )
        """
    type_lf = query_df(
        cte_analytics
        + """
        SELECT COALESCE(aircraft_type, 'Unbekannt') AS aircraft_type,
               COUNT(*) AS flights,
               ROUND(AVG(LEAST(bookings_per_flight * 100.0 / NULLIF(capacity, 0), 100)), 1) AS avg_load,
               ROUND(MEDIAN(LEAST(bookings_per_flight * 100.0 / NULLIF(capacity, 0), 100)), 1) AS median_load
        FROM flight_load
        GROUP BY aircraft_type
        HAVING flights > 50
        ORDER BY avg_load DESC
        LIMIT 25
        """,
        tuple(params),
    )

    fleet = query_df(
        """
        SELECT t.identifier AS aircraft_type,
               a.airlinename AS airline,
               COUNT(*) AS count,
               AVG(p.capacity) AS avg_capacity
        FROM airplane AS p
        LEFT JOIN airplane_type AS t USING (type_id)
        LEFT JOIN airline AS a USING (airline_id)
        GROUP BY aircraft_type, airline
        HAVING count > 0
        ORDER BY count DESC
        LIMIT 200
        """
    )

    left, right = st.columns(2)
    with left:
        st.markdown("##### Auslastung nach Flugzeugtyp")
        if type_lf.empty:
            st.info("Keine Daten.")
        else:
            fig = px.bar(type_lf, x="aircraft_type", y="avg_load",
                         hover_data=["flights", "median_load"],
                         color="avg_load", color_continuous_scale="RdYlGn")
            fig.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=10),
                              xaxis_tickangle=-30,
                              yaxis_title="Auslastung im Schnitt (%)")
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("##### Flotten-Treemap (alle Airlines)")
        if fleet.empty:
            st.info("Keine Daten.")
        else:
            fleet = fleet.fillna({"aircraft_type": "Unbekannt", "airline": "Unbekannt"})
            fig = px.treemap(fleet, path=["airline", "aircraft_type"], values="count",
                             color="avg_capacity", color_continuous_scale="Tealgrn",
                             hover_data=["count"])
            fig.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("##### Buchungen pro Wochentag x Stunde")
    weekday_heat = query_df(
        cte
        + """
        SELECT EXTRACT(dow FROM bf.departure)::INTEGER AS dow,
               EXTRACT(hour FROM bf.departure)::INTEGER AS hour,
               COUNT(b.booking_id) AS bookings
        FROM base_flights AS bf
        LEFT JOIN booking AS b ON b.flight_id = bf.flight_id
        GROUP BY dow, hour
        ORDER BY dow, hour
        """,
        tuple(params),
    )
    if weekday_heat.empty:
        st.info("Keine Daten.")
    else:
        days = ["So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"]
        weekday_heat["weekday"] = weekday_heat["dow"].map(lambda d: days[int(d) % 7])
        pivot = weekday_heat.pivot(index="weekday", columns="hour", values="bookings").fillna(0)
        pivot = pivot.reindex(["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"])
        fig = px.imshow(pivot, color_continuous_scale="Plasma", aspect="auto",
                        labels=dict(color="Buchungen"))
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig, use_container_width=True)
