from __future__ import annotations

from pathlib import Path

from ana_saga_cli.knowledge.loader import (
    get_bpcf_framework_path,
    get_humanization_framework_path,
    get_product_arsenal_path,
    get_product_identity_path,
    get_product_inventory_path,
    get_sales_frameworks_path,
    load_arsenal_entries,
    load_bpcf_framework,
    load_humanization_framework,
    load_product_identity,
    load_product_inventory,
    load_sales_frameworks,
)


ROOT = Path(__file__).resolve().parents[1]


def test_knowledge_paths_point_to_refactored_structure() -> None:
    assert get_bpcf_framework_path() == ROOT / "src/ana_saga_cli/data/knowledge/frameworks/bpcf_bidirectional_problem_cause_framework.json"
    assert get_humanization_framework_path() == ROOT / "src/ana_saga_cli/data/knowledge/frameworks/humanizacao.md"
    assert get_sales_frameworks_path() == ROOT / "src/ana_saga_cli/data/frameworks.json"
    assert get_product_identity_path("saga") == ROOT / "src/ana_saga_cli/data/knowledge/products/saga/identidade_do_produto.json"
    assert get_product_arsenal_path("saga") == ROOT / "src/ana_saga_cli/data/knowledge/products/saga/arsenal_comercial.json"
    assert get_product_inventory_path("saga") == ROOT / "src/ana_saga_cli/data/knowledge/products/saga/inventario_de_funcionalidades.json"


def test_knowledge_loader_reads_identity_inventory_and_arsenal_from_refactored_tree() -> None:
    framework = load_bpcf_framework()
    sales_frameworks = load_sales_frameworks()
    humanization = load_humanization_framework()
    identity = load_product_identity("saga")
    inventory = load_product_inventory("saga")
    arsenal_entries = load_arsenal_entries("saga")

    assert framework["framework_id"] == "BPCF-BIDIRECTIONAL-PROBLEM-CAUSE-FRAMEWORK"
    assert sales_frameworks["processo_de_vendas"]
    assert any(item["framework_principal"] == "Up-Front Contract" for item in sales_frameworks["processo_de_vendas"])
    assert "Conversa primeiro; condução depois." in humanization

    assert identity["identidade_do_produto"]["nome"] == "SAGA"
    assert "WhatsApp" in identity["identidade_do_produto"]["categoria"]
    assert "transforma o WhatsApp da empresa" in identity["identidade_do_produto"]["o_que_e"]
    assert identity["promessa_central"]["frase_curta"]

    assert any(fact.section == "mensagens" and fact.name == "formulário" for fact in inventory)
    assert any(
        fact.section == "painel_de_controle"
        and fact.name == "funil de conversão"
        and "tela onde a empresa vê tudo que está acontecendo" in fact.description
        for fact in inventory
    )

    assert arsenal_entries
    assert any(entry.function_name == "Falar com Atendente" for entry in arsenal_entries)
    assert any(entry.function_name == "Pagamento Integrado" for entry in arsenal_entries)


def test_refactored_knowledge_adds_universal_integration_and_comparison_layers_without_brand_lock() -> None:
    identity_path = ROOT / "src/ana_saga_cli/data/knowledge/products/saga/identidade_do_produto.json"
    arsenal_path = ROOT / "src/ana_saga_cli/data/knowledge/products/saga/arsenal_comercial.json"
    inventory_path = ROOT / "src/ana_saga_cli/data/knowledge/products/saga/inventario_de_funcionalidades.json"

    identity_payload = identity_path.read_text(encoding="utf-8")
    arsenal_payload = arsenal_path.read_text(encoding="utf-8")
    inventory_payload = inventory_path.read_text(encoding="utf-8")
    identity = load_product_identity("saga")

    assert identity["arquitetura_do_produto"]["natureza_da_solucao"] == "produto_proprio"
    assert identity["arquitetura_do_produto"]["depende_de_motor_terceiro_para_existir"] is False
    assert "api" in identity["capacidade_de_integracao"]["formas_de_integracao"]
    assert "webhook" in identity["capacidade_de_integracao"]["formas_de_integracao"]
    assert "crm" in identity["capacidade_de_integracao"]["tipos_de_sistema_compativeis"]
    assert "erp" in identity["capacidade_de_integracao"]["tipos_de_sistema_compativeis"]

    assert "integracoes" in inventory_payload
    assert "categorias_de_comparacao" in arsenal_payload
    assert "ferramenta_generica" in arsenal_payload
    assert "produto_proprio_vs_ferramenta_generica" in arsenal_payload

    assert "n8n" not in identity_payload.lower()
    assert "n8n" not in arsenal_payload.lower()
    assert "n8n" not in inventory_payload.lower()
