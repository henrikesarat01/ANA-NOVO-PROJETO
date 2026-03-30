from __future__ import annotations

from pathlib import Path

from ana_saga_cli.config import AppConfig
from ana_saga_cli.debug_markdown import ConversationMarkdownLogger

from ana_v2.restaurador_sessao_debug import restaurar_ultima_sessao_debug
from ana_v2.service import AnaV2ConversationService


def _extrair_desconstrucao_variavel_critica_id(payload: dict) -> str:
    leitura_estrutural = payload.get("leitura_estrutural", {}) or {}
    eixo_de_valor = leitura_estrutural.get("eixo_de_valor", {}) or {}
    variavel_critica = eixo_de_valor.get("variavel_critica", {}) or {}
    return str(variavel_critica.get("id", ""))


def _extrair_validacao_next_variable_id(payload: dict) -> str:
    proxima_validacao = payload.get("proxima_validacao", {}) or {}
    return str(proxima_validacao.get("id", ""))


def main() -> None:
    config = AppConfig()
    service = AnaV2ConversationService(config)
    sessao_restaurada = restaurar_ultima_sessao_debug(Path.cwd())
    if sessao_restaurada is not None:
        service.restaurar_sessao(
            current_stage=sessao_restaurada.current_stage,
            turn_count=sessao_restaurada.turn_count,
            history=sessao_restaurada.history,
            memoria_estavel=sessao_restaurada.memoria_estavel,
            memoria_de_progressao=sessao_restaurada.memoria_de_progressao,
            preco_ja_foi_dito_na_conversa=sessao_restaurada.preco_ja_foi_dito_na_conversa,
            ultima_referencia_de_preco=sessao_restaurada.ultima_referencia_de_preco,
            contexto_comercial_informado=sessao_restaurada.contexto_comercial_informado,
            descoberta_nicho=sessao_restaurada.descoberta_nicho,
            desconstrucao_primeiros_principios=sessao_restaurada.desconstrucao_primeiros_principios,
            validacao_preco_contexto=sessao_restaurada.validacao_preco_contexto,
        )
        markdown_logger = ConversationMarkdownLogger(
            Path.cwd(),
            config,
            file_path=sessao_restaurada.file_path,
            reuse_existing=True,
        )
        markdown_logger.append_system_event(
            "Resume Session",
            [
                "- action: restore_from_latest_debug",
                f"- removed_turn_number: {sessao_restaurada.removed_turn_number or 0}",
                f"- restored_stage: {sessao_restaurada.current_stage}",
                f"- restored_turn_count: {sessao_restaurada.turn_count}",
                f"- removed_client_message: {sessao_restaurada.removed_client_message}",
            ],
            payload={
                "action": "restore_from_latest_debug",
                "debug_file_path": str(sessao_restaurada.file_path),
                "removed_turn_number": sessao_restaurada.removed_turn_number,
                "removed_client_message": sessao_restaurada.removed_client_message,
                "restored_stage": sessao_restaurada.current_stage,
                "restored_turn_count": sessao_restaurada.turn_count,
                "restored_history_messages": len(sessao_restaurada.history),
                "restored_memoria_estavel": sessao_restaurada.memoria_estavel,
                "restored_memoria_de_progressao": sessao_restaurada.memoria_de_progressao,
                "restored_preco_ja_foi_dito_na_conversa": sessao_restaurada.preco_ja_foi_dito_na_conversa,
                "restored_ultima_referencia_de_preco": sessao_restaurada.ultima_referencia_de_preco,
                "restored_business_context_line": sessao_restaurada.contexto_comercial_informado,
                "restored_ranked_functions_count": len(sessao_restaurada.descoberta_nicho.get("funcoes_ranqueadas", [])),
                "restored_desconstrucao_variavel_critica": _extrair_desconstrucao_variavel_critica_id(
                    sessao_restaurada.desconstrucao_primeiros_principios
                ),
                "restored_next_variable_id": _extrair_validacao_next_variable_id(
                    sessao_restaurada.validacao_preco_contexto
                ),
            },
        )
    else:
        markdown_logger = ConversationMarkdownLogger(Path.cwd(), config)
        service.limpar_memoria_em_arquivos()

    print("=" * 72)
    print("ANA V2 CLI")
    print(f"provider={config.provider} model={config.model}")
    print(f"debug_md={markdown_logger.file_path.name}")
    if sessao_restaurada is not None:
        print(
            "sessao_restaurada=true "
            f"turno_removido={sessao_restaurada.removed_turn_number or 0} "
            f"turnos_ativos={sessao_restaurada.turn_count}"
        )
    print("Comandos: /voltar desfaz o último turno.")
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
        if user_message == "/voltar":
            if not service.pode_voltar_ultimo_turno():
                print("\nANA> não tem turno anterior para voltar.")
                continue
            undo_info = service.voltar_ultimo_turno()
            markdown_logger.append_system_event(
                "Undo Last Turn",
                [
                    f"- action: {undo_info['action']}",
                    f"- restored_stage: {undo_info['restored_stage']}",
                    f"- restored_turn_count: {undo_info['restored_turn_count']}",
                    f"- history_messages: {undo_info['history_messages']}",
                ],
                payload=undo_info,
            )
            print(
                "\nANA> último turno desfeito. "
                f"voltou para etapa={undo_info['restored_stage']} "
                f"no turno={undo_info['restored_turn_count']}."
            )
            continue
        if user_message.lower() in {"sair", "exit", "quit"}:
            print("Encerrado.")
            break

        result = service.respond(user_message)
        markdown_logger.append_turn(result)

        if config.stage_debug:
            for line in result.debug_trace:
                print(line)
        print(f"\nANA> {result.response}")


if __name__ == "__main__":
    main()
