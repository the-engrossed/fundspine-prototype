from __future__ import annotations

from pathlib import Path


def load_prompt(version: str, name: str) -> str:
    path = Path(__file__).resolve().parent / "prompts" / version / f"{name}.md"
    if not path.is_file():
        raise FileNotFoundError(f"prompt not found: {path}")
    return path.read_text(encoding="utf-8")
