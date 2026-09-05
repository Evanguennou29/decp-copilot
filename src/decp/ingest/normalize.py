"""Type, clean, and scope-filter the consolidated DECP data into DuckDB.

Scope applied here (SPEC.md section 1, "Dans le périmètre" / "Hors
périmètre"):

- keep only markets notified from 2024 onward (``dateNotification``);
- exclude concessions, which follow a different regulatory scheme;
- keep one row per market award: ``modification_id = 0`` is the initial
  attribution, before any amendment ("avenant"). A market can still span
  several output rows when it has several co-contractors (``titulaire_*``).

Only the columns relevant to search and citation are kept; the full DECP
schema has ~60 columns, most unused by this project (see
https://static.data.gouv.fr/resources/donnees-essentielles-de-la-commande-publique-consolidees-format-tabulaire/*/schema.json).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import duckdb

SCOPE_START_DATE = "2024-01-01"
TABLE_NAME = "marches"

SELECTED_COLUMNS = (
    "uid",
    "id",
    "nature",
    "type",
    "procedure",
    "acheteur_id",
    "acheteur_nom",
    "acheteur_departement_code",
    "acheteur_departement_nom",
    "titulaire_id",
    "titulaire_nom",
    "objet",
    "montant",
    "codeCPV",
    "dateNotification",
    "datePublicationDonnees",
    "dureeMois",
)

_SCOPE_WHERE = f"""
    modification_id = 0
    AND dateNotification >= DATE '{SCOPE_START_DATE}'
    AND (nature IS NULL OR nature NOT ILIKE '%concession%')
"""


@dataclass(frozen=True)
class NormalizeResult:
    database_path: Path
    rows_in: int
    rows_out: int
    elapsed_seconds: float
    database_bytes: int


def normalize_to_duckdb(parquet_path: Path, database_path: Path) -> NormalizeResult:
    """Load ``parquet_path`` into a ``marches`` table in a DuckDB file.

    ``database_path`` is replaced (``CREATE OR REPLACE TABLE``) so this is
    safe to re-run, e.g. after a fresh download.
    """
    parquet_path = Path(parquet_path)
    database_path = Path(database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    source_path = str(parquet_path)

    start = time.perf_counter()
    con = duckdb.connect(str(database_path))
    try:
        rows_in = con.execute(
            "SELECT count(*) FROM read_parquet(?)", [source_path]
        ).fetchone()[0]

        columns_sql = ", ".join(SELECTED_COLUMNS)
        con.execute(
            f"CREATE OR REPLACE TABLE {TABLE_NAME} AS "
            f"SELECT {columns_sql} FROM read_parquet(?) WHERE {_SCOPE_WHERE}",
            [source_path],
        )
        rows_out = con.execute(f"SELECT count(*) FROM {TABLE_NAME}").fetchone()[0]
    finally:
        con.close()
    elapsed = time.perf_counter() - start

    return NormalizeResult(
        database_path=database_path,
        rows_in=rows_in,
        rows_out=rows_out,
        elapsed_seconds=elapsed,
        database_bytes=database_path.stat().st_size,
    )
