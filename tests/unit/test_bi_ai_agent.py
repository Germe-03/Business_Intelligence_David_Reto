import pandas as pd
import pytest

from dashboard.bi.ai_agent import _display_dataframe, _extract_json, _sanitize_sql


def test_sanitize_sql_accepts_single_select_or_with_query():
    assert _sanitize_sql(" SELECT airline, COUNT(*) AS flights FROM flight; ") == (
        "SELECT airline, COUNT(*) AS flights FROM flight"
    )
    assert _sanitize_sql("WITH x AS (SELECT 1 AS value) SELECT value FROM x") == (
        "WITH x AS (SELECT 1 AS value) SELECT value FROM x"
    )


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM flight",
        "DROP TABLE flight",
        "COPY flight TO 'leak.csv'",
        "PRAGMA show_tables",
        "SELECT COUNT(*) FROM flight; SELECT * FROM passenger",
        "EXPLAIN SELECT * FROM flight",
    ],
)
def test_sanitize_sql_rejects_unsafe_or_non_select_queries(sql):
    with pytest.raises(ValueError):
        _sanitize_sql(sql)


def test_extract_json_reads_fenced_llm_response_with_surrounding_text():
    response = """
    Hier ist die Abfrage:
    ```json
    {"sql": "SELECT COUNT(*) AS flights FROM flight", "explanation": "zaehlt Fluege"}
    ```
    """

    data = _extract_json(response)

    assert data == {
        "sql": "SELECT COUNT(*) AS flights FROM flight",
        "explanation": "zaehlt Fluege",
    }


def test_display_dataframe_hides_technical_keys_and_renames_columns():
    result = pd.DataFrame(
        {
            "flight_id": [1],
            "to_id": [13591],
            "airlinename": ["Swiss"],
            "avg_price": [220.5],
            "custom_metric": [4],
        }
    )

    display = _display_dataframe(result)

    assert list(display.columns) == [
        "Airline",
        "Ticketpreis im Schnitt (CHF)",
        "Custom Metric",
    ]
    assert display.iloc[0].to_dict() == {
        "Airline": "Swiss",
        "Ticketpreis im Schnitt (CHF)": 220.5,
        "Custom Metric": 4,
    }
