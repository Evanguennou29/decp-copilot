"""Hybrid search: structured filters (DuckDB) + lexical (BM25) + semantic
(vector index), fused by reciprocal rank.

Structured filters run against the full ingested corpus (the `marches`
table from lot 1, ~780k markets notified since 2024) — montant,
département, date, and type are exact SQL predicates and stay unrestricted.
Semantic ranking only covers markets present in the vector index, i.e. the
recent window chosen in ``decp.index.embed`` (see README.md, "Indexed
corpus scope"). Lexical (BM25) ranking runs over the same structured-
filtered candidates as the semantic one, so a market outside the indexed
window can still surface by keyword match — it just gets no semantic score.

``MAX_CANDIDATES`` bounds how many structured-filter matches are pulled
into Python for lexical/semantic scoring (most recent first), so a broad
or unfiltered question still returns in well under a second.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import duckdb

from decp.index.embed import Encoder
from decp.index.store import VectorIndex
from decp.retrieval.filters import Filters, extract_filters
from decp.retrieval.hybrid import bm25_scores, reciprocal_rank_fusion

MAX_CANDIDATES = 2000
TOP_K = 10


@dataclass(frozen=True)
class SearchResult:
    uid: str
    acheteur_nom: str
    objet: str
    montant: float | None
    date_notification: date | None
    departement_nom: str | None
    score: float


def _build_where(filters: Filters) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if filters.montant_min is not None:
        clauses.append("montant >= ?")
        params.append(filters.montant_min)
    if filters.montant_max is not None:
        clauses.append("montant <= ?")
        params.append(filters.montant_max)
    if filters.departement_code is not None:
        clauses.append("acheteur_departement_code = ?")
        params.append(filters.departement_code)
    if filters.date_min is not None:
        clauses.append("dateNotification >= ?")
        params.append(filters.date_min)
    if filters.date_max is not None:
        clauses.append("dateNotification <= ?")
        params.append(filters.date_max)
    if filters.marche_type is not None:
        clauses.append("type = ?")
        params.append(filters.marche_type)
    if filters.code_cpv is not None:
        clauses.append("codeCPV = ?")
        params.append(filters.code_cpv)
    where_sql = " AND ".join(clauses) if clauses else "TRUE"
    return where_sql, params


def fetch_candidates(
    con: duckdb.DuckDBPyConnection,
    filters: Filters,
    *,
    limit: int = MAX_CANDIDATES,
) -> dict[str, dict[str, Any]]:
    """Rows matching ``filters``, most recently notified first, capped at ``limit``.

    Keyed by ``uid``, so a market with several co-contractors (several rows
    sharing the same uid, see ``decp.ingest.normalize``) collapses to a
    single candidate rather than appearing once per co-contractor.
    """
    where_sql, params = _build_where(filters)
    query = (
        "SELECT uid, acheteur_nom, objet, montant, dateNotification, acheteur_departement_nom "
        f"FROM marches WHERE {where_sql} ORDER BY dateNotification DESC LIMIT {int(limit)}"
    )
    rows = con.execute(query, params).fetchall()
    return {
        row[0]: {
            "uid": row[0],
            "acheteur_nom": row[1],
            "objet": row[2] or "",
            "montant": row[3],
            "date_notification": row[4],
            "departement_nom": row[5],
        }
        for row in rows
    }


def search(
    question: str,
    *,
    database_path: Path,
    vector_index: VectorIndex,
    encoder: Encoder,
    top_k: int = TOP_K,
) -> list[SearchResult]:
    filters = extract_filters(question)
    con = duckdb.connect(str(database_path), read_only=True)
    try:
        candidates = fetch_candidates(con, filters)
    finally:
        con.close()

    if not candidates:
        return []

    lexical_scores = bm25_scores(
        question, {uid: row["objet"] for uid, row in candidates.items()}
    )
    lexical_ranking = [
        uid
        for uid, score in sorted(lexical_scores.items(), key=lambda kv: kv[1], reverse=True)
        if score > 0
    ]

    query_vector = encoder([question])[0]
    semantic_ranking = [
        uid
        for uid, _ in vector_index.search(
            query_vector, top_k=len(candidates), candidate_ids=set(candidates)
        )
    ]

    fused = reciprocal_rank_fusion([lexical_ranking, semantic_ranking])
    if fused:
        ranked_ids = [uid for uid, _ in fused[:top_k]]
        scores = dict(fused)
    else:
        # No lexical or semantic signal at all (e.g. a purely structured
        # query whose words don't overlap any objet): fall back to the
        # structured-filter order (most recent first) rather than nothing.
        ranked_ids = list(candidates)[:top_k]
        scores = dict.fromkeys(ranked_ids, 0.0)

    return [SearchResult(score=scores[uid], **candidates[uid]) for uid in ranked_ids]
