# decp-copilot

Retrieval-augmented search over French public procurement awards (DECP), with measured retrieval quality.

> **Status:** lot 3 (API and generation) — evaluation and the frontend land in the following lots. See `SPEC.md` for the full plan.

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

## Indexed corpus scope (lot 2 criterion)

Hybrid search needs an embedding for every market's `objet`, and encoding
is CPU-only (no paid API, no GPU — SPEC.md section 1). Before deciding what
to index, `scripts/benchmark_embedding.py` measured real throughput against
the lot 1 corpus, reused for search: **~86 documents/second** for
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` on this
machine (single-call batches; see the engineering note below for why an
earlier chunked measurement looked ~6x slower). At that rate, the full
lot 1 corpus (781,439 rows) would take **~2.5 hours** to encode — far past
the "a few minutes, not hours" budget the spec sets.

**Decision:** index only markets notified in the **last 60 days**, recomputed
at index-build time from the corpus's own most recent date (not a fixed
calendar date, since the source refreshes daily). This is also the more
useful scope for the product itself: a PME pricing a bid today cares most
about recent comparable awards, not one from early 2024. Structured filters
(montant, département, date, type, CPV) are **not** limited by this window —
they still run against the full `marches` table; only semantic ranking is
restricted to what has been embedded (`src/decp/retrieval/search.py`).

A brute-force, in-memory cosine-similarity index (`src/decp/index/store.py`,
plain NumPy, persisted as `.npz`) is used instead of an ANN library like
FAISS: at this deliberately small scale (tens of thousands of 384-dim
vectors), brute force runs in single-digit milliseconds, and FAISS would
only add a dependency without buying anything.

**Engineering note:** the real, full-scale build first measured at 6,135s
(~102 min) for 22,465 rows — 40x slower than the sample benchmark predicted.
The cause was `embed_texts`'s outer batching: calling the real model's
`.encode()` repeatedly over small chunks (256 rows) carries a large,
roughly fixed per-call overhead in this environment (~15s), so many small
calls cost far more than a couple of large ones. Raising the default outer
batch size to 10,000 (so realistic corpus sizes fit in one or two calls)
fixed it; the measurement below is from the corrected code.

Real run, reproducible with `python -m decp index` (or `make index`), on 2026-09-05:

| Metric | Value |
|---|---|
| Indexed window | markets notified in the last 60 days (cutoff computed from the corpus's own max date) |
| Rows indexed | 22,465 |
| Encoding wall time | 290.9 s (~4.8 min) |
| Vector index size on disk | `data/index/decp.index.npz` |
| End-to-end search latency (query encode + structured filter + BM25 + semantic + fusion) | 168–389 ms per query, measured over several real questions |

## API and generation (lot 3)

`src/decp/api/app.py` exposes two endpoints over the hybrid search from
lot 2: `GET /search` (raw ranked markets) and `GET /answer` (search plus,
when available, a cited natural-language answer). `GET /health` reports
whether generation is available.

**The no-key mode is the default, not a fallback bolted on afterwards**
(SPEC.md section 1: "un mode nominal documenté, pas une panne"). With an
empty `.env`, `/answer` returns the matching markets and their statistics
(count, montant total/min/max/moyen/médian) computed by
`src/decp/answer/degraded.py` — no LLM call, no API key, nothing to
configure. This is exactly what a recruiter cloning the repo without
touching `.env` will see.

When a generator *is* available (see below), `/answer` instead returns a
drafted answer — but only if it cites at least one market's `uid`.
`decp.answer.generate.generate_answer` builds the prompt (which explicitly
demands `[uid: ...]` citations for every figure), calls the model, and
raises `UncitedAnswerError` if no known `uid` appears in the response; the
API catches that and **falls back to the degraded answer** rather than
show an answer with unverifiable figures (SPEC.md section 7). This is
checked directly: `tests/test_generate.py` feeds a fake generator an
uncited response and asserts the error is raised, and
`tests/test_app.py::test_answer_endpoint_falls_back_to_degraded_when_uncited`
checks the same thing through the actual HTTP endpoint.

Generation resolution, in order (`decp.answer.generate.load_generator`):
1. an `OPENAI_API_KEY` — sent to `OPENAI_BASE_URL` (default `api.openai.com`,
   but any OpenAI-compatible chat completions endpoint works, e.g. Groq's
   free tier — see `.env.example`);
2. otherwise, a locally reachable Ollama server (`OLLAMA_BASE_URL`, default
   `localhost:11434`) — free, no key, but needs Ollama installed and running;
3. otherwise, the degraded mode above.

**Explicit verification, with a genuinely empty `.env`** (2026-09-05), against
the real lot 1/2 data — both generation branches actually exercised, not just unit-tested:

| Scenario | `GET /health` | `GET /answer` |
|---|---|---|
| Empty `.env`, no Ollama reachable (`OLLAMA_BASE_URL` pointed at a closed port) | `generation_available: false` | `mode: "degraded"`, real markets + stats, `answer: null` |
| Empty `.env`, a local Ollama server reachable (this machine has one) | `generation_available: true` | `mode: "generated"`, a real `llama3.2` answer citing `[uid: ...]`, validated by `generate_answer` |

Both started and answered correctly with `python -m decp serve` and no
`OPENAI_API_KEY` set anywhere — the lot 3 criterion.

## Development

```bash
make install   # pip install -e ".[dev]"
make lint      # ruff check .
make test      # pytest
make ingest    # python -m decp ingest — downloads and normalizes the DECP dataset
make index     # python -m decp index — encodes the recent-window corpus and builds the vector index
make serve     # python -m decp serve — runs the API on http://0.0.0.0:8000
```

No API key is required to install, lint, test, ingest data, build the
index, or serve the API — see "API and generation" above.

## Licence

MIT — see `LICENSE`, for the code in this repository. The DECP dataset
itself is published under the Licence Ouverte 2.0 (Etalab), see above.
