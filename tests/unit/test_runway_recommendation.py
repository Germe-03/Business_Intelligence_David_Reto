from src.application.recommend_runway import RecommendRunway
from src.domain.runway import Runway, SuitabilityStatus, WeatherCondition


def test_recommends_runway_with_strongest_headwind():
    use_case = RecommendRunway()
    weather = WeatherCondition(
        wind_speed_kmh=24,
        wind_direction_deg=280,
        gust_speed_kmh=30,
        visibility_m=8000,
        precipitation="none",
    )

    result = use_case.execute(weather=weather, aircraft_category="medium")

    assert result.best.runway.number == "28"
    assert result.best.status == SuitabilityStatus.RECOMMENDED
    assert result.best.headwind_kmh > 20
    assert abs(result.best.crosswind_kmh) < 1


def test_marks_runway_not_suitable_when_tailwind_exceeds_limit():
    use_case = RecommendRunway(runways=(Runway(number="28", heading_deg=280),))
    weather = WeatherCondition(
        wind_speed_kmh=35,
        wind_direction_deg=100,
        visibility_m=10000,
        precipitation="none",
    )

    result = use_case.execute(weather=weather, aircraft_category="light")

    assert result.best.runway.number == "28"
    assert result.best.status == SuitabilityStatus.NOT_SUITABLE
    assert result.best.tailwind_kmh > 30
    assert "Rückenwind" in " ".join(result.best.limitations)


def test_normalizes_wind_direction_before_scoring():
    use_case = RecommendRunway(runways=(Runway(number="34", heading_deg=340),))
    weather = WeatherCondition(
        wind_speed_kmh=20,
        wind_direction_deg=-20,
        visibility_m=9000,
        precipitation="none",
    )

    result = use_case.execute(weather=weather, aircraft_category="medium")

    assert result.best.runway.number == "34"
    assert result.best.status == SuitabilityStatus.RECOMMENDED
    assert result.best.headwind_kmh > 19


def test_low_visibility_reduces_confidence_and_adds_limitation():
    use_case = RecommendRunway(runways=(Runway(number="28", heading_deg=280),))
    weather = WeatherCondition(
        wind_speed_kmh=10,
        wind_direction_deg=280,
        visibility_m=700,
        precipitation="fog",
    )

    result = use_case.execute(weather=weather, aircraft_category="heavy")

    assert result.best.confidence < 0.7
    assert result.best.status == SuitabilityStatus.CAUTION
    assert any("Sicht" in limitation for limitation in result.best.limitations)
