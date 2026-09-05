"""Command-line entry point for decp-copilot.

Subcommands are wired up here as each lot lands (see SPEC.md section 6);
"serve" only describes what is coming so far.
"""

from __future__ import annotations

import argparse
import time
from datetime import timedelta

import duckdb

from decp.config import load_settings
from decp.index.embed import INDEX_SCOPE_WINDOW_DAYS, embed_texts, load_encoder
from decp.index.store import save_index
from decp.ingest.download import download_parquet
from decp.ingest.normalize import normalize_to_duckdb

_PLANNED_COMMANDS = {
    "serve": "Run the FastAPI application (lot 3).",
}


def _format_bytes(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="decp", description="DECP copilot command-line interface."
    )
    subparsers = parser.add_subparsers(dest="command")

    ingest_parser = subparsers.add_parser(
        "ingest", help="Download and normalize the DECP dataset into DuckDB (lot 1)."
    )
    ingest_parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Reuse the parquet file already on disk instead of downloading it again.",
    )

    subparsers.add_parser(
        "index", help="Encode the recent-window corpus and build the vector index (lot 2)."
    )

    for name, help_text in _PLANNED_COMMANDS.items():
        subparsers.add_parser(name, help=help_text)

    return parser


def _run_ingest(skip_download: bool) -> int:
    settings = load_settings()

    if skip_download:
        print(f"Skipping download, reusing {settings.raw_parquet_path}")
    else:
        print(f"Downloading {settings.source_url} -> {settings.raw_parquet_path}")
        download = download_parquet(settings.raw_parquet_path, settings.source_url)
        print(
            f"Downloaded {_format_bytes(download.bytes_downloaded)} "
            f"in {download.elapsed_seconds:.1f}s"
        )

    print(f"Normalizing into {settings.database_path}")
    normalized = normalize_to_duckdb(settings.raw_parquet_path, settings.database_path)
    print(
        f"Kept {normalized.rows_out:,} of {normalized.rows_in:,} rows "
        f"in {normalized.elapsed_seconds:.1f}s "
        f"({_format_bytes(normalized.database_bytes)} on disk)"
    )
    return 0


def _run_index() -> int:
    settings = load_settings()

    con = duckdb.connect(str(settings.database_path), read_only=True)
    try:
        cutoff = con.execute(
            "SELECT max(dateNotification) FROM marches"
        ).fetchone()[0] - timedelta(days=INDEX_SCOPE_WINDOW_DAYS)
        rows = con.execute(
            "SELECT uid, objet FROM marches WHERE dateNotification >= ?", [cutoff]
        ).fetchall()
    finally:
        con.close()

    ids = [row[0] for row in rows]
    texts = [row[1] or "" for row in rows]
    print(
        f"Encoding {len(ids):,} markets notified since {cutoff} "
        f"(last {INDEX_SCOPE_WINDOW_DAYS} days)..."
    )

    encoder = load_encoder()
    start = time.perf_counter()
    vectors = embed_texts(texts, encoder)
    elapsed = time.perf_counter() - start

    save_index(
        settings.vector_index_path,
        ids,
        vectors,
        metadata={
            "scope_cutoff_date": cutoff.isoformat(),
            "scope_window_days": INDEX_SCOPE_WINDOW_DAYS,
            "row_count": len(ids),
            "elapsed_seconds": elapsed,
        },
    )
    print(
        f"Indexed {len(ids):,} markets in {elapsed:.1f}s "
        f"-> {settings.vector_index_path}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "ingest":
        return _run_ingest(skip_download=args.skip_download)
    if args.command == "index":
        return _run_index()
    print(f"'{args.command}' is not implemented yet — see SPEC.md for the corresponding lot.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
