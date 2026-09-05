from datetime import date
from pathlib import Path

import numpy as np

from decp.index.store import VectorIndex
from decp.ingest.normalize import normalize_to_duckdb
from decp.retrieval.search import search, semantic_search

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


def _build_index(database_path, *, metadata=None):
    import duckdb

    con = duckdb.connect(str(database_path), read_only=True)
    rows = con.execute("SELECT uid, objet FROM marches").fetchall()
    con.close()
    ids = [row[0] for row in rows]
    vectors = _fake_encoder([row[1] for row in rows])
    return VectorIndex(ids=ids, vectors=vectors, metadata=metadata or {})


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


def test_search_with_no_filters_falls_back_to_index_cutoff_date(tmp_path, monkeypatch):
    """A fully unfiltered question must draw its candidate pool using the
    index's own scope_cutoff_date, not the full table's plain recency
    LIMIT: at real scale (~780k rows), that LIMIT was found to reach back
    only ~15 days out of the indexed window's 60, silently hiding most of
    the indexed corpus from an unfiltered query. (Passing the indexed uids
    themselves as a query parameter was tried first, but DuckDB was
    measured to take 20+ seconds binding a ~20k-element list — see
    README.md, "Indexed corpus scope".)"""
    database_path = tmp_path / "decp.duckdb"
    normalize_to_duckdb(FIXTURE_PATH, database_path)
    vector_index = _build_index(database_path, metadata={"scope_cutoff_date": "2024-01-01"})

    import decp.retrieval.search as search_module

    calls = []
    real_fetch_candidates = search_module.fetch_candidates

    def spy_fetch_candidates(con, filters, **kwargs):
        calls.append((filters, kwargs))
        return real_fetch_candidates(con, filters, **kwargs)

    monkeypatch.setattr(search_module, "fetch_candidates", spy_fetch_candidates)

    search(
        "nettoyage des locaux municipaux",
        database_path=database_path,
        vector_index=vector_index,
        encoder=_fake_encoder,
    )

    filters_used, kwargs_used = calls[0]
    assert filters_used.date_min == date(2024, 1, 1)
    assert kwargs_used["limit"] == max(search_module.MAX_CANDIDATES, len(vector_index.ids))


def test_search_with_filters_does_not_apply_the_cutoff_fallback(tmp_path, monkeypatch):
    """As soon as any structured filter is present, the plain candidate
    search still applies unmodified — the cutoff-date fallback is only for
    the fully-unfiltered case."""
    database_path = tmp_path / "decp.duckdb"
    normalize_to_duckdb(FIXTURE_PATH, database_path)
    vector_index = _build_index(database_path, metadata={"scope_cutoff_date": "2024-01-01"})

    import decp.retrieval.search as search_module

    calls = []
    real_fetch_candidates = search_module.fetch_candidates

    def spy_fetch_candidates(con, filters, **kwargs):
        calls.append((filters, kwargs))
        return real_fetch_candidates(con, filters, **kwargs)

    monkeypatch.setattr(search_module, "fetch_candidates", spy_fetch_candidates)

    search(
        "marchés en Ille-et-Vilaine",
        database_path=database_path,
        vector_index=vector_index,
        encoder=_fake_encoder,
    )

    filters_used, kwargs_used = calls[0]
    assert filters_used.date_min is None
    assert kwargs_used == {"limit": search_module.MAX_CANDIDATES}


def test_semantic_search_ranks_by_similarity_alone(tmp_path):
    database_path = tmp_path / "decp.duckdb"
    normalize_to_duckdb(FIXTURE_PATH, database_path)
    vector_index = _build_index(database_path)

    ranked_ids = semantic_search(
        "nettoyage des locaux municipaux", vector_index=vector_index, encoder=_fake_encoder
    )

    assert ranked_ids
    assert ranked_ids[0] == "12345678900011M001"


def test_semantic_search_ignores_structured_filters_in_the_question(tmp_path):
    """Unlike search(), a montant/département mention is just more text —
    semantic_search never applies it as a filter."""
    database_path = tmp_path / "decp.duckdb"
    normalize_to_duckdb(FIXTURE_PATH, database_path)
    vector_index = _build_index(database_path)

    ranked_ids = semantic_search(
        "marchés de moins de 100 euros", vector_index=vector_index, encoder=_fake_encoder
    )

    # search() with this question returns nothing (every market is over
    # 100 euros); semantic_search still ranks the whole indexed corpus —
    # 5 here since, unlike fetch_candidates, it doesn't dedupe co-contractor
    # rows sharing a uid (the real index build does dedupe, via DISTINCT).
    assert len(ranked_ids) == 5


def test_semantic_search_empty_index_returns_empty(tmp_path):
    empty_index = VectorIndex(ids=[], vectors=np.zeros((0, 32), dtype=np.float32))

    assert semantic_search("question", vector_index=empty_index, encoder=_fake_encoder) == []
