from pathlib import Path

import duckdb
import pytest

from decp.ingest.normalize import TABLE_NAME, normalize_to_duckdb

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "decp_sample.parquet"


@pytest.fixture
def result(tmp_path):
    database_path = tmp_path / "decp.duckdb"
    return normalize_to_duckdb(FIXTURE_PATH, database_path)


def test_normalize_reports_scope_filtering(result):
    assert result.rows_in == 8
    assert result.rows_out == 5


def test_normalize_measures_timing_and_size(result):
    assert result.elapsed_seconds >= 0
    assert result.database_bytes > 0
    assert result.database_path.exists()


def test_normalize_excludes_pre_2024_markets(result):
    con = duckdb.connect(str(result.database_path))
    rows = con.execute(
        f"SELECT uid FROM {TABLE_NAME} WHERE dateNotification < DATE '2024-01-01'"
    ).fetchall()
    con.close()
    assert rows == []


def test_normalize_excludes_amendments(result):
    con = duckdb.connect(str(result.database_path))
    rows = con.execute(
        f"SELECT uid FROM {TABLE_NAME} WHERE uid = '44444444400011M002'"
    ).fetchall()
    con.close()
    assert rows == []


def test_normalize_excludes_concessions(result):
    con = duckdb.connect(str(result.database_path))
    rows = con.execute(
        f"SELECT uid FROM {TABLE_NAME} WHERE nature ILIKE '%concession%'"
    ).fetchall()
    con.close()
    assert rows == []


def test_normalize_keeps_markets_with_missing_nature(result):
    con = duckdb.connect(str(result.database_path))
    rows = con.execute(
        f"SELECT uid FROM {TABLE_NAME} WHERE uid = '10101010100011M001'"
    ).fetchall()
    con.close()
    assert rows == [("10101010100011M001",)]


def test_normalize_keeps_all_co_contractors_of_a_market(result):
    con = duckdb.connect(str(result.database_path))
    rows = con.execute(
        f"SELECT titulaire_nom FROM {TABLE_NAME} "
        "WHERE uid = '13131313100011M001' ORDER BY titulaire_nom"
    ).fetchall()
    con.close()
    assert rows == [("Titulaire Deux",), ("Titulaire Un",)]


def test_normalize_types_montant_as_number(result):
    con = duckdb.connect(str(result.database_path))
    montant = con.execute(
        f"SELECT montant FROM {TABLE_NAME} WHERE uid = '12345678900011M001'"
    ).fetchone()[0]
    con.close()
    assert montant == 45000.0


def test_normalize_is_rerunnable(result):
    second = normalize_to_duckdb(FIXTURE_PATH, result.database_path)
    assert second.rows_out == result.rows_out
