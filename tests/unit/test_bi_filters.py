from datetime import date, datetime

from dashboard.bi.filters import BIFilter, filter_summary_caption


def test_bi_filter_builds_where_clause_with_all_selected_filters():
    filt = BIFilter(
        date_from=date(2015, 7, 1),
        date_to=date(2015, 7, 31),
        airline_id=7,
        airline_label="LX - Swiss",
        aircraft_type_id=228,
        aircraft_label="Airbus-A320-Familie",
        destination_airport_id=13591,
        destination_label="ZRH - Zuerich",
    )

    where_clause, params = filt.flight_where_clause()

    assert where_clause == (
        "f.departure >= ? AND f.departure < ? AND "
        "f.airline_id = ? AND p.type_id = ? AND f.to_id = ?"
    )
    assert params == [
        datetime(2015, 7, 1),
        datetime(2015, 8, 1),
        7,
        228,
        13591,
    ]


def test_bi_filter_where_clause_omits_optional_filters_when_all_selected():
    filt = BIFilter(
        date_from=date(2015, 8, 10),
        date_to=date(2015, 8, 10),
        airline_id=None,
        airline_label="Alle Airlines",
        aircraft_type_id=None,
        aircraft_label="Alle Flugzeugtypen",
        destination_airport_id=None,
        destination_label="Alle Destinationen",
    )

    where_clause, params = filt.flight_where_clause()

    assert where_clause == "f.departure >= ? AND f.departure < ?"
    assert params == [datetime(2015, 8, 10), datetime(2015, 8, 11)]


def test_filter_summary_caption_is_user_readable():
    filt = BIFilter(
        date_from=date(2015, 9, 1),
        date_to=date(2015, 9, 7),
        airline_id=None,
        airline_label="Alle Airlines",
        aircraft_type_id=228,
        aircraft_label="Airbus-A320-Familie",
        destination_airport_id=None,
        destination_label="Alle Destinationen",
    )

    assert filter_summary_caption(filt) == (
        "01.09.2015 - 07.09.2015 | Alle Airlines | "
        "Airbus-A320-Familie | Alle Destinationen"
    )
