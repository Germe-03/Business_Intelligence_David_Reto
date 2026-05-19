import pandas as pd

from dashboard.osint import views


def test_kepler_arcs_keeps_low_volume_routes_visible(monkeypatch):
    calls = []

    def fake_query_df(sql, params):
        calls.append((sql, params))
        return pd.DataFrame(
            {
                "from_iata": ["ZRH"],
                "from_lat": [47.4647],
                "from_lon": [8.5492],
                "to_iata": ["PVC"],
                "to_lat": [42.0719],
                "to_lon": [-70.2214],
                "flights": [26],
            }
        )

    monkeypatch.setattr(views, "query_df", fake_query_df)

    arcs = views._kepler_arcs.__wrapped__(10)

    assert len(arcs) == 1
    assert arcs.loc[0, "flights"] == 26
    assert "HAVING flights > 0" in calls[0][0]
    assert "HAVING flights > 50" not in calls[0][0]
    assert calls[0][1] == (views.ZRH_AIRPORT_ID, 10)


def test_kepler_heat_keeps_existing_booking_points_visible(monkeypatch):
    calls = []

    def fake_query_df(sql, params):
        calls.append((sql, params))
        return pd.DataFrame(
            {
                "ts": [pd.Timestamp("2015-08-01")],
                "lat": [42.0719],
                "lon": [-70.2214],
                "bookings": [326],
            }
        )

    monkeypatch.setattr(views, "query_df", fake_query_df)

    heat = views._kepler_heat.__wrapped__()

    assert len(heat) == 1
    assert heat.loc[0, "bookings"] == 326
    assert "HAVING bookings > 0" in calls[0][0]
    assert "HAVING bookings > 500" not in calls[0][0]
    assert calls[0][1] == (views.ZRH_AIRPORT_ID,)


def test_format_age_handles_missing_and_recent_values(monkeypatch):
    assert views._format_age(pd.NaT) == "?"

    fixed_now = pd.Timestamp("2026-05-19T12:00:30Z").to_pydatetime()

    class FixedDateTime:
        @classmethod
        def now(cls, tz):
            return fixed_now

    monkeypatch.setattr(views, "datetime", FixedDateTime)

    assert views._format_age(pd.Timestamp("2026-05-19T12:00:00Z")) == "vor 30s"
    assert views._format_age(pd.Timestamp("2026-05-19T11:55:00Z")) == "vor 5 min"
    assert views._format_age(pd.Timestamp("2026-05-19T09:00:00Z")) == "vor 3 h"
