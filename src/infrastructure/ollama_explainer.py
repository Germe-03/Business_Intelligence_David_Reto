from __future__ import annotations

import json
from dataclasses import dataclass
from urllib import error, request

from src.application.explain_runway_decision import (
    RunwayDecisionContext,
    build_fallback_explanation,
    build_runway_explanation_prompt,
)


@dataclass(frozen=True)
class ExplanationResult:
    text: str
    source: str
    error_message: str | None = None


class OllamaRunwayExplainer:
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str | None = None,
        timeout_seconds: int = 20,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model.strip() if model else None
        self._timeout_seconds = timeout_seconds

    def explain(self, context: RunwayDecisionContext) -> ExplanationResult:
        model = self._model
        if model is None:
            try:
                model = self.latest_model_name()
            except (OSError, TimeoutError, error.URLError, error.HTTPError) as exc:
                return ExplanationResult(
                    text=build_fallback_explanation(context),
                    source="fallback",
                    error_message=_friendly_error(exc),
                )

        if not model:
            return ExplanationResult(
                text=build_fallback_explanation(context),
                source="fallback",
                error_message=(
                    "In Ollama ist kein lokales Modell installiert. "
                    "Installiere eines mit `ollama pull llama3.2`."
                ),
            )

        payload = {
            "model": model,
            "prompt": build_runway_explanation_prompt(context),
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 180,
            },
        }

        try:
            response = self._post_json("/api/generate", payload)
        except (OSError, TimeoutError, error.URLError, error.HTTPError) as exc:
            return ExplanationResult(
                text=build_fallback_explanation(context),
                source="fallback",
                error_message=_friendly_error(exc),
            )

        generated = str(response.get("response", "")).strip()
        if not generated:
            return ExplanationResult(
                text=build_fallback_explanation(context),
                source="fallback",
                error_message="Ollama hat keine Antwort geliefert.",
            )

        return ExplanationResult(text=generated, source=f"ollama:{model}")

    def latest_model_name(self) -> str | None:
        response = self._get_json("/api/tags")
        models = response.get("models", [])
        if not isinstance(models, list):
            return None
        return select_latest_model_name(models)

    def _post_json(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            url=f"{self._base_url}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(http_request, timeout=self._timeout_seconds) as response:
            response_body = response.read().decode("utf-8")
        return json.loads(response_body)

    def _get_json(self, path: str) -> dict[str, object]:
        http_request = request.Request(
            url=f"{self._base_url}{path}",
            headers={"Content-Type": "application/json"},
            method="GET",
        )
        with request.urlopen(http_request, timeout=self._timeout_seconds) as response:
            response_body = response.read().decode("utf-8")
        return json.loads(response_body)


def select_latest_model_name(models: list[object]) -> str | None:
    valid_models = [
        model
        for model in models
        if isinstance(model, dict) and isinstance(model.get("name"), str)
    ]
    if not valid_models:
        return None
    latest = max(valid_models, key=lambda model: str(model.get("modified_at", "")))
    return str(latest["name"])


def _friendly_error(exc: BaseException) -> str:
    if isinstance(exc, error.HTTPError):
        detail = exc.read().decode("utf-8", errors="replace")
        if exc.code == 404:
            return (
                "Ollama ist erreichbar, aber das Modell wurde nicht gefunden. "
                "Führe z.B. `ollama pull llama3.2` aus."
            )
        return f"Ollama HTTP {exc.code}: {detail[:180]}"
    return (
        "Ollama ist lokal nicht erreichbar. Starte Ollama und prüfe "
        "`http://localhost:11434`."
    )
