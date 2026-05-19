import pandas as pd
import pytest

from src.infrastructure.meteoswiss_weather import (
    MeteoSwissWeatherError,
    _derive_weather_condition,
    _is_true,
    _optional_float,
    _required_float,
)


@pytest.mark.parametrize(
    ("visual", "expected"),
    [
        ({"fog": True}, "Nebel"),
        ({"rain_snow": True}, "Regen-Schneefall"),
        ({"snowfall": True}, "Schneefall"),
        ({"rain": True}, "Regen"),
    ],
)
def test_visual_observation_has_priority_for_live_weather_condition(visual, expected):
    row = pd.Series({"rre150z0": 0.0, "tre200s0": 18.0, "htoauts0": 0.0})

    assert _derive_weather_condition(row, visual) == expected


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ({"rre150z0": 0.0, "tre200s0": 18.0, "htoauts0": 0.0}, None),
        ({"rre150z0": 1.0, "tre200s0": 0.5, "htoauts0": 0.0}, "Schneefall"),
        ({"rre150z0": 1.0, "tre200s0": 2.5, "htoauts0": 0.0}, "Regen-Schneefall"),
        ({"rre150z0": 1.0, "tre200s0": 5.0, "htoauts0": 0.0}, "Regen"),
        ({"rre150z0": 1.0, "tre200s0": 3.5, "htoauts0": 4.0}, "Regen-Schneefall"),
    ],
)
def test_live_weather_condition_falls_back_to_precipitation_temperature_and_snow(row, expected):
    assert _derive_weather_condition(pd.Series(row), {}) == expected


def test_optional_and_required_float_helpers_handle_missing_values():
    row = pd.Series({"present": "12.5", "missing": pd.NA})

    assert _optional_float(row, "present") == 12.5
    assert _optional_float(row, "missing") is None
    assert _optional_float(row, "unknown") is None

    with pytest.raises(MeteoSwissWeatherError):
        _required_float(row, "missing")


@pytest.mark.parametrize(
    ("value", "expected"),
    [(1, True), ("1", True), (0, False), (pd.NA, False)],
)
def test_is_true_handles_meteoswiss_indicator_values(value, expected):
    assert _is_true(pd.Series({"indicator": value}), "indicator") is expected
