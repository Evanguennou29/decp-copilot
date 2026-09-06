from pathlib import Path

import duckdb
import numpy as np
from fastapi.testclient import TestClient

from decp.api.app import Dependencies, create_app
from decp.config import load_settings
from decp.index.store import VectorIndex
from decp.ingest.normalize import normalize_to_duckdb

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


def _build_deps(tmp_path, monkeypatch, *, generator=None):
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
        generator=generator,
    )


def test_health_reports_no_generation_without_key(tmp_path, monkeypatch):
    """The no-key path is the default a fresh clone sees: /health must say so."""
    deps = _build_deps(tmp_path, monkeypatch, generator=None)
    client = TestClient(create_app(deps))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "generation_available": False}


def test_health_reports_generation_available_with_a_generator(tmp_path, monkeypatch):
    deps = _build_deps(tmp_path, monkeypatch, generator=lambda prompt: "x")
    client = TestClient(create_app(deps))

    response = client.get("/health")

    assert response.json()["generation_available"] is True


def test_search_endpoint_returns_matches(tmp_path, monkeypatch):
    deps = _build_deps(tmp_path, monkeypatch)
    client = TestClient(create_app(deps))

    response = client.get("/search", params={"q": "nettoyage des locaux municipaux"})

    assert response.status_code == 200
    body = response.json()
    assert body["results"]
    assert body["results"][0]["uid"] == "12345678900011M001"


def test_search_endpoint_returns_parsed_filters(tmp_path, monkeypatch):
    deps = _build_deps(tmp_path, monkeypatch)
    client = TestClient(create_app(deps))

    response = client.get(
        "/search", params={"q": "moins de 50000 euros dans le Finistère"}
    )

    assert response.status_code == 200
    filters = response.json()["filters"]
    assert filters["montant_max"] == 50000.0
    assert filters["departement_code"] == "29"


def test_search_endpoint_rejects_empty_question(tmp_path, monkeypatch):
    deps = _build_deps(tmp_path, monkeypatch)
    client = TestClient(create_app(deps))

    response = client.get("/search", params={"q": ""})

    assert response.status_code == 422


def test_answer_endpoint_degraded_without_generator(tmp_path, monkeypatch):
    """The no-key mode: no answer text, but real markets and stats."""
    deps = _build_deps(tmp_path, monkeypatch, generator=None)
    client = TestClient(create_app(deps))

    response = client.get("/answer", params={"q": "nettoyage des locaux municipaux"})

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "degraded"
    assert body["answer"] is None
    assert body["markets"]
    assert body["markets"][0]["uid"] == "12345678900011M001"
    assert body["stats"]["count"] >= 1
    assert body["stats"]["montant_total"] > 0


def test_answer_endpoint_degraded_with_no_matches_returns_empty_stats(tmp_path, monkeypatch):
    deps = _build_deps(tmp_path, monkeypatch, generator=None)
    client = TestClient(create_app(deps))

    response = client.get("/answer", params={"q": "marchés de moins de 100 euros"})

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "degraded"
    assert body["markets"] == []
    assert body["stats"]["count"] == 0
    assert body["stats"]["montant_total"] == 0.0


def test_answer_endpoint_generated_with_citation(tmp_path, monkeypatch):
    def fake_generator(prompt):
        return "Le marché [uid: 12345678900011M001] coûte 45 000 euros."

    deps = _build_deps(tmp_path, monkeypatch, generator=fake_generator)
    client = TestClient(create_app(deps))

    response = client.get("/answer", params={"q": "nettoyage des locaux municipaux"})

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "generated"
    assert "12345678900011M001" in body["answer"]
    assert body["markets"]
    assert body["stats"]["count"] >= 1
    assert "filters" in body


def test_answer_endpoint_falls_back_to_degraded_when_generator_raises(tmp_path, monkeypatch):
    """A generation backend failure (network timeout, connection error...)
    must not 500 the whole request — found by hand-testing the frontend
    against a real, slow local Ollama call that timed out."""

    def failing_generator(prompt):
        raise TimeoutError("Ollama did not respond in time")

    deps = _build_deps(tmp_path, monkeypatch, generator=failing_generator)
    client = TestClient(create_app(deps))

    response = client.get("/answer", params={"q": "nettoyage des locaux municipaux"})

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "degraded"
    assert body["answer"] is None
    assert body["stats"]["count"] >= 1


def test_answer_endpoint_falls_back_to_degraded_when_uncited(tmp_path, monkeypatch):
    """SPEC.md section 7: an uncited generation is rejected, not shown."""

    def fake_generator(prompt):
        return "Réponse générique sans référence à un marché précis."

    deps = _build_deps(tmp_path, monkeypatch, generator=fake_generator)
    client = TestClient(create_app(deps))

    response = client.get("/answer", params={"q": "nettoyage des locaux municipaux"})

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "degraded"
    assert body["answer"] is None
    assert body["stats"]["count"] >= 1
