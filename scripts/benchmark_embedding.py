"""One-off benchmark: measure CPU encoding throughput on a real sample of
`objet` text from the ingested DECP corpus, to size the lot 2 indexed
corpus. Not part of the application; run manually:
``python scripts/benchmark_embedding.py``.
"""

from __future__ import annotations

import random
import time
from pathlib import Path

import duckdb

from decp.index.embed import DEFAULT_MODEL_NAME

DATABASE_PATH = Path(__file__).resolve().parent.parent / "data" / "decp.duckdb"
SAMPLE_SIZES = (200, 1000)


def main() -> None:
    con = duckdb.connect(str(DATABASE_PATH), read_only=True)
    total_rows = con.execute("SELECT count(*) FROM marches").fetchone()[0]
    print(f"Full corpus: {total_rows:,} rows")

    from sentence_transformers import SentenceTransformer

    print(f"Loading model {DEFAULT_MODEL_NAME}...")
    model = SentenceTransformer(DEFAULT_MODEL_NAME)

    random.seed(42)
    for sample_size in SAMPLE_SIZES:
        rows = con.execute(
            f"SELECT objet FROM marches USING SAMPLE {int(sample_size)} ROWS (reservoir, 42)"
        ).fetchall()
        texts = [r[0] or "" for r in rows][:sample_size]
        n = len(texts)

        start = time.perf_counter()
        model.encode(texts, batch_size=64, show_progress_bar=False, normalize_embeddings=True)
        elapsed = time.perf_counter() - start

        throughput = n / elapsed if elapsed else float("inf")
        full_corpus_seconds = total_rows / throughput if throughput else float("inf")
        print(
            f"sample={n:>5} elapsed={elapsed:6.2f}s "
            f"throughput={throughput:6.1f} docs/s "
            f"-> full corpus ({total_rows:,} rows) estimated at "
            f"{full_corpus_seconds / 60:.1f} min"
        )

    con.close()


if __name__ == "__main__":
    main()
