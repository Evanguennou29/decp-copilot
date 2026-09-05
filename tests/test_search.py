from pathlib import Path

import numpy as np

from decp.index.store import VectorIndex
from decp.ingest.normalize import normalize_to_duckdb
from decp.retrieval.search import search

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "decp_sample.parquet"


def _fake_encoder(texts):
    """Deterministic bag-of-words hashing encoder, standing in for the real
    sentence-transformers model so tests never touch the network."""
    dim = 32
    vectors = np.zeros((len(texts), dim), dtype=np.float32)
    for i, text in enumerate(texts):
        for token in text.lower().split():
            vectors[i, hash(token) % dim] += 1.0
        norm = np.linalg.norm(vectors[i])
        if norm:
            vectors[i] /= norm
    return vectors


def _build_index(database_path):
    import duckdb

    con = duckdb.connect(str(database_path), read_only=True)
    rows = con.execute("SELECT uid, objet FROM marches").fetchall()
    con.close()
    ids = [row[0] for row in rows]
    vectors = _fake_encoder([row[1] for row in rows])
    return VectorIndex(ids=ids, vectors=vectors)


def test_search_ranks_exact_lexical_and_semantic_match_first(tmp_path):
    database_path = tmp_path / "decp.duckdb"
    normalize_to_duckdb(FIXTURE_PATH, database_path)
    vector_index = _build_index(database_path)

    results = search(
        "nettoyage des locaux municipaux",
        database_path=database_path,
        vector_index=vector_index,
        encoder=_fake_encoder,
    )

    assert results
    assert results[0].uid == "12345678900011M001"


def test_search_departement_filter_narrows_results(tmp_path):
    database_path = tmp_path / "decp.duckdb"
    normalize_to_duckdb(FIXTURE_PATH, database_path)
    vector_index = _build_index(database_path)

    results = search(
        "marchés en Ille-et-Vilaine",
        database_path=database_path,
        vector_index=vector_index,
        encoder=_fake_encoder,
    )

    assert results
    assert all(r.departement_nom == "Ille-et-Vilaine" for r in results)


def test_search_montant_max_filter_excludes_expensive_markets(tmp_path):
    database_path = tmp_path / "decp.duckdb"
    normalize_to_duckdb(FIXTURE_PATH, database_path)
    vector_index = _build_index(database_path)

    results = search(
        "marchés de moins de 50000 euros",
        database_path=database_path,
        vector_index=vector_index,
        encoder=_fake_encoder,
    )

    assert results
    assert all(r.montant <= 50000 for r in results)


def test_search_returns_empty_when_no_candidates_match_filters(tmp_path):
    database_path = tmp_path / "decp.duckdb"
    normalize_to_duckdb(FIXTURE_PATH, database_path)
    vector_index = _build_index(database_path)

    results = search(
        "marchés de moins de 100 euros",
        database_path=database_path,
        vector_index=vector_index,
        encoder=_fake_encoder,
    )

    assert results == []


def test_search_falls_back_to_recency_when_no_text_signal(tmp_path):
    database_path = tmp_path / "decp.duckdb"
    normalize_to_duckdb(FIXTURE_PATH, database_path)
    empty_index = VectorIndex(ids=[], vectors=np.zeros((0, 32), dtype=np.float32))

    results = search(
        "xyzabc",
        database_path=database_path,
        vector_index=empty_index,
        encoder=_fake_encoder,
    )

    # 5 fixture rows but only 4 distinct markets: two rows share a uid
    # (co-contractors on the same award), and fetch_candidates keys by uid.
    assert len(results) == 4
