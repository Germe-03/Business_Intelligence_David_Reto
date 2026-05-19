from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from src.infrastructure.meteoswiss_weather import (
    MeteoSwissWeatherError,
    _derive_forecast_weather_condition,
    _forecast_target_time_utc,
    _latest_forecast_asset,
    _read_forecast_value_from_lines,
)


def test_forecast_target_time_uses_next_full_local_hour_in_utc():
    now = datetime(2026, 5, 19, 13, 15, tzinfo=ZoneInfo("Europe/Zurich"))

    target = _forecast_target_time_utc(2, now)

    assert target == datetime(2026, 5, 19, 14, 0, tzinfo=timezone.utc)


def test_forecast_parser_reads_klo_value_for_exact_target():
    lines = [
        "point_id;point_type_id;Date;tre200h0",
        "58;1;202605191400;11.0",
        "59;1;202605191400;12,5",
        "60;1;202605191400;13.0",
    ]

    value = _read_forecast_value_from_lines(
        lines,
        "tre200h0",
        point_id=59,
        point_type_id=1,
        target_at_utc=datetime(2026, 5, 19, 14, 0, tzinfo=timezone.utc),
        allow_next=False,
    )

    assert value.value == 12.5
    assert value.valid_at_utc == datetime(2026, 5, 19, 14, 0, tzinfo=timezone.utc)


def test_forecast_parser_can_use_next_available_hour():
    lines = [
        "point_id;point_type_id;Date;fu3010h0",
        "59;1;202605191400;19.0",
        "59;1;202605191500;20.0",
    ]

    value = _read_forecast_value_from_lines(
        lines,
        "fu3010h0",
        point_id=59,
        point_type_id=1,
        target_at_utc=datetime(2026, 5, 19, 13, 0, tzinfo=timezone.utc),
        allow_next=True,
    )

    assert value.value == 19.0
    assert value.valid_at_utc == datetime(2026, 5, 19, 14, 0, tzinfo=timezone.utc)


def test_forecast_parser_requires_exact_hour_when_configured():
    lines = [
        "point_id;point_type_id;Date;fu3010h0",
        "59;1;202605191400;19.0",
    ]

    with pytest.raises(MeteoSwissWeatherError):
        _read_forecast_value_from_lines(
            lines,
            "fu3010h0",
            point_id=59,
            point_type_id=1,
            target_at_utc=datetime(2026, 5, 19, 13, 0, tzinfo=timezone.utc),
            allow_next=False,
        )


def test_latest_forecast_asset_uses_newest_run_for_parameter():
    assets = {
        "vnut12.lssw.202605191100.tre200h0.csv": {"href": "old"},
        "vnut12.lssw.202605191200.tre200h0.csv": {"href": "new"},
        "vnut12.lssw.202605191200.fu3010h0.csv": {"href": "wind"},
    }

    asset = _latest_forecast_asset(assets, "tre200h0")

    assert asset["href"] == "new"


@pytest.mark.parametrize(
    ("symbol_code", "precipitation_mm", "temperature_c", "expected"),
    [
        (28, 0.0, 10.0, "Nebel"),
        (24, 1.2, 18.0, "Regen-Gewitter"),
        (15, 0.4, 2.0, "Regen-Schneefall"),
        (None, 0.8, -1.0, "Schneefall"),
        (None, 0.0, 12.0, None),
    ],
)
def test_derive_forecast_weather_condition(
    symbol_code,
    precipitation_mm,
    temperature_c,
    expected,
):
    assert (
        _derive_forecast_weather_condition(
            symbol_code,
            precipitation_mm,
            temperature_c,
        )
        == expected
    )
