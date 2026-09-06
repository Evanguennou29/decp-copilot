import asyncio
import sys
from pathlib import Path

import duckdb
import numpy as np

from decp.api.app import Dependencies
from decp.config import load_settings
from decp.index.store import VectorIndex
from decp.ingest.normalize import normalize_to_duckdb

# mcp/server.py lives outside src/decp (it's a standalone script, not part
# of the installed package — see README.md, "MCP server"). Importing it by
# path, rather than adding the repo root to sys.path, avoids any ambiguity
# with the installed `mcp` package itself.
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp"))
import server as mcp_server  # noqa: E402

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "decp_sample.parquet"


def _fake_encoder(texts):
    """Deterministic bag-of-words hashing encoder — stands in for the real
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


def _build_deps(tmp_path, monkeypatch):
    monkeypatch.setenv("DECP_DATA_DIR", str(tmp_path))
    database_path = tmp_path / "decp.duckdb"
    normalize_to_duckdb(FIXTURE_PATH, database_path)

    con = duckdb.connect(str(database_path), read_only=True)
    rows = con.execute("SELECT uid, objet FROM marches").fetchall()
    con.close()
    ids = [row[0] for row in rows]
    vectors = _fake_encoder([row[1] for row in rows])
    vector_index = VectorIndex(ids=ids, vectors=vectors)

    return Dependencies(
        settings=load_settings(),
        database_path=database_path,
        encoder=_fake_encoder,
        vector_index=vector_index,
        generator=None,
    )


def test_search_marches_returns_matching_uid(tmp_path, monkeypatch):
    deps = _build_deps(tmp_path, monkeypatch)

    results = mcp_server.search_marches(deps, "nettoyage des locaux municipaux")

    assert results
    assert results[0]["uid"] == "12345678900011M001"
    assert results[0]["montant"] == 45000.0


def test_search_marches_applies_structured_filters(tmp_path, monkeypatch):
    deps = _build_deps(tmp_path, monkeypatch)

    results = mcp_server.search_marches(deps, "marchés en Ille-et-Vilaine")

    assert results
    assert all(r["departement_nom"] == "Ille-et-Vilaine" for r in results)


def test_get_marche_returns_known_market(tmp_path, monkeypatch):
    deps = _build_deps(tmp_path, monkeypatch)

    market = mcp_server.get_marche(deps, "12345678900011M001")

    assert market["uid"] == "12345678900011M001"
    assert market["montant"] == 45000.0
    assert market["date_notification"] == "2024-06-01"


def test_get_marche_unknown_uid_returns_error(tmp_path, monkeypatch):
    deps = _build_deps(tmp_path, monkeypatch)

    market = mcp_server.get_marche(deps, "does-not-exist")

    assert "error" in market


def test_create_server_registers_both_tools(tmp_path, monkeypatch):
    deps = _build_deps(tmp_path, monkeypatch)

    server = mcp_server.create_server(deps)
    tools = asyncio.run(server.list_tools())
    tool_names = {tool.name for tool in tools}

    assert "search_marches_tool" in tool_names
    assert "get_marche_tool" in tool_names
