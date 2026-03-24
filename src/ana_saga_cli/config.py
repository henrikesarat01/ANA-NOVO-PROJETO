from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"


def _load_dotenv() -> None:
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()


@dataclass(slots=True)
class AppConfig:
    provider: str = os.getenv("ANA_PROVIDER", "mock").strip().lower()
    model: str = os.getenv("ANA_MODEL", "gpt-5.4").strip()
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    cerebras_api_key: str | None = os.getenv("CEREBRAS_API_KEY")
    verbose: bool = os.getenv("ANA_VERBOSE", "false").strip().lower() == "true"
    stage_debug: bool = os.getenv("ANA_STAGE_DEBUG", "false").strip().lower() == "true"
    stage_debug_scope: str = os.getenv("ANA_STAGE_DEBUG_SCOPE", "neural").strip().lower()
    naturality_debug: bool = os.getenv("ANA_NATURALITY_DEBUG", "false").strip().lower() == "true"
    repair_enabled: bool = os.getenv("ANA_ENABLE_REPAIR", "false").strip().lower() == "true"
    max_arsenal_hits: int = 6
    product_name: str = "SAGA"
    system_name: str = "ANA"
