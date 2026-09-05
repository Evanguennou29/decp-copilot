"""FastAPI application: hybrid search plus generation, degraded without a key.

``create_app`` takes an explicit ``Dependencies`` bundle rather than
loading anything itself, so tests can inject a tiny fixture-built database,
a fake encoder, a tiny vector index, and either a fake generator or
``None`` — never the real, network- or model-loading path.
``load_real_dependencies`` is that real path, used only by ``decp serve``.

The no-key mode (``deps.generator is None``) is not a lesser code path: it
is what an unconfigured clone actually serves by default, so ``/answer``
always returns comparable markets and statistics, with or without a
generator — see ``decp.answer.degraded``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from fastapi import FastAPI, Query

from decp.answer.degraded import build_degraded_answer
from decp.answer.generate import Generator, UncitedAnswerError, generate_answer, load_generator
from decp.config import Settings, load_settings
from decp.index.embed import Encoder, load_encoder
from decp.index.store import VectorIndex, load_index
from decp.retrieval.search import SearchResult, search


@dataclass(frozen=True)
class Dependencies:
    settings: Settings
    database_path: Path
    encoder: Encoder
    vector_index: VectorIndex
    generator: Generator | None


def load_real_dependencies() -> Dependencies:
    """Load the real database, model, index, and generator. Never used in tests."""
    settings = load_settings()

    if not settings.database_path.exists():
        raise FileNotFoundError(
            f"No DuckDB database at {settings.database_path} — run `python -m decp ingest` first."
        )
    if not settings.vector_index_path.exists():
        raise FileNotFoundError(
            f"No vector index at {settings.vector_index_path} — run `python -m decp index` first."
        )

    return Dependencies(
        settings=settings,
        database_path=settings.database_path,
        encoder=load_encoder(),
        vector_index=load_index(settings.vector_index_path),
        generator=load_generator(settings),
    )


def _market_dict(result: SearchResult) -> dict:
    data = asdict(result)
    if data.get("date_notification") is not None:
        data["date_notification"] = result.date_notification.isoformat()
    return data


def create_app(deps: Dependencies) -> FastAPI:
    app = FastAPI(
        title="decp-copilot",
        description=(
            "Recherche hybride et synthèse citée sur les marchés publics "
            "français attribués (DECP)."
        ),
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "generation_available": deps.generator is not None}

    @app.get("/search")
    def search_endpoint(q: str = Query(..., min_length=1), top_k: int = 10) -> dict:
        results = search(
            q,
            database_path=deps.database_path,
            vector_index=deps.vector_index,
            encoder=deps.encoder,
            top_k=top_k,
        )
        return {"results": [_market_dict(r) for r in results]}

    @app.get("/answer")
    def answer_endpoint(q: str = Query(..., min_length=1), top_k: int = 10) -> dict:
        results = search(
            q,
            database_path=deps.database_path,
            vector_index=deps.vector_index,
            encoder=deps.encoder,
            top_k=top_k,
        )

        if deps.generator is not None:
            try:
                answer_text = generate_answer(q, results, deps.generator)
                return {
                    "mode": "generated",
                    "answer": answer_text,
                    "markets": [_market_dict(r) for r in results],
                }
            except UncitedAnswerError:
                pass  # never surface an uncited answer: fall through to degraded

        degraded = build_degraded_answer(results)
        return {
            "mode": "degraded",
            "answer": None,
            "markets": [_market_dict(r) for r in degraded.markets],
            "stats": asdict(degraded.stats),
        }

    return app
