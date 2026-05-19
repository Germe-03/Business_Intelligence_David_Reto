from src.interfaces.runway_controller import RunwayDecisionController


def test_controller_returns_user_facing_labels_and_confidence_percent():
    controller = RunwayDecisionController()

    recommendation = controller.recommend(
        aircraft_category="medium",
        wind_speed_kmh=24,
        gust_speed_kmh=30,
        wind_direction_deg=280,
        visibility_m=8000,
        precipitation="none",
    )

    assert recommendation.best.runway_number == "28"
    assert recommendation.best.status_label == "Empfohlen"
    assert recommendation.best.confidence_percent == round(recommendation.best.score)
    assert [candidate.runway_number for candidate in recommendation.candidates] == [
        "28",
        "32",
        "34",
    ]


def test_controller_marks_thunderstorm_as_not_suitable():
    controller = RunwayDecisionController()

    recommendation = controller.recommend(
        aircraft_category="heavy",
        wind_speed_kmh=8,
        wind_direction_deg=280,
        visibility_m=9000,
        precipitation="rain",
        thunderstorm=True,
    )

    assert recommendation.best.status_label == "Nicht geeignet"
    assert any("Gewitterlage" in limitation for limitation in recommendation.best.limitations)
