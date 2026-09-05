from decp.retrieval.hybrid import bm25_scores, reciprocal_rank_fusion, tokenize


def test_tokenize_lowercases_and_splits_on_punctuation():
    assert tokenize("Nettoyage, des locaux (municipaux) !") == [
        "nettoyage",
        "des",
        "locaux",
        "municipaux",
    ]


def test_bm25_scores_ranks_exact_match_higher():
    documents = {
        "a": "nettoyage des locaux municipaux",
        "b": "construction d'une médiathèque",
        "c": "nettoyage des espaces verts",
    }
    scores = bm25_scores("nettoyage locaux", documents)
    assert scores["a"] > scores["c"] > scores["b"] == 0.0


def test_bm25_scores_empty_query_gives_zero():
    documents = {"a": "nettoyage des locaux"}
    scores = bm25_scores("", documents)
    assert scores == {"a": 0.0}


def test_bm25_scores_empty_documents():
    assert bm25_scores("nettoyage", {}) == {}


def test_reciprocal_rank_fusion_favors_docs_ranked_high_in_both_lists():
    lexical = ["b", "a", "c"]
    semantic = ["a", "b", "c"]
    fused = reciprocal_rank_fusion([lexical, semantic])
    fused_ids = [doc_id for doc_id, _ in fused]
    assert fused_ids[0] in ("a", "b")
    assert set(fused_ids) == {"a", "b", "c"}


def test_reciprocal_rank_fusion_includes_docs_from_either_list():
    fused = dict(reciprocal_rank_fusion([["a"], ["b"]]))
    assert set(fused) == {"a", "b"}
    assert fused["a"] == fused["b"]


def test_reciprocal_rank_fusion_empty_lists():
    assert reciprocal_rank_fusion([[], []]) == []
