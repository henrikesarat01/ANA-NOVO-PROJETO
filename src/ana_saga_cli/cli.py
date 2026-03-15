from __future__ import annotations

from ana_saga_cli.config import AppConfig
from ana_saga_cli.evals.naturality import evaluate_response
from ana_saga_cli.sales.conversation_service import ConversationService


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
    if not hypotheses or not hypotheses.get("business_context"):
        return ["[debug] mapa_nicho: -"]

    lines = [
        f"[debug] mapa_nicho.contexto={hypotheses.get('business_context', '')}",
        f"[debug] mapa_nicho.nicho={hypotheses.get('niche', '-')}",
        f"[debug] mapa_nicho.segmento={hypotheses.get('segment', '-')}",
        f"[debug] mapa_nicho.oferta={hypotheses.get('offer_type', '-')}",
        f"[debug] mapa_nicho.operacao={hypotheses.get('operation_model', '-')}",
        _render_debug_list("mapa_nicho.hipoteses_prioritarias", hypotheses.get("priority_hypotheses", []), limit=4),
        _render_debug_list("mapa_nicho.lacunas", hypotheses.get("known_context_gaps", []), limit=4),
    ]
    for index, cluster in enumerate(hypotheses.get("diagnostic_clusters", [])[:3], start=1):
        lines.extend(
            [
                f"[debug] mapa_nicho.cluster_{index}.nome={cluster.get('cluster_name', '-')}",
                f"[debug] mapa_nicho.cluster_{index}.frente={cluster.get('operational_front', '-')}",
                f"[debug] mapa_nicho.cluster_{index}.problema={cluster.get('problem', '-')}",
                f"[debug] mapa_nicho.cluster_{index}.causa={cluster.get('cause', '-')}",
                f"[debug] mapa_nicho.cluster_{index}.raiz={cluster.get('root_cause', '-')}",
                _render_debug_list(f"mapa_nicho.cluster_{index}.efeitos", cluster.get("operational_effects", []), limit=3),
                _render_debug_list(f"mapa_nicho.cluster_{index}.sinais", cluster.get("observable_signs", []), limit=3),
                _render_debug_list(f"mapa_nicho.cluster_{index}.funcoes_saga", cluster.get("saga_functions", []), limit=4),
            ]
        )
    return lines


def main() -> None:
    config = AppConfig()
    service = ConversationService(config)

    print("=" * 72)
    print("ANA SAGA CLI")
    print(f"provider={config.provider} model={config.model}")
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

        print(f"\nANA> {result.response}")
        if config.stage_debug:
            print(f"\n[debug] etapa={result.stage_id} diagnosticos={result.diagnostics_count} hits={result.last_hits}")
            print(_render_scope_debug(service.state.lead_summary))
            for line in _render_hypothesis_debug(service.state.diagnostic_hypotheses):
                print(line)
            if report is not None:
                print(f"[debug] naturalidade score={report.score} aprovado={report.passed} findings={report.findings or ['ok']}")

if __name__ == "__main__":
    main()
