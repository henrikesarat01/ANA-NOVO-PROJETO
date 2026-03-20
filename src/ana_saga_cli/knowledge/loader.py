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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ValueError(f"YAML invalido em {path}: esperado objeto no topo.")
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
    return load_json(DATA_DIR / "knowledge" / "BPCF-BIDIRECTIONAL-PROBLEM-CAUSE-FRAMEWORK.json")


def load_arsenal_entries() -> list[ArsenalEntry]:
    payload = load_json(DATA_DIR / "knowledge" / "BPCF-ARSENAL-SAGA.json")
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


def load_product_inventory() -> list[ProductFact]:
    path = DATA_DIR / "knowledge" / "saga_funcionalidades_inventario.md"
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
