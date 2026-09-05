from datetime import date

from decp.answer.degraded import build_degraded_answer
from decp.retrieval.search import SearchResult


def _result(uid, montant):
    return SearchResult(
        uid=uid,
        acheteur_nom="Commune X",
        objet="Nettoyage",
        montant=montant,
        date_notification=date(2024, 1, 1),
        departement_nom="Finistère",
        score=1.0,
    )


def test_build_degraded_answer_computes_stats():
    results = [_result("U1", 100.0), _result("U2", 300.0)]

    answer = build_degraded_answer(results)

    assert answer.stats.count == 2
    assert answer.stats.montant_total == 400.0
    assert answer.stats.montant_min == 100.0
    assert answer.stats.montant_max == 300.0
    assert answer.stats.montant_moyen == 200.0
    assert answer.stats.montant_median == 200.0
    assert answer.markets == results


def test_build_degraded_answer_handles_empty_results():
    answer = build_degraded_answer([])

    assert answer.stats.count == 0
    assert answer.stats.montant_total == 0.0
    assert answer.stats.montant_min is None
    assert answer.stats.montant_max is None
    assert answer.stats.montant_moyen is None
    assert answer.stats.montant_median is None


def test_build_degraded_answer_ignores_missing_montant():
    results = [_result("U1", None), _result("U2", 100.0)]

    answer = build_degraded_answer(results)

    assert answer.stats.count == 2
    assert answer.stats.montant_total == 100.0
    assert answer.stats.montant_min == 100.0
