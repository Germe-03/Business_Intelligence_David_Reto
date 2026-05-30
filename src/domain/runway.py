from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import cos, radians, sin


class SuitabilityStatus(str, Enum):
    RECOMMENDED = "recommended"
    CAUTION = "caution"
    NOT_SUITABLE = "not_suitable"


@dataclass(frozen=True)
class Runway:
    number: str
    heading_deg: int
    supports_takeoff: bool = True


@dataclass(frozen=True)
class WeatherCondition:
    wind_speed_kmh: float
    wind_direction_deg: float
    visibility_m: int
    precipitation: str = "none"
    gust_speed_kmh: float | None = None
    temperature_c: float | None = None
    thunderstorm: bool = False

    def __post_init__(self) -> None:
        if self.wind_speed_kmh < 0:
            raise ValueError("wind_speed_kmh must not be negative")
        if self.gust_speed_kmh is not None and self.gust_speed_kmh < 0:
            raise ValueError("gust_speed_kmh must not be negative")
        if self.visibility_m < 0:
            raise ValueError("visibility_m must not be negative")

    @property
    def normalized_wind_direction_deg(self) -> float:
        return self.wind_direction_deg % 360

    @property
    def effective_wind_speed_kmh(self) -> float:
        if self.gust_speed_kmh is None:
            return self.wind_speed_kmh
        return max(self.wind_speed_kmh, self.gust_speed_kmh)


@dataclass(frozen=True)
class AircraftLimits:
    crosswind_limit_kmh: float
    tailwind_limit_kmh: float


@dataclass(frozen=True)
class RunwaySuitability:
    runway: Runway
    score: float
    confidence: float
    status: SuitabilityStatus
    headwind_kmh: float
    crosswind_kmh: float
    tailwind_kmh: float
    limitations: tuple[str, ...]
    rationale: tuple[str, ...]


ZRH_TAKEOFF_RUNWAYS: tuple[Runway, ...] = (
    Runway(number="28", heading_deg=280),
    Runway(number="32", heading_deg=320),
    Runway(number="34", heading_deg=340),
)

AIRCRAFT_LIMITS: dict[str, AircraftLimits] = {
    "light": AircraftLimits(crosswind_limit_kmh=25, tailwind_limit_kmh=8),
    "medium": AircraftLimits(crosswind_limit_kmh=35, tailwind_limit_kmh=12),
    "heavy": AircraftLimits(crosswind_limit_kmh=45, tailwind_limit_kmh=18),
}

PRECIPITATION_PENALTIES: dict[str, float] = {
    "none": 0,
    "rain": 8,
    "snow": 18,
    "fog": 12,
    "ice": 25,
}


def aircraft_limits_for(category: str) -> AircraftLimits:
    normalized = category.strip().lower()
    if normalized not in AIRCRAFT_LIMITS:
        raise ValueError(f"Unknown aircraft_category: {category}")
    return AIRCRAFT_LIMITS[normalized]


def evaluate_runway(
    runway: Runway,
    weather: WeatherCondition,
    aircraft_category: str,
) -> RunwaySuitability:
    limits = aircraft_limits_for(aircraft_category)
    headwind, crosswind = _wind_components(runway, weather)
    tailwind = max(0.0, -headwind)
    positive_headwind = max(0.0, headwind)

    score = 100.0
    limitations: list[str] = []
    rationale: list[str] = []
    disqualifying = False

    score += min(positive_headwind * 0.6, 15)
    if positive_headwind > 5:
        rationale.append(f"Gegenwind {positive_headwind:.0f} km/h stabilisiert den Start")

    crosswind_ratio = abs(crosswind) / limits.crosswind_limit_kmh
    score -= min(crosswind_ratio * 35, 80)
    if crosswind_ratio > 1:
        disqualifying = True
        limitations.append(
            f"Seitenwind {abs(crosswind):.0f} km/h über Limit "
            f"{limits.crosswind_limit_kmh:.0f} km/h"
        )
    elif crosswind_ratio >= 0.8:
        limitations.append(
            f"Seitenwind {abs(crosswind):.0f} km/h nahe Limit "
            f"{limits.crosswind_limit_kmh:.0f} km/h"
        )
    else:
        rationale.append(
            f"Seitenwind {abs(crosswind):.0f} km/h innerhalb Limit "
            f"{limits.crosswind_limit_kmh:.0f} km/h"
        )

    if tailwind > 0:
        tailwind_ratio = tailwind / limits.tailwind_limit_kmh
        score -= min(tailwind_ratio * 50, 95)
        if tailwind_ratio > 1:
            disqualifying = True
            limitations.append(
                f"Rückenwind {tailwind:.0f} km/h über Limit "
                f"{limits.tailwind_limit_kmh:.0f} km/h"
            )
        else:
            limitations.append(f"Rückenwind {tailwind:.0f} km/h")

    gust_penalty = _gust_penalty(weather)
    if gust_penalty:
        score -= gust_penalty
        limitations.append("Böen erhöhen die Unsicherheit")

    visibility_penalty = _visibility_penalty(weather.visibility_m)
    if visibility_penalty:
        score -= visibility_penalty
        limitations.append(f"Sichtweite {weather.visibility_m} m eingeschränkt")

    precipitation = weather.precipitation.strip().lower()
    precipitation_penalty = PRECIPITATION_PENALTIES.get(precipitation, 10)
    if precipitation_penalty:
        score -= precipitation_penalty
        limitations.append(f"Wetterlage: {weather.precipitation}")

    if weather.thunderstorm:
        score -= 55
        limitations.append("Gewitterlage")
        disqualifying = True

    score = max(0.0, min(100.0, score))
    status = _status_for(score, disqualifying)

    return RunwaySuitability(
        runway=runway,
        score=round(score, 1),
        confidence=round(score / 100, 2),
        status=status,
        headwind_kmh=round(positive_headwind, 1),
        crosswind_kmh=round(abs(crosswind), 1),
        tailwind_kmh=round(tailwind, 1),
        limitations=tuple(limitations),
        rationale=tuple(rationale),
    )


def _wind_components(runway: Runway, weather: WeatherCondition) -> tuple[float, float]:
    angle = _relative_angle(
        weather.normalized_wind_direction_deg,
        runway.heading_deg,
    )
    speed = weather.effective_wind_speed_kmh
    headwind = speed * cos(radians(angle))
    crosswind = speed * sin(radians(angle))
    return headwind, crosswind


def _relative_angle(wind_from_deg: float, runway_heading_deg: float) -> float:
    return ((wind_from_deg - runway_heading_deg + 180) % 360) - 180


def _gust_penalty(weather: WeatherCondition) -> float:
    if weather.gust_speed_kmh is None:
        return 0.0
    spread = weather.gust_speed_kmh - weather.wind_speed_kmh
    if spread <= 10:
        return 0.0
    return min((spread - 10) * 1.2, 20)


def _visibility_penalty(visibility_m: int) -> float:
    if visibility_m < 500:
        return 45
    if visibility_m < 800:
        return 32
    if visibility_m < 1500:
        return 22
    if visibility_m < 3000:
        return 10
    return 0


def _status_for(score: float, disqualifying: bool) -> SuitabilityStatus:
    if disqualifying or score < 45:
        return SuitabilityStatus.NOT_SUITABLE
    if score < 75:
        return SuitabilityStatus.CAUTION
    return SuitabilityStatus.RECOMMENDED
