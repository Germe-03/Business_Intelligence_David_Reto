from src.application.explain_runway_decision import (
    RunwayDecisionContext,
    build_fallback_explanation,
    build_runway_explanation_prompt,
)
from src.infrastructure.ollama_explainer import select_latest_model_name


def test_builds_prompt_with_operational_guardrails():
    context = _context()

    prompt = build_runway_explanation_prompt(context)

    assert "Keine operative Freigabe behaupten" in prompt
    assert "Piste 28" in prompt
    assert "Seitenwindkomponente: 4 km/h" in prompt
    assert "Keine erfundenen Wetterdaten" in prompt


def test_fallback_explanation_mentions_best_runway_and_limits():
    context = _context(limitations=("Sichtweite 700 m eingeschränkt",))

    explanation = build_fallback_explanation(context)

    assert "Piste 28" in explanation
    assert "87% Konfidenz" in explanation
    assert "Sichtweite 700 m eingeschränkt" in explanation


def test_selects_latest_local_ollama_model_by_modified_at():
    models = [
        {"name": "llama3.2:latest", "modified_at": "2026-01-10T10:00:00Z"},
        {"name": "gemma3:latest", "modified_at": "2026-03-01T10:00:00Z"},
    ]

    assert select_latest_model_name(models) == "gemma3:latest"


def _context(
    limitations: tuple[str, ...] = (),
) -> RunwayDecisionContext:
    return RunwayDecisionContext(
        runway_number="28",
        status_label="Empfohlen",
        confidence_percent=87,
        aircraft_label="Mittel",
        wind_speed_kmh=20,
        gust_speed_kmh=28,
        wind_direction_deg=280,
        visibility_m=7000,
        precipitation_label="Trocken",
        thunderstorm=False,
        headwind_kmh=20,
        crosswind_kmh=4,
        tailwind_kmh=0,
        limitations=limitations,
        rationale=("Gegenwind stabilisiert den Start",),
    )
