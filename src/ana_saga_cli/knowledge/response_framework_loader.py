from __future__ import annotations

import functools
from pathlib import Path

from ana_saga_cli.config import DATA_DIR

_RESPONSE_FRAMEWORKS_DIR = DATA_DIR / "response_frameworks"


@functools.lru_cache(maxsize=32)
def _read_file_cached(path: str) -> str:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Response framework prompt not found: {file_path}")
    return file_path.read_text(encoding="utf-8")


def get_response_framework_prompt_path(framework_name: str) -> Path:
    file_path = _RESPONSE_FRAMEWORKS_DIR / f"{framework_name}.md"
    if not file_path.exists():
        raise KeyError(f"Response framework '{framework_name}' not found")
    return file_path


def load_response_framework_prompt(framework_name: str) -> str:
    return _read_file_cached(str(get_response_framework_prompt_path(framework_name)))