# decp-copilot

Retrieval-augmented search over French public procurement awards (DECP), with measured retrieval quality.

> **Status:** lot 0 (project skeleton) — ingestion, search, generation, evaluation and the frontend land in the following lots. See `SPEC.md` for the full plan.

## Planned contents

Once later lots land, this README will follow the plan in `SPEC.md` section 5:
evaluation results table, problem statement, architecture, quickstart
(including the no-API-key mode), data source and licence, evaluation
methodology, known limitations, and licence.

## Development

```bash
make install   # pip install -e ".[dev]"
make lint      # ruff check .
make test      # pytest
```

No API key is required to install, lint, or test this project.

## Licence

MIT — see `LICENSE`. The DECP dataset itself is published under the
Licence Ouverte 2.0 (Etalab); the exact terms and link are documented here
starting at lot 1.
