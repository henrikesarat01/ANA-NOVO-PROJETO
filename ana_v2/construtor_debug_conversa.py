from __future__ import annotations

from typing import Any

from ana_v2.loaders import ProductData, PromptData


def _extrair_validacao_next_variable_id(payload: dict[str, Any]) -> str:
    proxima_validacao = payload.get("proxima_validacao", {}) or {}
    return str(proxima_validacao.get("id", ""))


def _extrair_validacao_movement(payload: dict[str, Any]) -> str:
    movimento_do_momento = payload.get("movimento_do_momento", {}) or {}
    if movimento_do_momento.get("natureza"):
        return str(movimento_do_momento.get("natureza", ""))
    return ""


def construir_debug_markdown(
    *,
    produto: ProductData,
    prompt_etapa_final: PromptData,
    entry_stage: str,
    final_stage: str,
    user_message: str,
    response: str,
    stage_selection: dict[str, Any],
    instructions: str,
    prompt_input: str,
    prompt_meta: dict[str, Any],
    debug_trace: list[str],
    llm_calls: list[dict[str, Any]],
    state_before: dict[str, Any],
    state_after: dict[str, Any],
    contexto_comercial_informado: str,
    descoberta_nicho: dict[str, Any],
    descoberta_nicho_meta: dict[str, Any],
    desconstrucao_primeiros_principios: dict[str, Any],
    desconstrucao_primeiros_principios_meta: dict[str, Any],
    validacao_preco_contexto: dict[str, Any],
    validacao_preco_contexto_meta: dict[str, Any],
    contexto_uso_explicacao_produto: dict[str, Any],
    contexto_uso_explicacao_produto_meta: dict[str, Any],
    storytelling_explicacao_produto: dict[str, Any],
    storytelling_explicacao_produto_meta: dict[str, Any],
) -> dict[str, Any]:
    funcoes_ranqueadas = descoberta_nicho.get("funcoes_ranqueadas", [])
    proxima_variavel_id = _extrair_validacao_next_variable_id(validacao_preco_contexto)
    movement = _extrair_validacao_movement(validacao_preco_contexto)
    lead_summary = {
        "known_context_count": 1 if contexto_comercial_informado else 0,
        "commercial_scope_ready": bool(contexto_comercial_informado),
        "next_question_focus": (
            proxima_variavel_id
            if final_stage == "preco_contexto"
            else "-"
        ),
        "niche_specificity": "",
        "business_context_line": contexto_comercial_informado,
        "product_or_service": contexto_comercial_informado,
        "ranked_functions_count": len(funcoes_ranqueadas) if isinstance(funcoes_ranqueadas, list) else 0,
    }
    return {
        "turn": {
            "turn_count": state_after.get("turn_count", 0),
            "entry_stage": entry_stage,
            "final_stage": final_stage,
            "final_stage_title": prompt_etapa_final.title,
        },
        "messages": {
            "user": user_message,
            "assistant": response,
        },
        "lead_summary": lead_summary,
        "offer_sales_architecture": {
            "mode": "ana_v2_minimo",
            "product_slug": produto.slug,
            "product_name": produto.payload.get("nome", ""),
        },
        "neural": {},
        "counterparty_model": {},
        "policy": {
            "initial": {
                "response_mode": "minimal_flow",
                "main_intention": "manter conversa viva",
                "question_goal": "none",
            },
            "final": {
                "response_mode": "minimal_flow",
                "main_intention": final_stage,
                "question_goal": (
                    (proxima_variavel_id or "none")
                    if final_stage == "preco_contexto"
                    else "none"
                ),
            },
        },
        "response_strategy": {
            "message_goal": final_stage,
            "response_format": "free_text",
            "persuasion_axis": "clareza_humana",
            "tactical_moves": [
                "responder_movimento_real_do_cliente",
                "manter_fluxo_minimo",
                "segurar_preco_quando_necessario",
            ],
        },
        "stage_router": {
            "source": "ana_v2_decisor_etapas",
            "reason": stage_selection.get("reason", ""),
            "selected_stage": final_stage,
            "confidence": stage_selection.get("confidence", 0.0),
        },
        "diagnostic_hypotheses": {},
        "retrieval": {
            "descoberta_nicho_executada": descoberta_nicho_meta.get("executed", False),
            "descoberta_nicho_prompt_path": descoberta_nicho_meta.get("prompt_path", ""),
            "descoberta_nicho_input_chars": descoberta_nicho_meta.get("input_chars", 0),
            "descoberta_nicho_result": descoberta_nicho,
            "desconstrucao_primeiros_principios_executada": desconstrucao_primeiros_principios_meta.get("executed", False),
            "desconstrucao_primeiros_principios_prompt_path": desconstrucao_primeiros_principios_meta.get("prompt_path", ""),
            "desconstrucao_primeiros_principios_input_chars": desconstrucao_primeiros_principios_meta.get("input_chars", 0),
            "desconstrucao_primeiros_principios_variavel_critica": desconstrucao_primeiros_principios_meta.get("variavel_critica_id", ""),
            "desconstrucao_primeiros_principios_result": desconstrucao_primeiros_principios,
            "validacao_preco_contexto_executada": validacao_preco_contexto_meta.get("executed", False),
            "validacao_preco_contexto_prompt_path": validacao_preco_contexto_meta.get("prompt_path", ""),
            "validacao_preco_contexto_input_chars": validacao_preco_contexto_meta.get("input_chars", 0),
            "validacao_preco_contexto_campos_considerados": validacao_preco_contexto_meta.get("campos_considerados", []),
            "validacao_preco_contexto_evidencias_utilizadas_count": validacao_preco_contexto_meta.get("evidencias_utilizadas_count", 0),
            "validacao_preco_contexto_result": validacao_preco_contexto,
            "contexto_uso_explicacao_produto_executado": contexto_uso_explicacao_produto_meta.get("executed", False),
            "contexto_uso_explicacao_produto_prompt_path": contexto_uso_explicacao_produto_meta.get("prompt_path", ""),
            "contexto_uso_explicacao_produto_input_chars": contexto_uso_explicacao_produto_meta.get("input_chars", 0),
            "contexto_uso_explicacao_produto_result": contexto_uso_explicacao_produto,
            "storytelling_explicacao_produto_executado": storytelling_explicacao_produto_meta.get("executed", False),
            "storytelling_explicacao_produto_prompt_path": storytelling_explicacao_produto_meta.get("prompt_path", ""),
            "storytelling_explicacao_produto_input_chars": storytelling_explicacao_produto_meta.get("input_chars", 0),
            "storytelling_explicacao_produto_result": storytelling_explicacao_produto,
        },
        "pricing": {
            "price_visible_to_llm": prompt_meta["includes_price_data"],
            "price_stage_blocked": final_stage == "preco_contexto",
        },
        "bpcf": {},
        "surface_guidance": {
            "response_opening": "llm_defined",
            "brevity_mode": "natural",
            "question_anchor": "",
            "active_stage": final_stage,
        },
        "offer_context": (
            {
                "product_name": produto.payload.get("nome", ""),
                "product_category": produto.payload.get("categoria", ""),
                "descricao_curta": produto.payload.get("descricao_curta", ""),
                "descricao_longa": produto.payload.get("descricao_longa", ""),
                "funcoes_count": len(produto.payload.get("funcoes", [])),
            }
            if final_stage == "explicacao_produto"
            else {}
        ),
        "channel_context": {
            "channel": "whatsapp",
            "runner": "ana_v2_minimo",
        },
        "forensic": {
            "state_before": state_before,
            "state_after": state_after,
            "loaded_files": {
                "stage_prompt_path": prompt_meta["stage_prompt_path"],
                "stage_prompt_paths": prompt_meta.get("stage_prompt_paths", [prompt_meta["stage_prompt_path"]]),
                "decisor_etapas_prompt_path": prompt_meta["decisor_etapas_prompt_path"],
                "product_path": prompt_meta["product_path"],
                "descoberta_nicho_prompt_path": prompt_meta.get("descoberta_nicho_prompt_path", ""),
                "desconstrucao_primeiros_principios_prompt_path": prompt_meta.get("desconstrucao_primeiros_principios_prompt_path", ""),
                "validacao_preco_contexto_prompt_path": prompt_meta.get("validacao_preco_contexto_prompt_path", ""),
                "contexto_uso_prompt_path": prompt_meta.get("contexto_uso_prompt_path", ""),
                "storytelling_prompt_path": prompt_meta.get("storytelling_prompt_path", ""),
            },
            "generated_artifacts": {
                "stage_selection": stage_selection,
                "product_included": prompt_meta["product_included"],
                "includes_price_data": prompt_meta["includes_price_data"],
                "descoberta_nicho_executada": descoberta_nicho_meta.get("executed", False),
                "descoberta_nicho_ranked_functions_count": descoberta_nicho_meta.get("ranked_functions_count", 0),
                "desconstrucao_primeiros_principios_executada": desconstrucao_primeiros_principios_meta.get("executed", False),
                "desconstrucao_primeiros_principios_variavel_critica_id": desconstrucao_primeiros_principios_meta.get("variavel_critica_id", ""),
                "validacao_preco_contexto_executada": validacao_preco_contexto_meta.get("executed", False),
                "validacao_preco_contexto_next_variable_id": validacao_preco_contexto_meta.get("next_variable_id", ""),
                "validacao_preco_contexto_movement": movement,
                "validacao_preco_contexto_campos_considerados": validacao_preco_contexto_meta.get("campos_considerados", []),
                "validacao_preco_contexto_evidencias_utilizadas_count": validacao_preco_contexto_meta.get("evidencias_utilizadas_count", 0),
                "contexto_uso_explicacao_produto_executado": contexto_uso_explicacao_produto_meta.get("executed", False),
                "contexto_uso_explicacao_produto_texto": contexto_uso_explicacao_produto_meta.get("texto", ""),
                "storytelling_explicacao_produto_executado": storytelling_explicacao_produto_meta.get("executed", False),
                "storytelling_explicacao_produto_texto": storytelling_explicacao_produto_meta.get("texto", ""),
            },
        },
        "llm_calls": llm_calls,
        "prompt": {
            "stage_prompt_path": prompt_meta["stage_prompt_path"],
            "stage_prompt_paths": prompt_meta.get("stage_prompt_paths", [prompt_meta["stage_prompt_path"]]),
            "decisor_etapas_prompt_path": prompt_meta["decisor_etapas_prompt_path"],
            "product_path": prompt_meta["product_path"],
            "desconstrucao_primeiros_principios_prompt_path": prompt_meta.get("desconstrucao_primeiros_principios_prompt_path", ""),
            "contexto_uso_prompt_path": prompt_meta.get("contexto_uso_prompt_path", ""),
            "storytelling_prompt_path": prompt_meta.get("storytelling_prompt_path", ""),
            "instruction_chars": len(instructions),
            "input_chars": prompt_meta["input_chars"],
            "history_items": prompt_meta["history_items"],
            "product_included": prompt_meta["product_included"],
            "includes_price_data": prompt_meta["includes_price_data"],
            "instructions": instructions,
            "user_input": prompt_input,
        },
        "pipeline_trace": debug_trace,
    }
