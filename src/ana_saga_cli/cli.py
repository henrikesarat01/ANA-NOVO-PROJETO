from __future__ import annotations

from pathlib import Path

from ana_saga_cli.config import AppConfig
from ana_saga_cli.debug_markdown import ConversationMarkdownLogger
from ana_saga_cli.evals.naturality import evaluate_response
from ana_saga_cli.sales.conversation_service import ConversationService


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _render_debug_list(label: str, items: list[str], limit: int = 4) -> str:
    if not items:
        return f"[debug] {label}: -"
    preview = " | ".join(items[:limit])
    return f"[debug] {label}: {preview}"


def _render_scope_debug(lead_summary: dict) -> str:
    if not lead_summary:
        return "[debug] lead_scope niche_specificity=unknown commercial_scope_ready=False"
    return (
        "[debug] lead_scope "
        f"niche_specificity={lead_summary.get('niche_specificity', 'unknown')} "
        f"commercial_scope_ready={bool(lead_summary.get('commercial_scope_ready', False))}"
    )


def _render_hypothesis_debug(hypotheses: dict) -> list[str]:
    contexto = hypotheses.get("contexto_simples", hypotheses.get("business_context", ""))
    if not hypotheses or not contexto:
        return ["[debug] mapa_nicho: -"]

    lines = [
        f"[debug] mapa_nicho.contexto={contexto}",
        f"[debug] mapa_nicho.leitura={hypotheses.get('leitura_do_cenario', '-')}",
        f"[debug] mapa_nicho.nicho={hypotheses.get('nicho', hypotheses.get('niche', '-'))}",
        f"[debug] mapa_nicho.segmento={hypotheses.get('segmento', hypotheses.get('segment', '-'))}",
        f"[debug] mapa_nicho.oferta={hypotheses.get('tipo_oferta', hypotheses.get('offer_type', '-'))}",
        f"[debug] mapa_nicho.operacao={hypotheses.get('modelo_operacao', hypotheses.get('operation_model', '-'))}",
        _render_debug_list("mapa_nicho.prioridades", hypotheses.get("prioridades_do_mapa", hypotheses.get("priority_hypotheses", [])), limit=4),
        _render_debug_list("mapa_nicho.lacunas", hypotheses.get("lacunas_em_aberto", hypotheses.get("known_context_gaps", [])), limit=4),
    ]
    pains = hypotheses.get("dores_reais", hypotheses.get("diagnostic_clusters", []))
    for index, pain in enumerate(pains[:3], start=1):
        lines.extend(
            [
                f"[debug] mapa_nicho.dor_{index}.nome={pain.get('nome', pain.get('cluster_name', '-'))}",
                f"[debug] mapa_nicho.dor_{index}.como_aparece={pain.get('como_aparece', pain.get('problem', '-'))}",
                f"[debug] mapa_nicho.dor_{index}.gera={pain.get('o_que_isso_gera', '-')}",
                f"[debug] mapa_nicho.dor_{index}.funcao_principal={pain.get('funcao_saga_que_ajuda', '-')}",
                f"[debug] mapa_nicho.dor_{index}.resolve={pain.get('como_o_saga_resolve', pain.get('resolution_logic', '-'))}",
                _render_debug_list(f"mapa_nicho.dor_{index}.funcoes_relacionadas", pain.get("funcoes_saga_relacionadas", pain.get("saga_functions", [])), limit=4),
            ]
        )
    return lines


def _debug_scope_is_full(config: AppConfig) -> bool:
    return config.stage_debug_scope == "full"


def _debug_scope_is_neural(config: AppConfig) -> bool:
    return config.stage_debug_scope == "neural"


def _debug_scope_is_deconstruction(config: AppConfig) -> bool:
    return config.stage_debug_scope == "deconstruction"


def _is_deconstruction_debug_line(line: str) -> bool:
    compact = " ".join(str(line or "").split())
    return "pipeline.deconstruction." in compact


def _is_neural_debug_line(line: str) -> bool:
    compact = " ".join(str(line or "").split())
    return any(
        token in compact
        for token in (
            "pipeline.neural.",
            "pipeline.deconstruction.",
            "pipeline.neurobehavior",
        )
    )


def _render_debug_trace(result_debug_trace: list[str], config: AppConfig) -> list[str]:
    if _debug_scope_is_neural(config):
        return []
    if _debug_scope_is_full(config):
        return [line for line in result_debug_trace if not _is_neural_debug_line(line)]
    return [line for line in result_debug_trace if _is_deconstruction_debug_line(line) and not _is_neural_debug_line(line)]


def _join_preview(items: list[str], empty: str = "-") -> str:
    cleaned = [_clean_text(item) for item in items if _clean_text(item)]
    return " | ".join(cleaned) if cleaned else empty


def _chunked_items(items: list[str], size: int = 3) -> list[str]:
    cleaned = [_clean_text(item) for item in items if _clean_text(item)]
    if not cleaned:
        return ["-"]
    return [" | ".join(cleaned[index:index + size]) for index in range(0, len(cleaned), size)]


def _render_neural_debug(result, config: AppConfig) -> list[str]:
    payload = getattr(result, "neural_debug", {}) or {}
    if not payload:
        return []

    stage = payload.get("stage", {}) if isinstance(payload.get("stage", {}), dict) else {}
    route = payload.get("route", {}) if isinstance(payload.get("route", {}), dict) else {}
    calls = payload.get("calls", []) if isinstance(payload.get("calls", []), list) else []
    state = payload.get("state", {}) if isinstance(payload.get("state", {}), dict) else {}
    negotiation = payload.get("negotiation", {}) if isinstance(payload.get("negotiation", {}), dict) else {}
    policy = payload.get("policy", {}) if isinstance(payload.get("policy", {}), dict) else {}
    strategy = payload.get("strategy", {}) if isinstance(payload.get("strategy", {}), dict) else {}
    neuro = payload.get("neurobehavior", {}) if isinstance(payload.get("neurobehavior", {}), dict) else {}

    lines: list[str] = []
    lines.append("[turn] ---- stage ----")
    lines.append(
        "[turn] "
        f"pipeline_stage={_clean_text(stage.get('stage_id', getattr(result, 'stage_id', '-')))} | "
        f"titulo={_clean_text(stage.get('stage_title', '-'))}"
    )
    if any(_clean_text(negotiation.get(key, "")) for key in ("decision_stage", "interaction_mode", "counterparty_intent", "trust_level")):
        lines.append("[turn] ---- negotiation ----")
        lines.append(
            "[turn] "
            f"decision_stage={_clean_text(negotiation.get('decision_stage', '-'))} | "
            f"mode={_clean_text(negotiation.get('interaction_mode', '-'))} | "
            f"intent={_clean_text(negotiation.get('counterparty_intent', '-'))}"
        )
        lines.append(
            "[turn] "
            f"trust={_clean_text(negotiation.get('trust_level', '-'))} | "
            f"resistance={_clean_text(negotiation.get('resistance_level', '-'))} | "
            f"priority={_clean_text(negotiation.get('question_priority', '-'))}"
        )
        if _clean_text(negotiation.get("microcommitment_goal", "")):
            lines.append(f"[turn] microcommitment={_clean_text(negotiation.get('microcommitment_goal', ''))}")
        if _clean_text(negotiation.get("conversation_tension", "")):
            lines.append(f"[turn] tension={_clean_text(negotiation.get('conversation_tension', ''))}")

    lines.append("[neural] ---- route ----")
    lines.append(
        "[neural] "
        f"simple_turn={str(bool(route.get('simple_turn', False))).lower()} | "
        f"base={_join_preview(route.get('base', []), empty='-')}"
    )

    contextual_items = []
    for item in route.get("contextual", []):
        if not isinstance(item, dict):
            continue
        name = _clean_text(item.get("name", ""))
        intensity = _clean_text(item.get("intensity", ""))
        contextual_items.append(f"{name}({intensity or '-'})" if name else "")
    if contextual_items:
        lines.append(f"[neural] contextual={_join_preview(contextual_items)}")
    for item in route.get("contextual", []):
        if not isinstance(item, dict):
            continue
        name = _clean_text(item.get("name", ""))
        reasons = item.get("reasons", []) if isinstance(item.get("reasons", []), list) else []
        if name and reasons:
            lines.append(f"[neural] reasons.{name}={_join_preview(reasons)}")

    lines.append("[neural] ---- calls ----")
    deconstruction_only = _debug_scope_is_deconstruction(config)
    for item in calls:
        if not isinstance(item, dict):
            continue
        name = _clean_text(item.get("name", ""))
        if not name:
            continue
        if deconstruction_only and name != "desconstrucao":
            continue
        scope = _clean_text(item.get("scope", "base"))
        intensity = _clean_text(item.get("intensity", ""))
        label = f"[neural] call {name} [{scope}]"
        if intensity:
            label = f"{label} intensity={intensity}"
        lines.append(label)
        lines.append(f"[neural]   return { _clean_text(item.get('summary', 'sem retorno')) }")

    if not calls:
        lines.append("[neural]   sem analyzers ativos neste turno")

    if not deconstruction_only:
        lines.append("[neural] ---- state ----")
        lines.append(f"[neural] active={_join_preview(state.get('active_neurals', []), empty='-')}")
        lines.append(
            "[neural] "
            f"emocao={_clean_text(state.get('emotional_state', '-'))} | "
            f"intencao={_clean_text(state.get('communicative_intent', '-'))} | "
            f"estilo={_clean_text(state.get('decision_style', '-'))}"
        )
        lines.append(
            "[neural] "
            f"simplificar={'sim' if bool(state.get('needs_simplification', False)) else 'nao'} | "
            f"conf={_clean_text(state.get('confidence', 0.0))}"
        )
        if _clean_text(state.get("pain_reading", "")):
            lines.append(f"[neural] pain_reading={_clean_text(state.get('pain_reading', ''))}")
        if _clean_text(state.get("clarity_note", "")):
            lines.append(f"[neural] clarity_note={_clean_text(state.get('clarity_note', ''))}")

        if policy:
            lines.append("[turn] ---- policy ----")
            lines.append(
                "[turn] "
                f"response_mode={_clean_text(policy.get('response_mode', '-'))} | "
                f"main_intention={_clean_text(policy.get('main_intention', '-'))} | "
                f"question_goal={_clean_text(policy.get('question_goal', '-'))}"
            )
            lines.append(
                "[turn] "
                f"question_type={_clean_text(policy.get('question_type', '-'))} | "
                f"question_budget={_clean_text(policy.get('question_budget', 0))}"
            )
            if _clean_text(policy.get("question_anchor", "")):
                lines.append(f"[turn] question_anchor={_clean_text(policy.get('question_anchor', ''))}")

        if strategy:
            lines.append("[turn] ---- strategy ----")
            lines.append(
                "[turn] "
                f"goal={_clean_text(strategy.get('message_goal', '-'))} | "
                f"intensity={_clean_text(strategy.get('approach_intensity', '-'))} | "
                f"format={_clean_text(strategy.get('response_format', '-'))}"
            )
            lines.append(
                "[turn] "
                f"axis={_clean_text(strategy.get('persuasion_axis', '-'))} | "
                f"conf={_clean_text(strategy.get('confidence', 0.0))}"
            )
            move_chunks = _chunked_items(strategy.get("tactical_moves", []), size=3)
            lines.append(f"[turn] moves={move_chunks[0]}")
            for chunk in move_chunks[1:]:
                lines.append(f"[turn]   {chunk}")
            avoid_chunks = _chunked_items(strategy.get("avoid", []), size=3)
            lines.append(f"[turn] avoid={avoid_chunks[0]}")
            for chunk in avoid_chunks[1:]:
                lines.append(f"[turn]   {chunk}")

    if _clean_text(state.get("deconstruction_intensity", "")):
        lines.append("[neural] ---- deconstruction state ----")
        lines.append(
            "[neural] "
            f"intensity={_clean_text(state.get('deconstruction_intensity', '-'))} | "
            f"summary={_clean_text(state.get('deconstruction_summary', '-'))}"
        )
        if _clean_text(state.get("blocked_variable", "")):
            lines.append(f"[neural] blocker={_clean_text(state.get('blocked_variable', ''))}")
        if _clean_text(state.get("literal_response_risk", "")):
            lines.append(f"[neural] literal_risk={_clean_text(state.get('literal_response_risk', ''))}")

    if not deconstruction_only and neuro:
        lines.append("[neuro] ---- authority ----")
        lines.append(f"[neuro] barrier={_clean_text(neuro.get('dominant_barrier', '-'))}")
        lines.append(f"[neuro] principles={_join_preview(neuro.get('active_principles', []), empty='-')}")
        lines.append(f"[neuro] conf={_clean_text(neuro.get('confidence', 0.0))}")
        lines.append(
            "[neuro] "
            f"load={_clean_text(neuro.get('cognitive_load', '-'))} | "
            f"risk={_clean_text(neuro.get('perceived_risk', '-'))} | "
            f"threat={_clean_text(neuro.get('threat_level', '-'))}"
        )
        lines.append(
            "[neuro] "
            f"predictability={_clean_text(neuro.get('predictability_gap', '-'))} | "
            f"concreteness={_clean_text(neuro.get('concreteness_gap', '-'))} | "
            f"choices={_clean_text(neuro.get('choice_overload', '-'))}"
        )
        lever_chunks = _chunked_items(neuro.get("recommended_levers", []), size=3)
        lines.append(f"[neuro] levers={lever_chunks[0]}")
        for chunk in lever_chunks[1:]:
            lines.append(f"[neuro]   {chunk}")
        suppress_chunks = _chunked_items(neuro.get("suppressed_moves", []), size=3)
        lines.append(f"[neuro] suppress={suppress_chunks[0]}")
        for chunk in suppress_chunks[1:]:
            lines.append(f"[neuro]   {chunk}")
    return lines


def main() -> None:
    config = AppConfig()
    service = ConversationService(config)
    markdown_logger = ConversationMarkdownLogger(Path.cwd(), config)

    print("=" * 72)
    print("ANA SAGA CLI")
    print(f"provider={config.provider} model={config.model}")
    print(f"debug_md={markdown_logger.file_path.name}")
    print("Digite 'sair' para encerrar.")
    print("=" * 72)

    while True:
        try:
            user_message = input("\ncliente> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrado.")
            break

        if not user_message:
            continue
        if user_message.lower() in {"sair", "exit", "quit"}:
            print("Encerrado.")
            break

        result = service.respond(user_message)
        report = evaluate_response(user_message, result.response) if config.naturality_debug else None
        markdown_logger.append_turn(result, naturality_report=report)

        if config.stage_debug:
            for line in _render_neural_debug(result, config):
                print(line)
            for line in _render_debug_trace(result.debug_trace, config):
                print(line)
            if _debug_scope_is_full(config):
                print(f"\n[debug] etapa={result.stage_id} diagnosticos={result.diagnostics_count} hits={result.last_hits}")
                print(_render_scope_debug(service.state.lead_summary))
                for line in _render_hypothesis_debug(service.state.diagnostic_hypotheses):
                    print(line)
        print(f"\nANA> {result.response}")
        if config.stage_debug:
            if report is not None and _debug_scope_is_full(config):
                print(f"[debug] naturalidade score={report.score} aprovado={report.passed} findings={report.findings or ['ok']}")

if __name__ == "__main__":
    main()
