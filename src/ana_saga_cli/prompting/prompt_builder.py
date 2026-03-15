from __future__ import annotations

from ana_saga_cli.domain.models import ConversationState, StageDefinition, ArsenalEntry, ProductFact
from ana_saga_cli.prompting.global_rules import GLOBAL_RESPONSE_RULES


def _join_lines(items: list[str], prefix: str = "- ") -> str:
    return "\n".join(f"{prefix}{item}" for item in items)


def _bool_label(value: object) -> str:
    return "sim" if bool(value) else "não"


class PromptBuilder:
    def build(self, state: ConversationState, stage: StageDefinition, user_message: str, arsenal_hits: list[ArsenalEntry], facts: list[ProductFact], bpcf_framework: dict) -> tuple[str, str]:
        lead_summary = state.lead_summary or {}
        diagnostic_hypotheses = state.diagnostic_hypotheses or {}
        diagnostic_clusters = diagnostic_hypotheses.get("diagnostic_clusters", [])
        surface_guidance = state.surface_guidance or {}
        response_policy = state.response_policy or {}
        diagnostics_preview = "\n".join(
            f"- Problema percebido: {entry.problem}\n  Característica útil: {entry.characteristic}\n  Produto/solução: {entry.product}"
            for entry in state.diagnostics[-4:]
        ) or "- ainda sem mapa acumulado relevante"

        arsenal_preview = "\n".join(
            f"- Função: {hit.function_name}\n  Problema: {hit.problem}\n  Característica: {hit.characteristic}\n  Produto/solução: {hit.product}"
            for hit in arsenal_hits[:6]
        ) or "- sem hits fortes neste turno"

        facts_preview = "\n".join(
            f"- {fact.name}: {fact.description}"
            for fact in facts[:8]
        ) or "- use apenas fatos gerais da solução configurada"

        lead_summary_preview = "\n".join(
            [
                f"- nicho/tipo de negócio conhecido: {_bool_label(lead_summary.get('niche_known'))}",
                f"- oferta conhecida: {_bool_label(lead_summary.get('offer_known'))}",
                f"- modelo operacional conhecido: {_bool_label(lead_summary.get('operation_model_known'))}",
                f"- uso do WhatsApp conhecido: {_bool_label(lead_summary.get('channel_usage_known'))}",
                f"- tipo principal de cliente conhecido: {_bool_label(lead_summary.get('customer_type_known'))}",
                f"- especificidade do nicho: {lead_summary.get('niche_specificity', 'unknown')}",
                f"- contexto base suficiente: {_bool_label(lead_summary.get('minimum_context_ready'))}",
                f"- escopo comercial mínimo pronto: {_bool_label(lead_summary.get('commercial_scope_ready'))}",
                f"- dor principal já apareceu: {_bool_label(lead_summary.get('pain_known'))}",
                f"- impacto principal já apareceu: {_bool_label(lead_summary.get('impact_known'))}",
                f"- impacto suficiente para avançar: {_bool_label(lead_summary.get('impact_context_ready'))}",
                f"- foco da próxima pergunta: {lead_summary.get('next_question_focus', 'context')}",
                f"- resumo do impacto: {lead_summary.get('impact_summary', 'ainda sem impacto consolidado')}",
                f"- turnos na etapa 5: {lead_summary.get('stage5_turn_count', 0)}",
                f"- lacunas restantes: {', '.join(lead_summary.get('missing_context_slots', [])) or 'nenhuma lacuna crítica'}",
                f"- resumo do caso: {lead_summary.get('narrative_summary', 'ainda em construção')}",
                f"- evidência recente: {lead_summary.get('evidence_summary', 'ainda sem evidência consolidada')}",
            ]
        )

        cluster_preview_lines = [
            f"- contexto do negócio: {diagnostic_hypotheses.get('business_context', 'ainda sem mapa de nicho consolidado')}",
            f"- nicho: {diagnostic_hypotheses.get('niche', 'não definido')}",
            f"- segmento: {diagnostic_hypotheses.get('segment', 'não definido')}",
            f"- tipo de oferta: {diagnostic_hypotheses.get('offer_type', 'não definido')}",
            f"- modelo operacional: {diagnostic_hypotheses.get('operation_model', 'não definido')}",
            f"- hipóteses prioritárias: {' | '.join(diagnostic_hypotheses.get('priority_hypotheses', [])[:4]) or 'ainda sem hipóteses fortes'}",
            f"- lacunas de contexto: {' | '.join(diagnostic_hypotheses.get('known_context_gaps', [])[:4]) or 'sem lacunas críticas'}",
        ]
        for index, cluster in enumerate(diagnostic_clusters[:3], start=1):
            cluster_preview_lines.extend(
                [
                    f"- cluster_{index}.nome: {cluster.get('cluster_name', '') or 'sem nome'}",
                    f"- cluster_{index}.frente: {cluster.get('operational_front', '') or 'sem frente definida'}",
                    f"- cluster_{index}.problema: {cluster.get('problem', '') or 'sem problema definido'}",
                    f"- cluster_{index}.causa: {cluster.get('cause', '') or 'sem causa definida'}",
                    f"- cluster_{index}.raiz: {cluster.get('root_cause', '') or 'sem raiz definida'}",
                    f"- cluster_{index}.efeitos: {' | '.join(cluster.get('operational_effects', [])[:3]) or 'sem efeitos mapeados'}",
                    f"- cluster_{index}.sinais: {' | '.join(cluster.get('observable_signs', [])[:3]) or 'sem sinais mapeados'}",
                    f"- cluster_{index}.funcoes_saga: {' | '.join(cluster.get('saga_functions', [])[:4]) or 'sem funções mapeadas'}",
                    f"- cluster_{index}.logica_resolucao: {cluster.get('resolution_logic', '') or 'sem lógica definida'}",
                ]
            )
        hypothesis_preview = "\n".join(cluster_preview_lines)

        surface_guidance_preview = "\n".join(
            [
                f"- cluster ativo: {surface_guidance.get('active_cluster_name', 'não definido')}",
                f"- motivo da escolha: {surface_guidance.get('selection_reason', 'sem justificativa consolidada')}",
                f"- foco de superfície: {surface_guidance.get('surface_focus', 'sem foco definido')}",
                f"- tensão principal: {surface_guidance.get('surface_tension', 'sem tensão definida')}",
                f"- cena operacional: {' | '.join(surface_guidance.get('operational_scene', [])[:4]) or 'sem cena operacional priorizada'}",
                f"- pistas de especificidade: {' | '.join(surface_guidance.get('specificity_cues', [])[:4]) or 'sem pistas adicionais'}",
                f"- função do SAGA para citar: {surface_guidance.get('suggested_saga_function', 'nenhuma função priorizada')}",
                f"- por que essa função encaixa: {surface_guidance.get('saga_fit_reason', 'sem justificativa adicional')}",
                f"- âncora de pergunta: {surface_guidance.get('question_anchor', 'não perguntar se não destravar algo relevante')}",
                f"- evitar na fala: {' | '.join(surface_guidance.get('avoid_topics', [])[:4]) or 'sem alertas extras'}",
                f"- modo de brevidade: {surface_guidance.get('brevity_mode', 'medium')}",
                f"- abertura preferida: {surface_guidance.get('response_opening', 'validate_first')}",
            ]
        )

        saga_connection_preview = "\n".join(
            [
                f"- função prioritária 1: {arsenal_hits[0].function_name if len(arsenal_hits) > 0 else 'sem prioridade definida'}",
                f"- função prioritária 2: {arsenal_hits[1].function_name if len(arsenal_hits) > 1 else 'sem prioridade definida'}",
                f"- objetivo dessa conexão: {response_policy.get('saga_connection_goal', 'conectar uma função concreta do SAGA ao que o cliente acabou de dizer')}",
            ]
        )

        response_policy_preview = "\n".join(
            [
                f"- orçamento de perguntas: {response_policy.get('question_budget', 1)}",
                f"- must_ask: {_bool_label(response_policy.get('must_ask'))}",
                f"- optional_ask: {_bool_label(response_policy.get('optional_ask'))}",
                f"- contexto suficiente para avançar: {_bool_label(response_policy.get('enough_context_to_move'))}",
                f"- pedido comercial direto detectado: {_bool_label(response_policy.get('commercial_direct_question_detected'))}",
                f"- saudação social pura: {_bool_label(response_policy.get('social_opening_only'))}",
                f"- contexto suficiente para responder preço: {_bool_label(response_policy.get('enough_context_for_pricing_response'))}",
                f"- responder agora em vez de perguntar: {_bool_label(response_policy.get('answer_now_instead_of_asking'))}",
                f"- modo da resposta: {response_policy.get('response_mode', 'ask')}",
                f"- intenção principal: {response_policy.get('main_intention', 'confirm_impact')}",
                f"- motivo da pergunta: {response_policy.get('ask_reason', 'só pergunte se isso realmente destravar algo importante')}",
                f"- objetivo da pergunta: {response_policy.get('question_goal', 'context')}",
            ]
        )

        conduction_rules = []
        if stage.stage_id in {
            "etapa_01_abertura",
            "etapa_02_conexao_inicial",
            "etapa_03_contextualizacao_permissao",
            "etapa_04_diagnostico_situacional",
            "etapa_05_diagnostico_impacto",
            "etapa_06_qualificacao_fit",
            "etapa_09_ancoragem_valor",
            "etapa_11_oferta",
        }:
            conduction_rules = [
                "Antes de perguntar, valide e reaproveite algo específico que o cliente acabou de dizer.",
                "Crie uma micro-continuação narrativa curta mostrando o que isso significa no cenário dele.",
                "Conecte essa leitura a 1 ou 2 funções concretas do SAGA que façam sentido para o que o cliente acabou de dizer, sem soar catálogo.",
                "Se ainda for perguntar, explique por que a próxima pergunta importa e só depois faça a pergunta.",
                "Nunca faça pergunta seca, checklist explícito ou sequência de interrogatório.",
                "Use no máximo 2 blocos curtos antes da pergunta.",
                "Perguntas são recurso escasso: use só se realmente destravarem contexto, dor, fit ou decisão comercial.",
            ]
            if diagnostic_hypotheses.get("business_context"):
                conduction_rules.append(
                    "Use o mapa interno de clusters diagnósticos para escolher a frente operacional mais aderente ao que o cliente acabou de dizer."
                )
                conduction_rules.append(
                    "Transforme esse cluster em narrativa curta, justificativa de pergunta e conexão com função do SAGA, sem tratar o mapa como texto pronto."
                )
            if surface_guidance.get("active_cluster_name"):
                conduction_rules.append(
                    "Use o plano interno de superfície abaixo como orientação: ele já aponta a leitura operacional mais aderente deste turno."
                )
                conduction_rules.append(
                    "Não copie o mapa nem o plano. Reescreva do zero em linguagem humana, usando no máximo 2 elementos concretos da cena operacional."
                )
                conduction_rules.append(
                    "Evite frases que serviriam igual para vários nichos. Mostre o mundo operacional do cliente com 1 tensão concreta e 1 leitura curta."
                )
                conduction_rules.append(
                    "Se citar SAGA, cite só 1 função e encaixe isso como continuação natural do cenário, não como catálogo."
                )
            if surface_guidance.get("brevity_mode") == "short":
                conduction_rules.append(
                    "Neste turno, seja curto: 2 a 4 linhas úteis antes de encerrar ou perguntar."
                )
            if surface_guidance.get("response_opening") == "answer_first":
                conduction_rules.append(
                    "Abra respondendo ou situando o pedido principal do cliente antes de ampliar leitura ou perguntar."
                )
            if bool(lead_summary.get("minimum_context_ready", False)):
                conduction_rules.append(
                    "O contexto base já está suficiente. Não volte a perguntar nicho, oferta, canal, cliente ou modelo operacional. Avance para gargalo, peso principal ou impacto."
                )
            if lead_summary.get("next_question_focus") == "pain":
                conduction_rules.append(
                    "A próxima pergunta deve buscar onde mais pesa hoje ou qual é o principal gargalo, sem refazer contexto base."
                )
            if lead_summary.get("next_question_focus") == "impact":
                conduction_rules.append(
                    "A próxima resposta deve aprofundar impacto, consequência ou transição natural para solução, sem voltar para contexto base."
                )
            if lead_summary.get("next_question_focus") == "advance":
                conduction_rules.append(
                    "Não refine mais impacto. Resuma o peso principal em uma frase, conecte com 1 ou 2 funções do SAGA e avance."
                )
            if response_policy.get("question_budget", 1) <= 0 or response_policy.get("answer_now_instead_of_asking"):
                conduction_rules.append(
                    "Não faça pergunta neste turno. Consolide o que entendeu, conecte com funções do SAGA e avance explicando ou respondendo diretamente."
                )
            if stage.stage_id == "etapa_01_abertura" and response_policy.get("social_opening_only"):
                conduction_rules.append(
                    "O cliente só mandou uma saudação social. Responda saudação + disponibilidade leve em 1 ou 2 linhas e não faça pergunta de negócio, área ou qualificação."
                )
                conduction_rules.append(
                    "Não tente descobrir nicho, segmento, produto ou serviço nesse turno."
                )
            if response_policy.get("commercial_direct_question_detected") and response_policy.get("enough_context_for_pricing_response"):
                conduction_rules.append(
                    "O cliente pediu valor/implementação de forma direta e já existe contexto suficiente. Responda agora, com ancoragem curta e honestidade. Não volte para investigação."
                )
            if response_policy.get("commercial_direct_question_detected") and not lead_summary.get("commercial_scope_ready", False):
                conduction_rules.append(
                    "O cliente pediu preço/como funciona, mas o nicho ou o que ele vende ainda não está claro o suficiente. Não dê faixa nem oferta fechada agora."
                )
                conduction_rules.append(
                    "Responda de forma ampla sobre como funciona e faça só uma pergunta estruturante para descobrir nicho, segmento, produto ou serviço vendido."
                )
            if response_policy.get("response_mode") == "pricing_answer":
                conduction_rules.append(
                    "Se não houver tabela exata no contexto, seja transparente sobre isso, mas ainda responda de forma útil, situada e sem empurrar novas perguntas."
                )
            if stage.stage_id == "etapa_11_oferta" and not lead_summary.get("commercial_scope_ready", False):
                conduction_rules.append(
                    "Mesmo estando na etapa 11, não verbalize faixa, preço, mensalidade, implantação ou proposta fechada sem escopo comercial mínimo pronto."
                )
                conduction_rules.append(
                    "Não improvise número, faixa ou condição comercial. Responda só como funciona em termos amplos e faça uma única pergunta para descobrir nicho, segmento, produto ou serviço vendido."
                )
                conduction_rules.append(
                    "Se o cliente insistir em preço cedo demais, seja honesto: explique que primeiro precisa entender o tipo de operação antes de cravar valor."
                )
            if stage.stage_id == "etapa_05_diagnostico_impacto":
                conduction_rules.append(
                    "Na etapa 5, faça apenas uma intenção principal por resposta: confirmar impacto, conectar com o SAGA ou avançar para solução/valor."
                )
                conduction_rules.append(
                    "Não combine validação, narrativa, explicação de função, ancoragem de valor e nova pergunta no mesmo turno."
                )
                conduction_rules.append(
                    "Se a dor e o impacto já estiverem claros, a etapa 5 deve ser curta e terminar rápido."
                )
                if int(lead_summary.get("stage5_turn_count", 0)) >= 2 or bool(lead_summary.get("force_stop_impact", False)):
                    conduction_rules.append(
                        "O orçamento da etapa 5 acabou. Avance obrigatoriamente e não faça nova pergunta de impacto."
                    )
                if bool(lead_summary.get("impact_context_ready", False)):
                    conduction_rules.append(
                        "O impacto já está suficiente: não reabra confirmação de impacto. Use isso só para conectar SAGA e avançar."
                    )

        instructions = f"""{_join_lines(GLOBAL_RESPONSE_RULES)}

ETAPA ATUAL
- id: {stage.stage_id}
- título: {stage.title}
- objetivo: {stage.goal}

O QUE FAZER NESTA ETAPA
{_join_lines(stage.dos)}

O QUE EVITAR NESTA ETAPA
{_join_lines(stage.donts)}

CONTRATO DE RESPOSTA
- no máximo {stage.response_contract.get('max_questions', 1)} pergunta
- uma intenção principal por turno
- adapt_length_to_user={stage.response_contract.get('adapt_length_to_user', True)}
- avoid_forced_cta={stage.response_contract.get('avoid_forced_cta', True)}
- avoid_corporate_language={stage.response_contract.get('avoid_corporate_language', True)}
- never_surface_bpcf_root={stage.response_contract.get('never_surface_bpcf_root', True)}

BPCF
- fluxo central: {bpcf_framework['core_mechanism']['flow']}
- regra: nunca verbalizar causa ou raiz
- use o mapa diagnóstico acumulado apenas como orientação silenciosa

MAPA DIAGNÓSTICO ACUMULADO
{diagnostics_preview}

ESTADO ESTRUTURADO DO LEAD
{lead_summary_preview}

MAPA DE HIPÓTESES DIAGNÓSTICAS DO NEGÓCIO
{hypothesis_preview}

PLANO INTERNO DE SUPERFÍCIE
{surface_guidance_preview}

POLÍTICA CONVERSACIONAL DESTE TURNO
{response_policy_preview}

CONEXÃO PRIORITÁRIA COM O SAGA
{saga_connection_preview}

HITS DE CONHECIMENTO NESTE TURNO
{arsenal_preview}

FATOS DO PRODUTO DISPONÍVEIS
{facts_preview}

CONDUÇÃO DESTA RESPOSTA
{_join_lines(conduction_rules) if conduction_rules else '- siga a etapa atual com fluidez e sem soar robótico'}
"""

        user_input = f"""HISTÓRICO RECENTE
{_join_lines([f"{turn.role}: {turn.content}" for turn in state.turns[-6:]], prefix="")}

MENSAGEM ATUAL DO CLIENTE
{user_message}

TAREFA
Responda ao cliente em português do Brasil, com naturalidade alta, linguagem simples e tom de WhatsApp.
Use a etapa atual e o conhecimento fornecido para orientar a resposta.
Não metaexplique sua estratégia.
"""
        return instructions, user_input
