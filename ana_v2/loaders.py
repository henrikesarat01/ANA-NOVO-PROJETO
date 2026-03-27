from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ROOT_DIR = Path(__file__).resolve().parent


@dataclass(slots=True)
class ProductData:
    slug: str
    path: Path
    payload: dict[str, Any]


@dataclass(slots=True)
class PromptData:
    prompt_id: str
    path: Path
    paths: tuple[Path, ...]
    title: str
    body: str


def load_product(slug: str) -> ProductData:
    path = ROOT_DIR / "products" / slug / "product.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Produto não encontrado: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"YAML inválido para produto: {path}")
    return ProductData(slug=slug, path=path, payload=payload)


def load_prompt(relative_path: str, prompt_id: str | None = None) -> PromptData:
    path = ROOT_DIR / relative_path
    if not path.exists():
        raise FileNotFoundError(f"Prompt não encontrado: {path}")
    body = path.read_text(encoding="utf-8").strip()
    title = ""
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            break
    effective_id = prompt_id or path.stem
    return PromptData(
        prompt_id=effective_id,
        path=path,
        paths=(path,),
        title=title or effective_id,
        body=body,
    )


def load_prompt_composto(relative_paths: list[str], prompt_id: str) -> PromptData:
    prompts = [load_prompt(relative_path, prompt_id=f"{prompt_id}:{index}") for index, relative_path in enumerate(relative_paths, start=1)]
    if not prompts:
        raise ValueError(f"Nenhum prompt informado para {prompt_id}")
    body = "\n\n".join(prompt.body for prompt in prompts).strip()
    return PromptData(
        prompt_id=prompt_id,
        path=prompts[0].path,
        paths=tuple(prompt.path for prompt in prompts),
        title=prompts[0].title,
        body=body,
    )
