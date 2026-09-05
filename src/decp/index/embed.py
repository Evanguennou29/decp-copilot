"""CPU batch encoding of market descriptions ("objet") into embeddings.

Model: ``sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`` — a
small (118M parameters, 384-dim output) multilingual Sentence-BERT model,
chosen per SPEC.md's "modèle multilingue léger exécuté en local sur CPU"
requirement. Its throughput on this corpus, measured with
``scripts/benchmark_embedding.py``, is documented in README.md alongside
the indexed corpus scope decision it drove.

``load_encoder`` is the only place that touches the network (to fetch the
model from the Hugging Face Hub the first time) or does real, possibly
slow, CPU inference. ``embed_texts`` is the pure batching logic, exercised
in tests with a fake encoder — never the real model.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np

DEFAULT_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Indexed corpus scope: measured on this project's machine (see
# scripts/benchmark_embedding.py and the embed_texts docstring below for
# why the batch size matters), this model encodes ~86 short French
# sentences/second on CPU in a single call — i.e. ~2.5h for the full lot 1
# corpus (781,439 rows), well past the "a few minutes, not hours" budget
# (SPEC.md section 1). We index only markets notified in the last 60 days
# instead: 22,465 rows as of this run, ~4.8 minutes to encode. See
# README.md, "Indexed corpus scope", for the full reasoning. This does not
# limit structured filtering (montant/département/date/type/CPV), which
# runs against the full DuckDB table regardless — only semantic ranking is
# restricted to what's been embedded (decp.retrieval.search).
INDEX_SCOPE_WINDOW_DAYS = 60

Encoder = Callable[[Sequence[str]], np.ndarray]


def load_encoder(model_name: str = DEFAULT_MODEL_NAME) -> Encoder:
    """Load a real, local, CPU sentence-transformers model as an ``Encoder``."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name, device="cpu")

    def encode(texts: Sequence[str]) -> np.ndarray:
        return model.encode(
            list(texts),
            batch_size=64,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True,
        ).astype(np.float32)

    return encode


def embed_texts(
    texts: Sequence[str],
    encoder: Encoder,
    *,
    batch_size: int = 10_000,
) -> np.ndarray:
    """Encode ``texts`` in batches of ``batch_size`` using ``encoder``.

    Batching here only exists to bound memory for pathologically large
    inputs — it is deliberately much larger than the real encoder's own
    internal ``model.encode(..., batch_size=64, ...)`` batching. Measured
    on this project's machine, each call to the real encoder carries a
    large, roughly fixed overhead (~15s) on top of actual compute time, so
    calling it many times over small chunks (the original default was 256)
    is far slower than a few calls over large ones: 2,000 rows measured at
    ~13 docs/s chunked at 256 vs. ~86 docs/s in one call. At this default,
    the indexed corpus (tens of thousands of rows, see
    ``INDEX_SCOPE_WINDOW_DAYS``) fits in one or two calls.
    """
    if not texts:
        return np.empty((0, 0), dtype=np.float32)

    chunks = [
        encoder(texts[start : start + batch_size]) for start in range(0, len(texts), batch_size)
    ]
    return np.concatenate(chunks, axis=0).astype(np.float32)
