import pytest

from src.application.recommend_runway import RecommendRunway
from src.domain.runway import Runway, SuitabilityStatus, WeatherCondition, aircraft_limits_for


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
    assert "Rueckenwind" in " ".join(result.best.limitations)


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


def test_rejects_invalid_weather_inputs():
    with pytest.raises(ValueError, match="wind_speed"):
        WeatherCondition(wind_speed_kmh=-1, wind_direction_deg=280, visibility_m=8000)

    with pytest.raises(ValueError, match="gust_speed"):
        WeatherCondition(
            wind_speed_kmh=10,
            gust_speed_kmh=-1,
            wind_direction_deg=280,
            visibility_m=8000,
        )

    with pytest.raises(ValueError, match="visibility"):
        WeatherCondition(wind_speed_kmh=10, wind_direction_deg=280, visibility_m=-1)


def test_unknown_aircraft_category_is_rejected():
    with pytest.raises(ValueError, match="Unknown aircraft_category"):
        aircraft_limits_for("super-heavy")


def test_requires_at_least_one_takeoff_runway():
    with pytest.raises(ValueError, match="takeoff runway"):
        RecommendRunway(runways=(Runway(number="14", heading_deg=140, supports_takeoff=False),))


def test_crosswind_over_limit_is_not_suitable_for_light_aircraft():
    use_case = RecommendRunway(runways=(Runway(number="28", heading_deg=280),))
    weather = WeatherCondition(
        wind_speed_kmh=35,
        wind_direction_deg=10,
        visibility_m=10000,
        precipitation="none",
    )

    result = use_case.execute(weather=weather, aircraft_category="light")

    assert result.best.status == SuitabilityStatus.NOT_SUITABLE
    assert result.best.crosswind_kmh > 25
    assert any("Seitenwind" in limitation for limitation in result.best.limitations)


def test_large_gust_spread_adds_uncertainty_penalty():
    use_case = RecommendRunway(runways=(Runway(number="28", heading_deg=280),))

    steady = use_case.execute(
        weather=WeatherCondition(
            wind_speed_kmh=20,
            wind_direction_deg=280,
            visibility_m=10000,
        ),
        aircraft_category="medium",
    )
    gusty = use_case.execute(
        weather=WeatherCondition(
            wind_speed_kmh=20,
            gust_speed_kmh=45,
            wind_direction_deg=280,
            visibility_m=10000,
        ),
        aircraft_category="medium",
    )

    assert gusty.best.score < steady.best.score
    assert any("Boeen" in limitation for limitation in gusty.best.limitations)
