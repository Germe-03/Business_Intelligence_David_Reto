from src.application.explain_runway_decision import (
    RunwayDecisionContext,
    build_fallback_explanation,
    build_runway_explanation_prompt,
)
from src.infrastructure.ollama_explainer import OllamaRunwayExplainer, select_latest_model_name


def test_builds_prompt_with_operational_guardrails():
    context = _context()

    prompt = build_runway_explanation_prompt(context)

    assert "Keine operative Freigabe behaupten" in prompt
    assert "Piste 28" in prompt
    assert "Seitenwindkomponente: 4 km/h" in prompt
    assert "Keine erfundenen Wetterdaten" in prompt


def test_fallback_explanation_mentions_best_runway_and_limits():
    context = _context(limitations=("Sichtweite 700 m eingeschraenkt",))

    explanation = build_fallback_explanation(context)

    assert "Piste 28" in explanation
    assert "87% Konfidenz" in explanation
    assert "Sichtweite 700 m eingeschraenkt" in explanation


def test_selects_latest_local_ollama_model_by_modified_at():
    models = [
        {"name": "llama3.2:latest", "modified_at": "2026-01-10T10:00:00Z"},
        {"name": "gemma3:latest", "modified_at": "2026-03-01T10:00:00Z"},
    ]

    assert select_latest_model_name(models) == "gemma3:latest"


def test_ollama_explainer_uses_fallback_when_no_local_model_exists():
    result = _NoModelExplainer().explain(_context())

    assert result.source == "fallback"
    assert "Piste 28" in result.text
    assert "kein lokales Modell installiert" in result.error_message


def test_ollama_explainer_uses_configured_model_response():
    explainer = _StaticOllamaExplainer(model="llama3.2:latest")

    result = explainer.explain(_context())

    assert result.source == "ollama:llama3.2:latest"
    assert result.text == "Piste 28 bleibt die beste Empfehlung."
    assert explainer.last_payload["model"] == "llama3.2:latest"
    assert explainer.last_payload["stream"] is False


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


class _NoModelExplainer(OllamaRunwayExplainer):
    def latest_model_name(self) -> str | None:
        return None


class _StaticOllamaExplainer(OllamaRunwayExplainer):
    def __init__(self, model: str) -> None:
        super().__init__(model=model)
        self.last_payload = {}

    def _post_json(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        self.last_payload = payload
        return {"response": "Piste 28 bleibt die beste Empfehlung."}
