from __future__ import annotations

from dataclasses import dataclass

from src.application.recommend_runway import RecommendRunway
from src.domain.runway import RunwaySuitability, SuitabilityStatus, WeatherCondition


STATUS_LABELS = {
    SuitabilityStatus.RECOMMENDED: "Empfohlen",
    SuitabilityStatus.CAUTION: "Mit Einschraenkungen",
    SuitabilityStatus.NOT_SUITABLE: "Nicht geeignet",
}


@dataclass(frozen=True)
class RunwayCandidateView:
    runway_number: str
    runway_heading_deg: int
    status: SuitabilityStatus
    status_label: str
    score: float
    confidence_percent: int
    headwind_kmh: float
    crosswind_kmh: float
    tailwind_kmh: float
    limitations: tuple[str, ...]
    rationale: tuple[str, ...]


@dataclass(frozen=True)
class RunwayRecommendationView:
    best: RunwayCandidateView
    candidates: tuple[RunwayCandidateView, ...]


class RunwayDecisionController:
    def __init__(self, use_case: RecommendRunway | None = None) -> None:
        self._use_case = use_case or RecommendRunway()

    def recommend(
        self,
        wind_speed_kmh: float,
        wind_direction_deg: float,
        visibility_m: int,
        aircraft_category: str,
        precipitation: str = "none",
        gust_speed_kmh: float | None = None,
        temperature_c: float | None = None,
        thunderstorm: bool = False,
    ) -> RunwayRecommendationView:
        weather = WeatherCondition(
            wind_speed_kmh=wind_speed_kmh,
            wind_direction_deg=wind_direction_deg,
            gust_speed_kmh=gust_speed_kmh,
            visibility_m=visibility_m,
            precipitation=precipitation,
            temperature_c=temperature_c,
            thunderstorm=thunderstorm,
        )
        result = self._use_case.execute(
            weather=weather,
            aircraft_category=aircraft_category,
        )
        candidates = tuple(_to_view(candidate) for candidate in result.recommendations)
        return RunwayRecommendationView(best=candidates[0], candidates=candidates)


def _to_view(candidate: RunwaySuitability) -> RunwayCandidateView:
    return RunwayCandidateView(
        runway_number=candidate.runway.number,
        runway_heading_deg=candidate.runway.heading_deg,
        status=candidate.status,
        status_label=STATUS_LABELS[candidate.status],
        score=candidate.score,
        confidence_percent=round(candidate.confidence * 100),
        headwind_kmh=candidate.headwind_kmh,
        crosswind_kmh=candidate.crosswind_kmh,
        tailwind_kmh=candidate.tailwind_kmh,
        limitations=candidate.limitations,
        rationale=candidate.rationale,
    )
