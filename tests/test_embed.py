import numpy as np

from decp.index.embed import embed_texts


def test_embed_texts_batches_calls_by_batch_size():
    call_sizes: list[int] = []

    def encoder(texts):
        call_sizes.append(len(texts))
        return np.ones((len(texts), 3), dtype=np.float32)

    texts = [f"text-{i}" for i in range(5)]
    result = embed_texts(texts, encoder, batch_size=2)

    assert call_sizes == [2, 2, 1]
    assert result.shape == (5, 3)


def test_embed_texts_single_batch_when_smaller_than_batch_size():
    def encoder(texts):
        return np.arange(len(texts) * 2, dtype=np.float32).reshape(len(texts), 2)

    result = embed_texts(["a", "b", "c"], encoder, batch_size=10)

    assert result.shape == (3, 2)


def test_embed_texts_empty_input_returns_empty_array():
    def encoder(texts):
        raise AssertionError("encoder should not be called for empty input")

    result = embed_texts([], encoder)

    assert result.shape == (0, 0)
