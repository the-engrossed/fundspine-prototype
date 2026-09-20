"""Process configuration. Read once, from the environment, with no silent defaults
for anything whose wrong value would be expensive."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(REPO_ROOT / ".env")

DEFAULT_DATABASE_URL = "postgresql+psycopg://fundspine:fundspine@localhost:5433/fundspine"


@dataclass(frozen=True)
class Settings:
    database_url: str
    extract_model: str
    prose_model: str
    prompt_version: str
    schema_version: str
    out_dir: Path
    trace_dir: Path

    def require_openai_key(self) -> str:
        """Called at the point of use, not at import. Deterministic commands
        (golden generation, ingest, validation, eval scoring) run without a key."""
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Copy .env.example to .env and fill it in."
            )
        return key


@lru_cache(maxsize=1)
def settings() -> Settings:
    return Settings(
        database_url=os.environ.get("FUNDSPINE_DATABASE_URL", DEFAULT_DATABASE_URL),
        extract_model=os.environ.get("FUNDSPINE_EXTRACT_MODEL", "gpt-4o-2024-08-06"),
        prose_model=os.environ.get("FUNDSPINE_PROSE_MODEL", "gpt-4o-2024-08-06"),
        prompt_version=os.environ.get("FUNDSPINE_PROMPT_VERSION", "v1"),
        schema_version="1",
        out_dir=REPO_ROOT / "out",
        trace_dir=REPO_ROOT / "traces",
    )
