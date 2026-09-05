"""Command-line entry point for decp-copilot.

Subcommands are wired up here as each lot lands (see SPEC.md section 6);
"index" and "serve" only describe what is coming so far.
"""

from __future__ import annotations

import argparse

from decp.config import load_settings
from decp.ingest.download import download_parquet
from decp.ingest.normalize import normalize_to_duckdb

_PLANNED_COMMANDS = {
    "index": "Build the hybrid search index (lot 2).",
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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "ingest":
        return _run_ingest(skip_download=args.skip_download)
    print(f"'{args.command}' is not implemented yet — see SPEC.md for the corresponding lot.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
