from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.application.explain_runway_decision import RunwayDecisionContext
from src.application.operational_context import (
    BuildOperationalContext,
    LoadOperationalSelectionOptions,
    OperationalContext,
    OperationalSelectionOptions,
)
from src.domain.runway import SuitabilityStatus
from src.infrastructure.dump_operational_context import DumpOperationalContextRepository
from src.infrastructure.meteoswiss_weather import (
    LiveWeatherSnapshot,
    MeteoSwissWeatherError,
    fetch_live_weather,
)
from src.infrastructure.ollama_explainer import OllamaRunwayExplainer
from src.interfaces.runway_controller import (
    RunwayCandidateView,
    RunwayDecisionController,
    RunwayRecommendationView,
)


DEFAULT_INPUTS = {
    "wind_speed_kmh": 24,
    "gust_speed_kmh": 30,
    "wind_direction_deg": 280,
    "visibility_m": 8000,
    "temperature_c": 15,
    "departure_hour": 11,
    "detail_mode": "Details",
}

LIVE_WEATHER_STATION = "KLO"
LIVE_WEATHER_STATION_LABEL = "Flughafen Zuerich / Kloten"

STATUS_COLORS = {
    "Empfohlen": "#2E7D32",
    "Mit Einschraenkungen": "#EF6C00",
    "Nicht geeignet": "#C62828",
}


@st.cache_resource
def _controller() -> RunwayDecisionController:
    return RunwayDecisionController()


@st.cache_resource
def _operational_repository() -> DumpOperationalContextRepository:
    return DumpOperationalContextRepository()


@st.cache_resource
def _operational_context_use_case() -> BuildOperationalContext:
    return BuildOperationalContext(_operational_repository())


@st.cache_resource
def _selection_options_use_case() -> LoadOperationalSelectionOptions:
    return LoadOperationalSelectionOptions(_operational_repository())


@st.cache_data(ttl=600, show_spinner=False)
def _live_weather(station_code: str) -> LiveWeatherSnapshot:
    return fetch_live_weather(station_code)


def render_runway_recommendation_page() -> None:
    options = _selection_options_use_case().execute()
    _ensure_state(options)
    inputs = _render_sidebar(options)
    context = _load_operational_context(inputs)
    recommendation = _controller().recommend(**_decision_inputs(inputs, context))

    st.title("Runway-Entscheidung fuer Starts")
    st.caption("Entscheidungsunterstuetzung fuer ZRH. Nicht fuer operative Freigaben verwenden.")

    _render_decision(recommendation.best)
    _render_metrics(recommendation.best)
    _render_live_weather_details(inputs.get("live_weather_snapshot"))
    _render_ai_explanation(inputs=inputs, recommendation=recommendation, context=context)

    if st.session_state.detail_mode == "Details":
        left, right = st.columns([1, 1])
        with left:
            st.plotly_chart(
                _score_chart(recommendation),
                width="stretch",
                config={"displayModeBar": False},
            )
        with right:
            st.plotly_chart(
                _wind_direction_chart(
                    recommendation=recommendation,
                    wind_direction_deg=inputs["wind_direction_deg"],
                ),
                width="stretch",
                config={"displayModeBar": False},
            )
        _render_candidate_table(recommendation)
        _render_reasoning(recommendation.best)
        _render_operational_context(context)


def _ensure_state(options: OperationalSelectionOptions) -> None:
    st.session_state.setdefault(
        "aircraft_type_id",
        _default_aircraft_type_id(options),
    )
    st.session_state.setdefault("weather_condition", "__all__")
    st.session_state.setdefault("destination_airport_id", "__all__")
    st.session_state.setdefault("live_weather_loaded", False)
    st.session_state.setdefault("live_weather_loaded_station", None)
    for key, value in DEFAULT_INPUTS.items():
        st.session_state.setdefault(key, value)


def _render_sidebar(options: OperationalSelectionOptions) -> dict[str, object]:
    aircraft_labels = {option.value: option.label for option in options.aircraft_types}
    weather_labels = {option.value: option.label for option in options.weather_conditions}
    destination_labels = {option.value: option.label for option in options.destinations}

    with st.sidebar:
        st.header("Eingaben")
        live_snapshot = _render_live_weather_controls(weather_labels)
        st.selectbox(
            "Flugzeugtyp",
            options=list(aircraft_labels.keys()),
            format_func=aircraft_labels.__getitem__,
            key="aircraft_type_id",
        )
        st.slider(
            "Windgeschwindigkeit (km/h)",
            min_value=0,
            max_value=120,
            step=1,
            key="wind_speed_kmh",
        )
        st.slider(
            "Boeen (km/h)",
            min_value=0,
            max_value=150,
            step=1,
            key="gust_speed_kmh",
        )
        st.slider(
            "Windrichtung (Grad)",
            min_value=0,
            max_value=360,
            step=5,
            key="wind_direction_deg",
        )
        st.slider(
            "Sichtweite (m)",
            min_value=200,
            max_value=10000,
            step=100,
            key="visibility_m",
        )
        st.selectbox(
            "Wetterlage",
            options=list(weather_labels.keys()),
            format_func=weather_labels.__getitem__,
            key="weather_condition",
        )
        st.slider(
            "Temperatur (Grad C)",
            min_value=-30,
            max_value=45,
            step=1,
            key="temperature_c",
        )
        st.selectbox(
            "Destination",
            options=list(destination_labels.keys()),
            format_func=destination_labels.__getitem__,
            key="destination_airport_id",
        )
        st.slider(
            "Abflugstunde (lokale Zeit)",
            min_value=0,
            max_value=23,
            step=1,
            key="departure_hour",
        )
        st.radio(
            "Ansicht",
            options=["Kompakt", "Details"],
            horizontal=True,
            key="detail_mode",
        )
        if st.button("Zuruecksetzen", width="stretch"):
            st.session_state.aircraft_type_id = _default_aircraft_type_id(options)
            st.session_state.weather_condition = "__all__"
            st.session_state.destination_airport_id = "__all__"
            if live_snapshot is not None:
                _apply_live_weather(live_snapshot, weather_labels)
            else:
                for key, value in DEFAULT_INPUTS.items():
                    st.session_state[key] = value
            st.rerun()

    gust_speed = st.session_state.gust_speed_kmh
    return {
        "aircraft_type_id": _parse_optional_int(st.session_state.aircraft_type_id),
        "wind_speed_kmh": st.session_state.wind_speed_kmh,
        "gust_speed_kmh": gust_speed if gust_speed > st.session_state.wind_speed_kmh else None,
        "wind_direction_deg": st.session_state.wind_direction_deg,
        "visibility_m": st.session_state.visibility_m,
        "weather_condition": st.session_state.weather_condition,
        "temperature_c": st.session_state.temperature_c,
        "departure_hour": st.session_state.departure_hour,
        "destination_airport_id": _parse_optional_int(st.session_state.destination_airport_id),
        "live_weather_snapshot": live_snapshot,
    }


def _render_live_weather_controls(
    weather_labels: dict[str, str],
) -> LiveWeatherSnapshot | None:
    snapshot = _load_live_weather_snapshot()
    if snapshot is None:
        st.caption(f"Live-Wetter: {LIVE_WEATHER_STATION_LABEL} nicht verfuegbar.")
        return None

    if (
        not st.session_state.live_weather_loaded
        or st.session_state.live_weather_loaded_station != snapshot.station_code
    ):
        _apply_live_weather(snapshot, weather_labels)
        st.session_state.live_weather_loaded = True
        st.session_state.live_weather_loaded_station = snapshot.station_code

    measured = snapshot.measured_at_local.strftime("%d.%m.%Y %H:%M")
    st.caption(
        f"Live-Wetter: {LIVE_WEATHER_STATION_LABEL}, {measured} Lokalzeit. "
        "Messwerte sind unten vorbelegt; Sichtweite bleibt manuell, falls MeteoSchweiz "
        "keinen aktuellen Wert liefert."
    )

    if st.button("Livewerte aktualisieren", width="stretch"):
        _live_weather.clear()
        refreshed = _load_live_weather_snapshot()
        if refreshed is not None:
            _apply_live_weather(refreshed, weather_labels)
            st.session_state.live_weather_loaded = True
            st.session_state.live_weather_loaded_station = refreshed.station_code
        st.rerun()

    return snapshot


def _load_live_weather_snapshot() -> LiveWeatherSnapshot | None:
    try:
        return _live_weather(LIVE_WEATHER_STATION)
    except MeteoSwissWeatherError as exc:
        st.warning(
            f"Live-Wetter konnte nicht geladen werden: {exc} "
            "Die Eingaben bleiben manuell bearbeitbar."
        )
        return None


def _apply_live_weather(
    snapshot: LiveWeatherSnapshot,
    weather_labels: dict[str, str],
) -> None:
    st.session_state.wind_speed_kmh = _bounded_int(snapshot.wind_speed_kmh, 0, 120)
    if snapshot.gust_speed_kmh is not None:
        st.session_state.gust_speed_kmh = _bounded_int(snapshot.gust_speed_kmh, 0, 150)
    st.session_state.wind_direction_deg = _bounded_int(
        round(snapshot.wind_direction_deg / 5) * 5,
        0,
        360,
    )
    st.session_state.temperature_c = _bounded_int(snapshot.temperature_c, -30, 45)
    if snapshot.visibility_m is not None:
        st.session_state.visibility_m = _bounded_int(snapshot.visibility_m, 200, 10000)
    if (
        snapshot.derived_weather_condition is not None
        and snapshot.derived_weather_condition in weather_labels
    ):
        st.session_state.weather_condition = snapshot.derived_weather_condition
    elif st.session_state.weather_condition in {"Regen", "Schneefall", "Regen-Schneefall"}:
        st.session_state.weather_condition = "__all__"


def _bounded_int(value: float, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, int(round(value))))


def _load_operational_context(inputs: dict[str, object]) -> OperationalContext:
    with st.spinner("Lade Datenbank-Kontext..."):
        return _operational_context_use_case().execute(
            aircraft_type_id=inputs["aircraft_type_id"],
            weather_condition=str(inputs["weather_condition"]),
            wind_speed_kmh=float(inputs["wind_speed_kmh"]),
            wind_direction_deg=float(inputs["wind_direction_deg"]),
            departure_hour=int(inputs["departure_hour"]),
            destination_airport_id=inputs["destination_airport_id"],
        )


def _decision_inputs(
    inputs: dict[str, object],
    context: OperationalContext,
) -> dict[str, object]:
    return {
        "aircraft_category": context.aircraft.category,
        "wind_speed_kmh": inputs["wind_speed_kmh"],
        "gust_speed_kmh": inputs["gust_speed_kmh"],
        "wind_direction_deg": inputs["wind_direction_deg"],
        "visibility_m": inputs["visibility_m"],
        "precipitation": _precipitation_from_weather(str(inputs["weather_condition"])),
        "temperature_c": inputs["temperature_c"],
        "thunderstorm": _has_thunderstorm(str(inputs["weather_condition"])),
    }


def _render_decision(best: RunwayCandidateView) -> None:
    message = (
        f"Piste {best.runway_number} mit {best.confidence_percent}% Konfidenz "
        f"({best.status_label})"
    )
    if best.status == SuitabilityStatus.RECOMMENDED:
        st.success(message)
    elif best.status == SuitabilityStatus.CAUTION:
        st.warning(message)
    else:
        st.error(f"Keine geeignete Startbahn. Beste Option: {message}")


def _render_metrics(best: RunwayCandidateView) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Empfehlung", f"Piste {best.runway_number}", f"Score {best.score:.0f}")
    col2.metric("Gegenwind", f"{best.headwind_kmh:.0f} km/h")
    col3.metric("Seitenwind", f"{best.crosswind_kmh:.0f} km/h")
    col4.metric("Rueckenwind", f"{best.tailwind_kmh:.0f} km/h")


def _render_live_weather_details(snapshot: object) -> None:
    if not isinstance(snapshot, LiveWeatherSnapshot):
        return

    with st.expander("Live-Wetterdaten MeteoSchweiz", expanded=False):
        measured = snapshot.measured_at_local.strftime("%d.%m.%Y %H:%M")
        st.caption(
            f"{LIVE_WEATHER_STATION_LABEL}, Messzeit {measured} Lokalzeit. "
            "Quelle: MeteoSchweiz Open Data / STAC."
        )
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Luftfeuchte", _format_optional(snapshot.humidity_pct, "%"))
        col2.metric("Taupunkt", _format_optional(snapshot.dewpoint_c, " C"))
        col3.metric("QNH", _format_optional(snapshot.pressure_qnh_hpa, " hPa"))
        col4.metric("QFE", _format_optional(snapshot.pressure_qfe_hpa, " hPa"))

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Niederschlag 10 min", _format_optional(snapshot.precipitation_10min_mm, " mm"))
        col2.metric("Schneehoehe", _format_optional(snapshot.snow_depth_cm, " cm"))
        col3.metric("Sonne 10 min", _format_optional(snapshot.sunshine_10min_min, " min"))
        col4.metric("Globalstrahlung", _format_optional(snapshot.global_radiation_wm2, " W/m2"))

        col1, col2, col3 = st.columns(3)
        col1.metric("Windchill", _format_optional(snapshot.windchill_c, " C"))
        col2.metric("Foehnindex", _format_optional(snapshot.foehn_index, ""))
        col3.metric(
            "Bewoelkung visuell",
            _format_optional(snapshot.visual_cloud_cover_pct, "%"),
        )

        condition = snapshot.derived_weather_condition or "Keine besondere Wetterlage"
        visibility = (
            f"{snapshot.visibility_m} m"
            if snapshot.visibility_m is not None
            else "Nicht als aktueller KLO-Livewert verfuegbar"
        )
        st.caption(f"Abgeleitete Wetterlage: {condition}. Sichtweite: {visibility}.")
        if snapshot.visual_observation_note:
            st.info(snapshot.visual_observation_note)


def _render_ai_explanation(
    inputs: dict[str, object],
    recommendation: RunwayRecommendationView,
    context: OperationalContext,
) -> None:
    _inject_chat_styles()
    with st.popover(
        "Chat",
        icon=":material/chat:",
        help="Lokale KI-Erklaerung",
        width=420,
    ):
        st.markdown("**Lokale KI-Erklaerung**")
        st.caption("Nutzt automatisch das zuletzt aktualisierte lokale Ollama-Modell.")
        generate = st.button(
            "Erklaerung generieren",
            key="generate_ai_explanation",
            width="stretch",
        )

        if not generate:
            return

        decision_context = _build_decision_context(inputs, recommendation.best, context)
        explainer = OllamaRunwayExplainer()
        with st.spinner("Lokale KI formuliert die Begruendung..."):
            result = explainer.explain(decision_context)

        if result.error_message:
            st.warning(result.error_message)
        with st.chat_message("assistant"):
            st.write(result.text)
        st.caption(f"Quelle: {result.source}")


def _inject_chat_styles() -> None:
    st.markdown(
        """
        <style>
        .st-key-runway_chat_popover {
            position: fixed;
            right: 1.5rem;
            bottom: 1.5rem;
            z-index: 10000;
        }
        .st-key-runway_chat_popover button {
            width: 3.75rem;
            height: 3.75rem;
            border-radius: 999px;
            padding: 0;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.22);
        }
        .st-key-runway_chat_popover button p {
            display: none;
        }
        .st-key-runway_chat_popover button span {
            margin: 0;
            font-size: 1.7rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _build_decision_context(
    inputs: dict[str, object],
    best: RunwayCandidateView,
    context: OperationalContext,
) -> RunwayDecisionContext:
    return RunwayDecisionContext(
        runway_number=best.runway_number,
        status_label=best.status_label,
        confidence_percent=best.confidence_percent,
        aircraft_label=context.aircraft.aircraft_type,
        wind_speed_kmh=float(inputs["wind_speed_kmh"]),
        gust_speed_kmh=(
            float(inputs["gust_speed_kmh"])
            if inputs.get("gust_speed_kmh") is not None
            else None
        ),
        wind_direction_deg=float(inputs["wind_direction_deg"]),
        visibility_m=int(inputs["visibility_m"]),
        precipitation_label=context.weather.selected_weather,
        thunderstorm=_has_thunderstorm(str(inputs["weather_condition"])),
        headwind_kmh=best.headwind_kmh,
        crosswind_kmh=best.crosswind_kmh,
        tailwind_kmh=best.tailwind_kmh,
        limitations=best.limitations,
        rationale=best.rationale,
    )


def _score_chart(recommendation: RunwayRecommendationView) -> go.Figure:
    rows = [
        {
            "Piste": candidate.runway_number,
            "Score": candidate.score,
            "Status": candidate.status_label,
        }
        for candidate in recommendation.candidates
    ]
    fig = px.bar(
        pd.DataFrame(rows),
        x="Piste",
        y="Score",
        color="Status",
        color_discrete_map=STATUS_COLORS,
        range_y=[0, 100],
        text="Score",
        title="Eignung nach Startbahn",
    )
    fig.update_traces(texttemplate="%{text:.0f}", textposition="outside")
    fig.update_layout(
        height=360,
        margin=dict(l=10, r=10, t=50, b=10),
        yaxis_title="Score",
        xaxis_title="Startbahn",
        legend_title_text="Status",
    )
    return fig


def _wind_direction_chart(
    recommendation: RunwayRecommendationView,
    wind_direction_deg: float,
) -> go.Figure:
    fig = go.Figure()
    for candidate in recommendation.candidates:
        fig.add_trace(
            go.Scatterpolar(
                r=[0, 1],
                theta=[candidate.runway_heading_deg, candidate.runway_heading_deg],
                mode="lines+text",
                text=["", f"Piste {candidate.runway_number}"],
                textposition="top center",
                name=f"Piste {candidate.runway_number}",
                line=dict(width=4, color=_line_color(candidate.status_label)),
            )
        )

    fig.add_trace(
        go.Scatterpolar(
            r=[0, 1],
            theta=[wind_direction_deg, wind_direction_deg],
            mode="lines+text",
            text=["", "Wind"],
            textposition="bottom center",
            name="Windrichtung",
            line=dict(width=5, dash="dash", color="#1565C0"),
        )
    )
    fig.update_layout(
        title="Windrichtung und Runway-Ausrichtung",
        height=360,
        margin=dict(l=10, r=10, t=50, b=10),
        polar=dict(
            angularaxis=dict(direction="clockwise", rotation=90),
            radialaxis=dict(visible=False, range=[0, 1]),
        ),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2),
    )
    return fig


def _render_candidate_table(recommendation: RunwayRecommendationView) -> None:
    rows = [
        {
            "Piste": candidate.runway_number,
            "Status": candidate.status_label,
            "Score": candidate.score,
            "Konfidenz": f"{candidate.confidence_percent}%",
            "Gegenwind": f"{candidate.headwind_kmh:.0f} km/h",
            "Seitenwind": f"{candidate.crosswind_kmh:.0f} km/h",
            "Rueckenwind": f"{candidate.tailwind_kmh:.0f} km/h",
            "Hinweise": "; ".join(candidate.limitations) or "Keine",
        }
        for candidate in recommendation.candidates
    ]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


def _render_reasoning(best: RunwayCandidateView) -> None:
    with st.expander(f"Begruendung fuer Piste {best.runway_number}", expanded=True):
        if best.rationale:
            st.markdown("**Positive Faktoren**")
            for item in best.rationale:
                st.write(f"- {item}")
        if best.limitations:
            st.markdown("**Einschraenkungen**")
            for item in best.limitations:
                st.write(f"- {item}")


def _render_operational_context(context: OperationalContext) -> None:
    st.subheader("Datenbank-Kontext")
    weather_tab, aircraft_tab, traffic_tab, load_tab = st.tabs(
        ["Wetterhistorie", "Flugzeugtyp", "Verkehrslast", "Auslastung"]
    )
    with weather_tab:
        _render_weather_history(context)
    with aircraft_tab:
        _render_aircraft_profile(context)
    with traffic_tab:
        _render_traffic_load(context)
    with load_tab:
        _render_booking_load(context)


def _render_weather_history(context: OperationalContext) -> None:
    weather = context.weather
    st.caption(
        "Aehnlichkeit: Windrichtung +/-30 Grad, Windgeschwindigkeit +/-10 km/h, "
        f"Wetterlage: {weather.selected_weather}."
    )
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Aehnliche Messpunkte", _format_int(weather.similar_observations))
    col2.metric("Historie gesamt", _format_int(weather.total_observations))
    col3.metric("Durchschnitt Wind", _format_optional(weather.avg_wind_kmh, " km/h"))
    col4.metric("Durchschnitt Temp.", _format_optional(weather.avg_temp_c, " C"))

    col1, col2, col3 = st.columns(3)
    col1.metric("Durchschnitt Luftdruck", _format_optional(weather.avg_airpressure_hpa, " hPa"))
    col2.metric("Durchschnitt Feuchte", _format_optional(weather.avg_humidity_percent, "%"))
    col3.metric("Stationen", str(weather.station_count))

    range_text = f"{weather.date_min or '-'} bis {weather.date_max or '-'}"
    st.caption(f"Zeitraum im Dump: {range_text}")

    if not weather.top_weather:
        st.info("Keine aehnlichen Wetterpunkte im Dump gefunden.")
        return

    weather_rows = pd.DataFrame(weather.top_weather, columns=["Wetterlage", "Treffer"])
    fig = px.bar(
        weather_rows,
        x="Treffer",
        y="Wetterlage",
        orientation="h",
        title="Haeufigste Wetterlagen bei aehnlichen Bedingungen",
        color_discrete_sequence=["#1565C0"],
    )
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=45, b=10))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def _render_aircraft_profile(context: OperationalContext) -> None:
    aircraft = context.aircraft
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ausgewaehlter Typ", aircraft.aircraft_type)
    col2.metric("Flugzeuge im Dump", _format_int(aircraft.aircraft_count))
    col3.metric("Durchschnitt Kapazitaet", _format_optional(aircraft.avg_capacity, " Sitze"))
    col4.metric("Abgeleitete Klasse", _category_label(aircraft.category))

    col1, col2 = st.columns(2)
    col1.metric("Min. Kapazitaet", _format_optional(aircraft.min_capacity, " Sitze"))
    col2.metric("Max. Kapazitaet", _format_optional(aircraft.max_capacity, " Sitze"))

    if not aircraft.top_types:
        st.info("Keine Flugzeugtypen fuer diese Klasse gefunden.")
        return

    type_rows = pd.DataFrame(aircraft.top_types, columns=["Typ", "Anzahl"])
    st.dataframe(type_rows, hide_index=True, width="stretch")


def _render_traffic_load(context: OperationalContext) -> None:
    traffic = context.traffic
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Starts in Stunde", _format_int(traffic.departures_at_hour))
    col2.metric("Durchschnitt pro Tag", f"{traffic.avg_departures_at_hour_per_day:.2f}")
    col3.metric(
        "Peak-Stunde",
        "-" if traffic.busiest_hour is None else f"{traffic.busiest_hour:02d}:00",
    )
    col4.metric("ZRH Starts gesamt", _format_int(traffic.total_departures))
    st.caption(
        f"Basis: historische Abfluege ab {traffic.airport_iata}, "
        f"Destination: {traffic.destination_label}, "
        f"{traffic.active_days} aktive Tage im Flight-Dump."
    )

    hourly = pd.DataFrame(traffic.hourly_departures, columns=["Stunde", "Starts"])
    hourly["Auswahl"] = hourly["Stunde"].eq(traffic.departure_hour).map(
        {True: "Ausgewaehlt", False: "Andere"}
    )
    fig = px.bar(
        hourly,
        x="Stunde",
        y="Starts",
        color="Auswahl",
        color_discrete_map={"Ausgewaehlt": "#EF6C00", "Andere": "#607D8B"},
        title="Historische ZRH-Starts nach Stunde",
    )
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=45, b=10), xaxis_dtick=1)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def _render_booking_load(context: OperationalContext) -> None:
    booking = context.booking_load
    st.caption(
        f"Filter: {booking.aircraft_type}; Destination: {booking.destination_label}."
    )
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Sample-Buchungen", _format_int(booking.sampled_bookings))
    col2.metric("Sample-Fluege", _format_int(booking.sampled_flights))
    col3.metric("Durchschnitt Auslastung", _format_optional(booking.avg_load_factor_percent, "%"))
    col4.metric("Median Auslastung", _format_optional(booking.median_load_factor_percent, "%"))

    col1, col2 = st.columns(2)
    col1.metric(
        "Durchschnitt Buchungen pro Flug",
        _format_optional(booking.avg_bookings_per_flight, ""),
    )
    col2.metric(
        "Fluege >=85% Auslastung",
        _format_optional(booking.high_load_flights_percent, "%"),
    )
    st.caption(f"{booking.note} Quelle: {booking.sampled_chunk}.")


def _format_int(value: int) -> str:
    return f"{value:,}".replace(",", "'")


def _format_optional(value: float | int | None, suffix: str) -> str:
    if value is None:
        return "-"
    if isinstance(value, int):
        return f"{value}{suffix}"
    return f"{value:.1f}{suffix}"


def _default_aircraft_type_id(options: OperationalSelectionOptions) -> str:
    preferred = ("Airbus-A320", "Airbus A320", "A320")
    for option in options.aircraft_types:
        if any(term in option.label for term in preferred):
            return option.value
    if options.aircraft_types:
        return options.aircraft_types[0].value
    return "__all__"


def _parse_optional_int(value: object) -> int | None:
    text = str(value)
    if text == "__all__":
        return None
    return int(text)


def _precipitation_from_weather(weather_condition: str) -> str:
    if "Schneefall" in weather_condition:
        return "snow"
    if "Nebel" in weather_condition:
        return "fog"
    if "Regen" in weather_condition or "Gewitter" in weather_condition:
        return "rain"
    return "none"


def _has_thunderstorm(weather_condition: str) -> bool:
    return "Gewitter" in weather_condition


def _category_label(category: str) -> str:
    labels = {
        "light": "Klein",
        "medium": "Mittel",
        "heavy": "Gross",
    }
    return labels.get(category, category)


def _line_color(status_label: str) -> str:
    return STATUS_COLORS.get(status_label, "#616161")
