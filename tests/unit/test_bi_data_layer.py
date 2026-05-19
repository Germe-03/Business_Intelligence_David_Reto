from dashboard.bi import data_layer


def test_schema_overview_exposes_expected_core_tables_without_private_types():
    schema = data_layer.schema_overview()

    assert {"flight", "booking", "airplane", "weatherdata"}.issubset(schema)
    assert schema["flight"] == [
        "flight_id",
        "flightno",
        "from_id",
        "to_id",
        "departure",
        "arrival",
        "airline_id",
        "airplane_id",
    ]


def test_columns_sql_builds_duckdb_columns_map():
    columns_sql = data_layer._columns_sql("airline")

    assert columns_sql == (
        "{'airline_id': 'INTEGER', 'iata': 'VARCHAR', "
        "'airlinename': 'VARCHAR', 'base_airport': 'INTEGER'}"
    )


def test_empty_view_sql_preserves_table_schema_when_data_file_missing():
    sql = data_layer._empty_view_sql("flight")

    assert sql.startswith("CREATE OR REPLACE VIEW flight AS SELECT")
    assert "CAST(NULL AS INTEGER) AS flight_id" in sql
    assert "CAST(NULL AS TIMESTAMP) AS departure" in sql
    assert sql.endswith("WHERE 1=0")


def test_view_sql_points_duckdb_at_zstd_dump_with_expected_options():
    sql = data_layer._view_sql("booking")

    assert "CREATE OR REPLACE VIEW booking AS SELECT * FROM read_csv(" in sql
    assert "flughafendb_large@booking@*.tsv.zst" in sql
    assert "compression='zstd'" in sql
    assert "nullstr='\\N'" in sql
