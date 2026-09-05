"""LLM-based answer generation, always validated for citations.

Budget (SPEC.md section 1): a free-tier cloud provider first, a local
Ollama model as fallback, and — if neither is reachable — no generation at
all (``load_generator`` returns ``None``, routing callers to
``decp.answer.degraded`` instead). ``openai_base_url``/``openai_model`` in
``Settings`` default to OpenAI but accept any OpenAI-compatible chat
completions endpoint, so "un fournisseur au choix" is a `.env` choice
(e.g. Groq's free tier), not a code change.

``load_generator`` is the only function here that touches the network (a
cloud API call, or a localhost probe for Ollama); ``generate_answer`` is
the pure orchestration/validation logic, exercised in tests with a fake
``Generator`` — never the real network path.
"""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable, Sequence

from decp.answer.prompt import build_prompt
from decp.config import Settings
from decp.retrieval.search import SearchResult

Generator = Callable[[str], str]


class UncitedAnswerError(Exception):
    """Raised when a generated answer cites no known market identifier."""


def _openai_generator(base_url: str, api_key: str, model: str) -> Generator:
    def generate(prompt: str) -> str:
        payload = json.dumps(
            {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{base_url.rstrip('/')}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            body = json.loads(response.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"]

    return generate


def _ollama_available(base_url: str, *, timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(f"{base_url.rstrip('/')}/api/tags", timeout=timeout):  # noqa: S310
            return True
    except OSError:
        return False


def _ollama_generator(base_url: str, model: str) -> Generator:
    def generate(prompt: str) -> str:
        payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
        request = urllib.request.Request(
            f"{base_url.rstrip('/')}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
            body = json.loads(response.read().decode("utf-8"))
        return body["response"]

    return generate


def load_generator(settings: Settings) -> Generator | None:
    """Resolve a real generator: cloud key, then a reachable local Ollama,
    else ``None`` (degraded mode). Never called in tests."""
    if settings.has_llm_key:
        return _openai_generator(
            settings.openai_base_url, settings.openai_api_key, settings.openai_model
        )
    if _ollama_available(settings.ollama_base_url):
        return _ollama_generator(settings.ollama_base_url, settings.ollama_model)
    return None


def extract_cited_uids(text: str, valid_uids: Sequence[str]) -> list[str]:
    """Which of ``valid_uids`` are literally present in ``text``, in ``valid_uids`` order."""
    return [uid for uid in valid_uids if uid in text]


def generate_answer(question: str, results: Sequence[SearchResult], generator: Generator) -> str:
    """Generate a natural-language answer, requiring it to cite at least
    one of the given markets' ``uid``.

    Raises ``UncitedAnswerError`` when it doesn't — per SPEC.md section 7,
    callers must treat this as a rejection and fall back to the degraded
    mode rather than surface an answer with unverifiable figures.
    """
    prompt = build_prompt(question, results)
    answer = generator(prompt)
    valid_uids = [r.uid for r in results]
    if not extract_cited_uids(answer, valid_uids):
        raise UncitedAnswerError("Generated answer cites no known market identifier")
    return answer
