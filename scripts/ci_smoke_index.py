"""CI smoke test: build a tiny end-to-end index from fixtures.

Exercises the real chain (normalize -> embed with the real model -> persist
the vector index) end to end, unlike the pytest suite which fakes the
encoder to stay network-free (SPEC.md section 7: "construction d'un index
minuscule depuis des fixtures pour valider la chaîne complète").
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import duckdb

from decp.index.embed import embed_texts, load_encoder
from decp.index.store import save_index
from decp.ingest.normalize import normalize_to_duckdb

FIXTURE_PATH = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "decp_sample.parquet"


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        database_path = tmp_path / "decp.duckdb"
        index_path = tmp_path / "decp.index.npz"

        normalize_to_duckdb(FIXTURE_PATH, database_path)

        con = duckdb.connect(str(database_path), read_only=True)
        rows = con.execute("SELECT uid, objet FROM marches").fetchall()
        con.close()

        ids = [row[0] for row in rows]
        texts = [row[1] or "" for row in rows]

        encoder = load_encoder()
        vectors = embed_texts(texts, encoder)
        save_index(index_path, ids, vectors, metadata={"row_count": len(ids)})

        assert index_path.exists()
        assert vectors.shape[0] == len(ids)
        print(f"Built a tiny index with {len(ids)} vectors from fixtures: {index_path.name}")


if __name__ == "__main__":
    main()
