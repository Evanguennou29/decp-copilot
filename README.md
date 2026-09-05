# decp-copilot

Retrieval-augmented search over French public procurement awards (DECP), with measured retrieval quality.

> **Status:** lot 1 (ingestion and normalization) — hybrid search, generation, evaluation and the frontend land in the following lots. See `SPEC.md` for the full plan.

## Planned contents

Once later lots land, this README will follow the plan in `SPEC.md` section 5:
evaluation results table, problem statement, architecture, quickstart
(including the no-API-key mode), evaluation methodology, known limitations.

## Data source, licence, and scope

- **Dataset:** [Données essentielles de la commande publique consolidées (format tabulaire)](https://www.data.gouv.fr/datasets/donnees-essentielles-de-la-commande-publique-consolidees-format-tabulaire), published on data.gouv.fr by Colmo. It aggregates and retypes the DECP that French public buyers must publish under the [22 December 2022 decree](https://www.legifrance.gouv.fr/loda/id/JORFTEXT000046850496).
- **Licence:** **Licence Ouverte / Open Licence version 2.0 (Etalab)** — confirmed on the dataset page (`"license": "lov2"` in its [data.gouv.fr API metadata](https://www.data.gouv.fr/api/1/datasets/donnees-essentielles-de-la-commande-publique-consolidees-format-tabulaire/)). Full text: <https://www.etalab.gouv.fr/licence-ouverte-open-licence>. It allows free reuse, including commercial, with attribution of the source and update date.
- **Refresh cadence:** the producer updates the consolidated Parquet/CSV files roughly daily (`"frequency": "daily"`).
- **File used:** the dataset's stable "latest resource" URL, which always points at the current `decp.parquet` (see `DEFAULT_PARQUET_URL` in `src/decp/ingest/download.py`).
- **Scope filter applied** at ingestion (`src/decp/ingest/normalize.py`), per `SPEC.md` section 1:
  - only markets notified from **2024-01-01** onward (`dateNotification`);
  - concessions excluded (`nature NOT ILIKE '%concession%'`) — the current source did not contain any as of this run, but the filter guards against future contamination;
  - one row per market **award**: `modification_id = 0` keeps the initial attribution and drops later amendments ("avenants"); a market can still span several rows when it has several co-contractors.

### Ingestion measurements (lot 1 criterion)

Real run, reproducible with `python -m decp ingest` (or `make ingest`), on 2026-09-05:

| Step | Metric | Value |
|---|---|---|
| Download | source file size | 234.5 MB (`decp.parquet`) |
| Download | wall time | 236.2 s |
| Normalize (DuckDB) | rows read | 3,261,627 |
| Normalize (DuckDB) | rows kept (in scope) | 781,439 |
| Normalize (DuckDB) | wall time | 4.9 s |
| Normalize (DuckDB) | database size on disk | 190.0 MB (`data/decp.duckdb`) |

The final corpus (190 MB, ~781k rows) fits comfortably on a machine without a
GPU; download time dominates total runtime and depends on network
conditions, not on ingestion logic — DuckDB's own scan-and-filter step
(reading 234.5 MB of Parquet, writing 190 MB back out) takes under 5 seconds.

## Development

```bash
make install   # pip install -e ".[dev]"
make lint      # ruff check .
make test      # pytest
make ingest    # python -m decp ingest — downloads and normalizes the DECP dataset
```

No API key is required to install, lint, test, or ingest data for this project.

## Licence

MIT — see `LICENSE`, for the code in this repository. The DECP dataset
itself is published under the Licence Ouverte 2.0 (Etalab), see above.
