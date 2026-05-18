from __future__ import annotations

from dataclasses import dataclass

from src.domain.runway import (
    Runway,
    RunwaySuitability,
    WeatherCondition,
    ZRH_TAKEOFF_RUNWAYS,
    evaluate_runway,
)


@dataclass(frozen=True)
class RunwayRecommendationResult:
    best: RunwaySuitability
    recommendations: tuple[RunwaySuitability, ...]


class RecommendRunway:
    def __init__(self, runways: tuple[Runway, ...] = ZRH_TAKEOFF_RUNWAYS) -> None:
        self._runways = tuple(runway for runway in runways if runway.supports_takeoff)
        if not self._runways:
            raise ValueError("At least one takeoff runway is required")

    def execute(
        self,
        weather: WeatherCondition,
        aircraft_category: str,
    ) -> RunwayRecommendationResult:
        recommendations = tuple(
            sorted(
                (
                    evaluate_runway(
                        runway=runway,
                        weather=weather,
                        aircraft_category=aircraft_category,
                    )
                    for runway in self._runways
                ),
                key=lambda recommendation: recommendation.score,
                reverse=True,
            )
        )
        return RunwayRecommendationResult(
            best=recommendations[0],
            recommendations=recommendations,
        )
