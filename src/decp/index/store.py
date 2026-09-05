"""A small, persisted, brute-force vector index.

The indexed corpus is deliberately kept small (see README.md, "Indexed
corpus scope"), so an approximate-nearest-neighbour library like FAISS
would add a dependency without buying anything: a plain cosine similarity
over an in-memory matrix of a few thousand to a few tens of thousands of
384-dim vectors runs in a few milliseconds, comfortably inside the lot 2
"under one second" search budget. Vectors are expected to already be
L2-normalized (as ``decp.index.embed.load_encoder`` produces), so cosine
similarity is a plain dot product.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class VectorIndex:
    ids: list[str]
    vectors: np.ndarray  # shape (n, dim), L2-normalized rows
    metadata: dict[str, Any] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.ids)

    def search(
        self,
        query_vector: np.ndarray,
        *,
        top_k: int = 10,
        candidate_ids: set[str] | None = None,
    ) -> list[tuple[str, float]]:
        """Return up to ``top_k`` ``(id, cosine_similarity)`` pairs, best first.

        If ``candidate_ids`` is given, only those ids are considered — used
        to intersect the semantic search with structured filter results.
        """
        if len(self.ids) == 0:
            return []

        if candidate_ids is None:
            mask_indices = np.arange(len(self.ids))
        else:
            mask_indices = np.array(
                [i for i, doc_id in enumerate(self.ids) if doc_id in candidate_ids],
                dtype=np.int64,
            )
            if mask_indices.size == 0:
                return []

        scores = self.vectors[mask_indices] @ query_vector
        order = np.argsort(-scores)[:top_k]
        return [(self.ids[mask_indices[i]], float(scores[i])) for i in order]


def _meta_path(path: Path) -> Path:
    return path.with_suffix(".meta.json")


def save_index(
    path: Path,
    ids: list[str],
    vectors: np.ndarray,
    metadata: dict[str, Any] | None = None,
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, ids=np.array(ids, dtype=object), vectors=vectors.astype(np.float32))
    _meta_path(path).write_text(json.dumps(metadata or {}, indent=2), encoding="utf-8")


def load_index(path: Path) -> VectorIndex:
    path = Path(path)
    # allow_pickle is required because `ids` is an object-dtype string array.
    with np.load(path, allow_pickle=True) as data:
        ids = list(data["ids"])
        vectors = data["vectors"]
    meta_path = _meta_path(path)
    metadata = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    return VectorIndex(ids=ids, vectors=vectors, metadata=metadata)
