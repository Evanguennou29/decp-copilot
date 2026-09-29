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
import logging
import re
import urllib.request
from collections.abc import Callable, Sequence

from decp.answer.prompt import build_prompt
from decp.config import Settings
from decp.retrieval.search import SearchResult

Generator = Callable[[str], str]
logger = logging.getLogger(__name__)


class UncitedAnswerError(Exception):
    """Raised when a generated answer cannot be verified against retrieved markets."""


_CITATION_RE = re.compile(r"\[uid:\s*([^\]]+?)\s*\]", re.IGNORECASE)
_MONEY_RE = re.compile(
    r"(?<![\w])((?:\d{1,3}(?:[\s\u202f.,]\d{3})+|\d+)(?:[,.]\d{1,2})?)\s*(?:€|euros?\b)",
    re.IGNORECASE,
)


def _money_value(raw: str) -> float:
    value = raw.replace(" ", "").replace("\u202f", "")
    if "," in value and "." in value:
        value = value.replace(".", "").replace(",", ".")
    elif "," in value:
        value = (
            value.replace(",", ".")
            if len(value.split(",")[-1]) <= 2
            else value.replace(",", "")
        )
    elif "." in value and len(value.split(".")[-1]) == 3:
        value = value.replace(".", "")
    return float(value)


def validate_answer(answer: str, results: Sequence[SearchResult]) -> None:
    """Reject unknown citations and unsupported monetary claims.

    Each monetary sentence must cite a retrieved market with that exact amount.
    Aggregate figures are deliberately left to the deterministic stats panel.
    """
    known = {result.uid: result for result in results}
    citations = _CITATION_RE.findall(answer)
    if not citations or any(uid not in known for uid in citations):
        raise UncitedAnswerError("Answer has missing or unknown market citations")
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", answer):
        amounts = [_money_value(match) for match in _MONEY_RE.findall(sentence)]
        if not amounts:
            continue
        cited = [_money_value(str(known[uid].montant)) for uid in _CITATION_RE.findall(sentence)
                 if uid in known and known[uid].montant is not None]
        if any(not any(abs(amount - value) < 0.01 for value in cited) for amount in amounts):
            raise UncitedAnswerError("Answer contains an unsupported monetary amount")


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
    """Resolve cloud generation with a local Ollama fallback when available."""
    local = (
        _ollama_generator(settings.ollama_base_url, settings.ollama_model)
        if _ollama_available(settings.ollama_base_url)
        else None
    )
    if settings.has_llm_key:
        cloud = _openai_generator(
            settings.openai_base_url, settings.openai_api_key, settings.openai_model
        )
        if local is None:
            return cloud

        def generate(prompt: str) -> str:
            try:
                return cloud(prompt)
            except (OSError, ValueError, KeyError, IndexError, TypeError):
                logger.warning("Cloud generation failed; retrying with Ollama", exc_info=True)
                return local(prompt)

        return generate
    return local


def extract_cited_uids(text: str, valid_uids: Sequence[str]) -> list[str]:
    """Return only exact citation markers, in source order."""
    cited = set(_CITATION_RE.findall(text))
    return [uid for uid in valid_uids if uid in cited]


def generate_answer(question: str, results: Sequence[SearchResult], generator: Generator) -> str:
    """Generate a natural-language answer, requiring it to cite at least
    one of the given markets' ``uid``.

    Raises ``UncitedAnswerError`` when it doesn't — per SPEC.md section 7,
    callers must treat this as a rejection and fall back to the degraded
    mode rather than surface an answer with unverifiable figures.
    """
    prompt = build_prompt(question, results)
    answer = generator(prompt)
    validate_answer(answer, results)
    return answer
