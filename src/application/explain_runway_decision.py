from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RunwayDecisionContext:
    runway_number: str
    status_label: str
    confidence_percent: int
    aircraft_label: str
    wind_speed_kmh: float
    gust_speed_kmh: float | None
    wind_direction_deg: float
    visibility_m: int
    precipitation_label: str
    thunderstorm: bool
    headwind_kmh: float
    crosswind_kmh: float
    tailwind_kmh: float
    limitations: tuple[str, ...]
    rationale: tuple[str, ...]


def build_runway_explanation_prompt(context: RunwayDecisionContext) -> str:
    gust_text = (
        f"{context.gust_speed_kmh:.0f} km/h"
        if context.gust_speed_kmh is not None
        else "keine relevanten Böen"
    )
    limitations = _format_list(context.limitations, "Keine Einschränkungen")
    rationale = _format_list(context.rationale, "Keine positiven Faktoren")
    thunderstorm = "ja" if context.thunderstorm else "nein"

    return f"""Du bist ein sachlicher Decision-Support-Assistent für ein Flughafen-BI-Dashboard.
Erkläre die Startbahn-Empfehlung in Deutsch für einen Dispatcher.

Regeln:
- Keine operative Freigabe behaupten.
- Maximal 5 kurze Sätze.
- Erst Entscheidung, dann Begründung, dann Vorsichtshinweis.
- Keine erfundenen Wetterdaten oder Vorschriften.

Daten:
- Empfehlung: Piste {context.runway_number}
- Status: {context.status_label}
- Konfidenz: {context.confidence_percent}%
- Flugzeugkategorie: {context.aircraft_label}
- Wind: {context.wind_speed_kmh:.0f} km/h aus {context.wind_direction_deg:.0f} Grad
- Böen: {gust_text}
- Sichtweite: {context.visibility_m} m
- Wetterlage: {context.precipitation_label}
- Gewitterlage: {thunderstorm}
- Gegenwindkomponente: {context.headwind_kmh:.0f} km/h
- Seitenwindkomponente: {context.crosswind_kmh:.0f} km/h
- Rückenwindkomponente: {context.tailwind_kmh:.0f} km/h
- Positive Faktoren: {rationale}
- Einschränkungen: {limitations}
"""


def build_fallback_explanation(context: RunwayDecisionContext) -> str:
    core = (
        f"Piste {context.runway_number} ist aktuell die beste Option "
        f"({context.status_label}, {context.confidence_percent}% Konfidenz). "
        f"Die Entscheidung wird vor allem durch {context.headwind_kmh:.0f} km/h "
        f"Gegenwind, {context.crosswind_kmh:.0f} km/h Seitenwind und "
        f"{context.tailwind_kmh:.0f} km/h Rückenwind bestimmt."
    )
    if context.limitations:
        return f"{core} Zu beachten: {'; '.join(context.limitations)}."
    return f"{core} Es liegen keine besonderen Einschränkungen in der Regelbewertung vor."


def _format_list(items: tuple[str, ...], empty_text: str) -> str:
    if not items:
        return empty_text
    return "; ".join(items)
