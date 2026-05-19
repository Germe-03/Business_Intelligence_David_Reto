import pandas as pd

from dashboard.osint import opensky


def test_fetch_states_transforms_opensky_payload_without_network(monkeypatch):
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "time": 1_717_000_000,
                "states": [
                    [
                        "abc123",
                        " LX123  ",
                        "Switzerland",
                        1_717_000_000,
                        1_717_000_001,
                        8.55,
                        47.46,
                        1000.0,
                        False,
                        100.0,
                        280.0,
                        0.0,
                        None,
                        1100.0,
                        "7000",
                        False,
                        0,
                        3,
                    ]
                ],
            }

    calls = []

    def fake_get(url, params, auth, timeout):
        calls.append((url, params, auth, timeout))
        return Response()

    monkeypatch.setattr(opensky.requests, "get", fake_get)

    df = opensky.fetch_states.__wrapped__(
        bbox={"lamin": 47, "lamax": 48, "lomin": 8, "lomax": 9},
        username="user",
        password="secret",
    )

    assert calls == [
        (
            "https://opensky-network.org/api/states/all",
            {"lamin": 47, "lamax": 48, "lomin": 8, "lomax": 9},
            ("user", "secret"),
            15,
        )
    ]
    assert df.loc[0, "callsign"] == "LX123"
    assert df.loc[0, "velocity_kmh"] == 360
    assert df.loc[0, "altitude_ft"] == 3281
    assert str(df.loc[0, "server_time"].tz) == "UTC"


def test_fetch_states_returns_empty_frame_with_expected_columns(monkeypatch):
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"time": 1_717_000_000, "states": []}

    monkeypatch.setattr(opensky.requests, "get", lambda *args, **kwargs: Response())

    df = opensky.fetch_states.__wrapped__()

    assert df.empty
    assert {"icao24", "callsign", "origin_country", "velocity_mps"}.issubset(df.columns)


def test_summarise_counts_airborne_aircraft_and_averages():
    df = pd.DataFrame(
        {
            "on_ground": [False, True, False],
            "origin_country": ["CH", "DE", "CH"],
            "altitude_ft": [1000.0, None, 3000.0],
            "velocity_kmh": [200.0, 0.0, 400.0],
            "server_time": [pd.Timestamp("2026-05-19T12:00:00Z")] * 3,
        }
    )

    stats = opensky.summarise(df)

    assert stats.total == 3
    assert stats.on_ground == 1
    assert stats.airborne == 2
    assert stats.countries == 2
    assert stats.avg_altitude_ft == 2000
    assert stats.avg_speed_kmh == 200
    assert stats.fetched_at == pd.Timestamp("2026-05-19T12:00:00Z")


def test_summarise_empty_frame_returns_zero_stats():
    stats = opensky.summarise(pd.DataFrame())

    assert stats.total == 0
    assert stats.on_ground == 0
    assert stats.airborne == 0
    assert stats.countries == 0
    assert stats.avg_altitude_ft == 0.0
    assert stats.avg_speed_kmh == 0.0
