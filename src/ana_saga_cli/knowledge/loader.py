from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ana_saga_cli.config import DATA_DIR
from ana_saga_cli.domain.models import ArsenalEntry, ProductFact, StageDefinition


_STAGE_DEFINITION_KEYS = {
    "stage_id",
    "title",
    "goal",
    "global_tone",
    "dos",
    "donts",
    "response_contract",
}

_KNOWLEDGE_ROOT = DATA_DIR / "knowledge"
_FRAMEWORKS_DIR = _KNOWLEDGE_ROOT / "frameworks"
_PRODUCTS_DIR = _KNOWLEDGE_ROOT / "products"
_DEFAULT_PRODUCT_SLUG = "saga"

_LEGACY_FRAMEWORK_PATH = _KNOWLEDGE_ROOT / "BPCF-BIDIRECTIONAL-PROBLEM-CAUSE-FRAMEWORK.json"
_LEGACY_ARSENAL_PATHS = {
    "saga": _KNOWLEDGE_ROOT / "BPCF-ARSENAL-SAGA.json",
}
_LEGACY_INVENTORY_PATHS = {
    "saga": _KNOWLEDGE_ROOT / "saga_funcionalidades_inventario.md",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ValueError(f"YAML invalido em {path}: esperado objeto no topo.")
    return payload


def _resolve_existing_path(primary: Path, fallback: Path | None = None) -> Path:
    if primary.exists():
        return primary
    if fallback and fallback.exists():
        return fallback
    if fallback:
        raise FileNotFoundError(f"arquivo de knowledge ausente: {primary} (fallback legado: {fallback})")
    raise FileNotFoundError(f"arquivo de knowledge ausente: {primary}")


def _product_dir(product_slug: str = _DEFAULT_PRODUCT_SLUG) -> Path:
    return _PRODUCTS_DIR / product_slug.strip().lower()


def get_bpcf_framework_path() -> Path:
    primary = _FRAMEWORKS_DIR / "bpcf_bidirectional_problem_cause_framework.json"
    return _resolve_existing_path(primary, _LEGACY_FRAMEWORK_PATH)


def get_humanization_framework_path() -> Path:
    primary = _FRAMEWORKS_DIR / "humanizacao.md"
    return _resolve_existing_path(primary)


def get_product_identity_path(product_slug: str = _DEFAULT_PRODUCT_SLUG) -> Path:
    primary = _product_dir(product_slug) / "identidade_do_produto.json"
    return _resolve_existing_path(primary)


def get_product_arsenal_path(product_slug: str = _DEFAULT_PRODUCT_SLUG) -> Path:
    slug = product_slug.strip().lower()
    primary = _product_dir(slug) / "arsenal_comercial.json"
    return _resolve_existing_path(primary, _LEGACY_ARSENAL_PATHS.get(slug))


def get_product_inventory_path(product_slug: str = _DEFAULT_PRODUCT_SLUG) -> Path:
    slug = product_slug.strip().lower()
    primary = _product_dir(slug) / "inventario_de_funcionalidades.json"
    return _resolve_existing_path(primary, _LEGACY_INVENTORY_PATHS.get(slug))


@lru_cache(maxsize=16)
def load_product_identity(product_slug: str = _DEFAULT_PRODUCT_SLUG) -> dict[str, Any]:
    payload = load_json(get_product_identity_path(product_slug))
    if not isinstance(payload, dict):
        raise ValueError("identidade do produto invalida: esperado objeto JSON no topo")
    return payload


def load_stage_definitions() -> dict[str, StageDefinition]:
    root = DATA_DIR / "processo_de_vendas"
    definitions: dict[str, StageDefinition] = {}
    for stage_dir in sorted(root.iterdir()):
        if not stage_dir.is_dir():
            continue
        payload = load_json(stage_dir / "personalidade.json")
        filtered_payload = {key: value for key, value in payload.items() if key in _STAGE_DEFINITION_KEYS}
        definitions[payload["stage_id"]] = StageDefinition(**filtered_payload)
    return definitions


def load_bpcf_framework() -> dict[str, Any]:
    payload = load_json(get_bpcf_framework_path())
    if not isinstance(payload, dict):
        raise ValueError("framework BPCF invalido: esperado objeto JSON no topo")
    return payload


@lru_cache(maxsize=1)
def load_humanization_framework() -> str:
    return get_humanization_framework_path().read_text(encoding="utf-8").strip()


def load_arsenal_entries(product_slug: str = _DEFAULT_PRODUCT_SLUG) -> list[ArsenalEntry]:
    payload = load_json(get_product_arsenal_path(product_slug))
    if not isinstance(payload, dict):
        raise ValueError("arsenal comercial invalido: esperado objeto JSON no topo")
    items: list[ArsenalEntry] = []
    categories = payload.get("categorias", {})
    for category_name, blocks in categories.items():
        for block in blocks:
            for problem_entry in block.get("problemas", []):
                items.append(
                    ArsenalEntry(
                        category=category_name,
                        function_name=block["funcao"],
                        saga_features=block.get("funcoes_saga", []),
                        problem=problem_entry["problema"],
                        cause=problem_entry["causa"],
                        root=problem_entry["raiz"],
                        characteristic=block["caracteristica"],
                        product=block["produto"],
                    )
                )
    return items


def _load_inventory_from_markdown(path: Path) -> list[ProductFact]:
    section = "geral"
    facts: list[ProductFact] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("## "):
            section = line.replace("##", "", 1).strip()
            continue
        if line.startswith("- **") and "** -" in line:
            title_part, desc = line[2:].split("** -", 1)
            name = title_part.replace("**", "").strip()
            facts.append(ProductFact(section=section, name=name, description=desc.strip()))
    return facts


def _load_inventory_from_json(path: Path) -> list[ProductFact]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("inventario de funcionalidades invalido: esperado objeto JSON no topo")
    categories = payload.get("categorias", {})
    facts: list[ProductFact] = []
    for section, block in categories.items():
        if not isinstance(block, dict):
            continue
        section_hint = " ".join(
            part.strip()
            for part in [
                str(block.get("titulo", "") or "").strip(),
                str(block.get("descricao", "") or "").strip(),
            ]
            if part and part.strip()
        )
        for item in block.get("itens", []):
            if not isinstance(item, dict):
                continue
            name = str(item.get("nome", "") or "").strip()
            description = str(item.get("explicacao", "") or "").strip()
            if not name or not description:
                continue
            full_description = " ".join(part for part in [section_hint, description] if part)
            facts.append(ProductFact(section=section, name=name, description=full_description))
    return facts


def load_product_inventory(product_slug: str = _DEFAULT_PRODUCT_SLUG) -> list[ProductFact]:
    path = get_product_inventory_path(product_slug)
    if path.suffix.lower() == ".md":
        return _load_inventory_from_markdown(path)
    return _load_inventory_from_json(path)
