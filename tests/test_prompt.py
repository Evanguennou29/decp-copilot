from datetime import date

from decp.answer.prompt import build_prompt
from decp.retrieval.search import SearchResult


def _result(uid="U1", montant=1000.0):
    return SearchResult(
        uid=uid,
        acheteur_nom="Commune X",
        objet="Nettoyage des locaux",
        montant=montant,
        date_notification=date(2024, 6, 1),
        departement_nom="Finistère",
        score=1.0,
    )


def test_build_prompt_includes_question():
    prompt = build_prompt("Quel est le prix ?", [_result()])
    assert "Quel est le prix ?" in prompt


def test_build_prompt_includes_market_uid_and_montant():
    prompt = build_prompt("question", [_result(uid="U1", montant=45000.0)])
    assert "U1" in prompt
    assert "45 000" in prompt


def test_build_prompt_demands_citations():
    prompt = build_prompt("question", [_result()])
    assert "uid" in prompt.lower()
    assert "cite" in prompt.lower()


def test_build_prompt_handles_no_results():
    prompt = build_prompt("question", [])
    assert "aucun marché" in prompt.lower()


def test_build_prompt_handles_missing_montant_gracefully():
    prompt = build_prompt("question", [_result(montant=None)])
    assert "montant inconnu" in prompt
