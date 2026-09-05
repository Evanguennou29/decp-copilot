"""One-off generator for tests/fixtures/decp_sample.parquet.

Not part of the application; run manually whenever the fixture needs to
change: ``python scripts/generate_test_fixture.py``.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

FIXTURE_PATH = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "decp_sample.parquet"

ROWS = [
    # uid, id, nature, type, procedure, acheteur_id, acheteur_nom,
    # acheteur_departement_code, acheteur_departement_nom, titulaire_id,
    # titulaire_nom, objet, montant, codeCPV, dateNotification,
    # datePublicationDonnees, dureeMois, modification_id
    (
        "12345678900011M001", "M001", "Marché", "Services", "Procédure adaptée",
        "12345678900011", "Commune de Brest", "29", "Finistère",
        "98765432100022", "Acme Travaux", "Nettoyage des locaux municipaux",
        45000.0, "90910000", "2024-06-01", "2024-06-15", 12, 0,
    ),
    (
        "22222222200011M001", "M001", "Marché", "Fournitures", "Appel d'offres ouvert",
        "22222222200011", "Commune de Quimper", "29", "Finistère",
        "33333333300022", "Fournitures Bretonnes", "Achat de mobilier de bureau",
        30000.0, "39130000", "2023-12-31", "2024-01-05", 6, 0,
    ),
    (
        "44444444400011M002", "M002", "Marché", "Travaux", "Procédure adaptée",
        "44444444400011", "Departement du Finistere", "29", "Finistère",
        "55555555500022", "BTP Ouest", "Réfection de toiture, avenant n°1",
        120000.0, "45260000", "2024-05-01", "2024-05-20", 18, 1,
    ),
    (
        "66666666600011M001", "M001", "Concession", "Services", "Dialogue compétitif",
        "66666666600011", "Region Bretagne", "35", "Ille-et-Vilaine",
        "77777777700022", "Transdev Ouest", "Concession de transport public",
        5000000.0, "60112000", "2024-07-01", "2024-07-10", 60, 0,
    ),
    (
        "88888888800011M001", "M001", "Marché de partenariat", "Travaux", "Procédure négociée",
        "88888888800011", "Commune de Rennes", "35", "Ille-et-Vilaine",
        "99999999900022", "Vinci Construction", "Construction d'une médiathèque",
        2500000.0, "45212330", "2025-01-15", "2025-01-25", 24, 0,
    ),
    (
        "10101010100011M001", "M001", None, "Services", "Marché passé sans publicité",
        "10101010100011", "Commune de Morlaix", "29", "Finistère",
        "11111111100022", "Net Propre", "Entretien des espaces verts",
        8000.0, "77310000", "2024-03-01", "2024-03-10", 12, 0,
    ),
    (
        "13131313100011M001", "M001", "Marché", "Fournitures", "Appel d'offres ouvert",
        "13131313100011", "Commune de Lorient", "56", "Morbihan",
        "14141414100022", "Titulaire Un", "Fourniture de matériel informatique",
        60000.0, "30200000", "2024-02-01", "2024-02-10", 12, 0,
    ),
    (
        "13131313100011M001", "M001", "Marché", "Fournitures", "Appel d'offres ouvert",
        "13131313100011", "Commune de Lorient", "56", "Morbihan",
        "15151515100022", "Titulaire Deux", "Fourniture de matériel informatique",
        60000.0, "30200000", "2024-02-01", "2024-02-10", 12, 0,
    ),
]

COLUMNS = [
    "uid", "id", "nature", "type", "procedure",
    "acheteur_id", "acheteur_nom",
    "acheteur_departement_code", "acheteur_departement_nom",
    "titulaire_id", "titulaire_nom",
    "objet", "montant", "codeCPV",
    "dateNotification", "datePublicationDonnees", "dureeMois",
    "modification_id",
]


def main() -> None:
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    col_names = [f"c{i}" for i in range(len(COLUMNS))]
    row_placeholder = "(" + ", ".join(["?"] * len(COLUMNS)) + ")"
    values_sql = ", ".join([row_placeholder] * len(ROWS))
    params = [value for row in ROWS for value in row]

    con = duckdb.connect()
    con.execute(
        f"CREATE TABLE _rows({', '.join(col_names)}) AS "
        f"SELECT * FROM (VALUES {values_sql})",
        params,
    )
    select_columns = ", ".join(
        f"c{i} AS {name}" if name not in ("dateNotification", "datePublicationDonnees")
        else f"CAST(c{i} AS DATE) AS {name}"
        for i, name in enumerate(COLUMNS)
    )
    con.execute(
        f"COPY (SELECT {select_columns} FROM _rows) TO '{FIXTURE_PATH.as_posix()}' (FORMAT PARQUET)"
    )
    con.close()
    print(f"Wrote {FIXTURE_PATH} ({FIXTURE_PATH.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
