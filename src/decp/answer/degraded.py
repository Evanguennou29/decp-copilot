"""The no-LLM-key answer: comparable markets and their statistics, with no
natural-language generation.

This is not a fallback bolted on as an afterthought — per SPEC.md section
1, it is "un mode nominal documenté, pas une panne": the default an
unconfigured clone shows, and it must stay genuinely useful on its own.
"""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from dataclasses import dataclass

from decp.retrieval.search import SearchResult


@dataclass(frozen=True)
class DegradedStats:
    count: int
    montant_total: float
    montant_min: float | None
    montant_max: float | None
    montant_moyen: float | None
    montant_median: float | None


@dataclass(frozen=True)
class DegradedAnswer:
    markets: list[SearchResult]
    stats: DegradedStats


def build_degraded_answer(results: Sequence[SearchResult]) -> DegradedAnswer:
    montants = [r.montant for r in results if r.montant is not None]
    stats = DegradedStats(
        count=len(results),
        montant_total=sum(montants) if montants else 0.0,
        montant_min=min(montants) if montants else None,
        montant_max=max(montants) if montants else None,
        montant_moyen=(sum(montants) / len(montants)) if montants else None,
        montant_median=statistics.median(montants) if montants else None,
    )
    return DegradedAnswer(markets=list(results), stats=stats)
