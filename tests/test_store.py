import numpy as np
import pytest

from decp.index.store import load_index, save_index


def test_save_and_load_round_trip(tmp_path):
    ids = ["a", "b", "c"]
    vectors = np.array([[1.0, 0.0], [0.0, 1.0], [0.70, 0.70]], dtype=np.float32)
    path = tmp_path / "index" / "decp.index.npz"

    save_index(path, ids, vectors, metadata={"row_count": 3})
    index = load_index(path)

    assert index.ids == ids
    assert index.vectors.shape == (3, 2)
    assert index.metadata == {"row_count": 3}


def test_load_index_without_metadata_defaults_to_empty_dict(tmp_path):
    path = tmp_path / "decp.index.npz"
    save_index(path, ["a"], np.zeros((1, 2), dtype=np.float32))

    index = load_index(path)

    assert index.metadata == {}


def test_search_returns_best_match_first(tmp_path):
    ids = ["a", "b", "c"]
    vectors = np.array([[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0]], dtype=np.float32)
    path = tmp_path / "decp.index.npz"
    save_index(path, ids, vectors)
    index = load_index(path)

    results = index.search(np.array([1.0, 0.0], dtype=np.float32), top_k=2)

    assert results[0][0] == "a"
    assert results[0][1] == pytest.approx(1.0)
    assert results[1][0] == "b"


def test_search_restricts_to_candidate_ids(tmp_path):
    ids = ["a", "b", "c"]
    vectors = np.array([[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]], dtype=np.float32)
    path = tmp_path / "decp.index.npz"
    save_index(path, ids, vectors)
    index = load_index(path)

    results = index.search(np.array([1.0, 0.0], dtype=np.float32), candidate_ids={"c"})

    assert [doc_id for doc_id, _ in results] == ["c"]


def test_search_empty_index_returns_empty_list(tmp_path):
    path = tmp_path / "decp.index.npz"
    save_index(path, [], np.zeros((0, 2), dtype=np.float32))
    index = load_index(path)

    assert index.search(np.array([1.0, 0.0], dtype=np.float32)) == []


def test_len_reports_number_of_vectors(tmp_path):
    path = tmp_path / "decp.index.npz"
    save_index(path, ["a", "b"], np.zeros((2, 2), dtype=np.float32))
    index = load_index(path)

    assert len(index) == 2
