"""Application configuration derived from environment variables.

The app must remain useful without any API key (see SPEC.md section 1):
``Settings.has_llm_key`` is False by default, which is what routes the
answer step to the degraded, citation-only mode instead of failing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from decp.ingest.download import DEFAULT_PARQUET_URL

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_OLLAMA_MODEL = "llama3.2"


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None = None
    openai_base_url: str = DEFAULT_OPENAI_BASE_URL
    openai_model: str = DEFAULT_OPENAI_MODEL
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = DEFAULT_OLLAMA_MODEL
    data_dir: str = "data"
    source_url: str = DEFAULT_PARQUET_URL

    @property
    def has_llm_key(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def raw_parquet_path(self) -> Path:
        return Path(self.data_dir) / "raw" / "decp.parquet"

    @property
    def database_path(self) -> Path:
        return Path(self.data_dir) / "decp.duckdb"

    @property
    def vector_index_path(self) -> Path:
        return Path(self.data_dir) / "index" / "decp.index.npz"


def load_settings() -> Settings:
    """Read settings from the environment, defaulting to the no-key mode.

    ``openai_base_url``/``openai_model`` default to OpenAI itself but can
    point at any OpenAI-compatible chat completions endpoint (e.g. a free
    tier such as Groq's), so "un fournisseur au choix" (SPEC.md section 1)
    is a choice of environment variables, not of code.

    Reads only the real process environment — it does not itself load a
    ``.env`` file, so it stays a deterministic function of os.environ for
    tests regardless of what a developer's local ``.env`` contains. The
    ``decp`` CLI (``decp.cli.main``) loads ``.env`` once at startup before
    anything calls this.
    """
    return Settings(
        openai_api_key=os.environ.get("OPENAI_API_KEY") or None,
        openai_base_url=os.environ.get("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL),
        openai_model=os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
        ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL),
        data_dir=os.environ.get("DECP_DATA_DIR", "data"),
        source_url=os.environ.get("DECP_SOURCE_URL", DEFAULT_PARQUET_URL),
    )
