from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.domain.runway import SuitabilityStatus
from src.interfaces.runway_controller import (
    RunwayCandidateView,
    RunwayDecisionController,
    RunwayRecommendationView,
)


DEFAULT_INPUTS = {
    "aircraft_category": "medium",
    "wind_speed_kmh": 24,
    "gust_speed_kmh": 30,
    "wind_direction_deg": 280,
    "visibility_m": 8000,
    "precipitation": "none",
    "temperature_c": 15,
    "thunderstorm": False,
    "detail_mode": "Details",
}

AIRCRAFT_OPTIONS = {
    "light": "Klein",
    "medium": "Mittel",
    "heavy": "Gross",
}

PRECIPITATION_OPTIONS = {
    "none": "Trocken",
    "rain": "Regen",
    "snow": "Schnee",
    "fog": "Nebel",
    "ice": "Vereisung",
}

STATUS_COLORS = {
    "Empfohlen": "#2E7D32",
    "Mit Einschraenkungen": "#EF6C00",
    "Nicht geeignet": "#C62828",
}


@st.cache_resource
def _controller() -> RunwayDecisionController:
    return RunwayDecisionController()


def render_runway_recommendation_page() -> None:
    _ensure_state()
    inputs = _render_sidebar()
    recommendation = _controller().recommend(**inputs)

    st.title("Runway-Entscheidung fuer Starts")
    st.caption("Entscheidungsunterstuetzung fuer ZRH. Nicht fuer operative Freigaben verwenden.")

    _render_decision(recommendation.best)
    _render_metrics(recommendation.best)

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


def _ensure_state() -> None:
    for key, value in DEFAULT_INPUTS.items():
        st.session_state.setdefault(key, value)


def _render_sidebar() -> dict[str, object]:
    with st.sidebar:
        st.header("Eingaben")
        st.selectbox(
            "Flugzeugkategorie",
            options=list(AIRCRAFT_OPTIONS.keys()),
            format_func=AIRCRAFT_OPTIONS.__getitem__,
            key="aircraft_category",
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
            options=list(PRECIPITATION_OPTIONS.keys()),
            format_func=PRECIPITATION_OPTIONS.__getitem__,
            key="precipitation",
        )
        st.slider(
            "Temperatur (C)",
            min_value=-30,
            max_value=45,
            step=1,
            key="temperature_c",
        )
        st.checkbox("Gewitterlage", key="thunderstorm")
        st.radio(
            "Ansicht",
            options=["Kompakt", "Details"],
            horizontal=True,
            key="detail_mode",
        )
        if st.button("Zuruecksetzen", width="stretch"):
            for key, value in DEFAULT_INPUTS.items():
                st.session_state[key] = value
            st.rerun()

    gust_speed = st.session_state.gust_speed_kmh
    return {
        "aircraft_category": st.session_state.aircraft_category,
        "wind_speed_kmh": st.session_state.wind_speed_kmh,
        "gust_speed_kmh": gust_speed if gust_speed > st.session_state.wind_speed_kmh else None,
        "wind_direction_deg": st.session_state.wind_direction_deg,
        "visibility_m": st.session_state.visibility_m,
        "precipitation": st.session_state.precipitation,
        "temperature_c": st.session_state.temperature_c,
        "thunderstorm": st.session_state.thunderstorm,
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


def _line_color(status_label: str) -> str:
    return STATUS_COLORS.get(status_label, "#616161")
