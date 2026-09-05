from datetime import date

import pytest

from decp.answer.generate import UncitedAnswerError, extract_cited_uids, generate_answer
from decp.retrieval.search import SearchResult


def _result(uid, montant=100.0):
    return SearchResult(
        uid=uid,
        acheteur_nom="Commune X",
        objet="Nettoyage",
        montant=montant,
        date_notification=date(2024, 1, 1),
        departement_nom="Finistère",
        score=1.0,
    )


def test_extract_cited_uids_finds_present_ones_in_order():
    assert extract_cited_uids("voir [uid: U2] et [uid: U1]", ["U1", "U2"]) == ["U1", "U2"]


def test_extract_cited_uids_empty_when_none_present():
    assert extract_cited_uids("réponse générique", ["U1", "U2"]) == []


def test_generate_answer_accepts_response_with_citation():
    results = [_result("U1"), _result("U2")]

    def fake_generator(prompt):
        assert "U1" in prompt  # the prompt did carry the market context
        return "Le marché [uid: U1] coûte 100 euros."

    answer = generate_answer("question", results, fake_generator)

    assert "U1" in answer


def test_generate_answer_rejects_response_without_citation():
    """SPEC.md section 7: a generated answer without a citation is rejected."""
    results = [_result("U1")]

    def fake_generator(prompt):
        return "Voici une réponse générique sans référence précise."

    with pytest.raises(UncitedAnswerError):
        generate_answer("question", results, fake_generator)


def test_generate_answer_rejects_citation_to_an_unknown_uid():
    """A uid not among the results doesn't count as a valid citation."""
    results = [_result("U1")]

    def fake_generator(prompt):
        return "Le marché [uid: U999] coûte 100 euros."

    with pytest.raises(UncitedAnswerError):
        generate_answer("question", results, fake_generator)


def test_generate_answer_with_no_results_always_rejects():
    def fake_generator(prompt):
        return "Aucun marché ne correspond à votre recherche."

    with pytest.raises(UncitedAnswerError):
        generate_answer("question", [], fake_generator)
