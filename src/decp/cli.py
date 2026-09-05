"""Command-line entry point for decp-copilot.

Subcommands are wired up here as each lot lands (see SPEC.md section 6);
today they only describe what is coming.
"""

from __future__ import annotations

import argparse

_PLANNED_COMMANDS = {
    "ingest": "Download and normalize the DECP dataset (lot 1).",
    "index": "Build the hybrid search index (lot 2).",
    "serve": "Run the FastAPI application (lot 3).",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="decp", description="DECP copilot command-line interface."
    )
    subparsers = parser.add_subparsers(dest="command")
    for name, help_text in _PLANNED_COMMANDS.items():
        subparsers.add_parser(name, help=help_text)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    print(f"'{args.command}' is not implemented yet — see SPEC.md for the corresponding lot.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
