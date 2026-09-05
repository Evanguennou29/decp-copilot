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


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
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


def load_settings() -> Settings:
    """Read settings from the environment, defaulting to the no-key mode."""
    return Settings(
        openai_api_key=os.environ.get("OPENAI_API_KEY") or None,
        ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        data_dir=os.environ.get("DECP_DATA_DIR", "data"),
        source_url=os.environ.get("DECP_SOURCE_URL", DEFAULT_PARQUET_URL),
    )
