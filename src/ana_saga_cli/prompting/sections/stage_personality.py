"""Seção PERSONALIDADE DO ESTÁGIO — tom, compromissos e contrato real do estágio atual."""
from __future__ import annotations

from ana_saga_cli.domain.models import StageDefinition
from ana_saga_cli.prompting.text_utils import clean_text, join_lines


def _contract_lines(contract: dict[str, object]) -> list[str]:
    if not isinstance(contract, dict):
        return []

    lines: list[str] = []

    max_questions = contract.get("max_questions")
    if isinstance(max_questions, int) and max_questions >= 0:
        lines.append(f"no máximo {max_questions} pergunta por resposta")

    max_main_ideas = contract.get("max_main_ideas")
    if isinstance(max_main_ideas, int) and max_main_ideas >= 0:
        singular = "ideia central" if max_main_ideas == 1 else "ideias centrais"
        lines.append(f"no máximo {max_main_ideas} {singular} por resposta")

    if bool(contract.get("main_intention_only", False)):
        lines.append("mantenha uma intenção principal por resposta")
    if bool(contract.get("adapt_length_to_user", False)):
        lines.append("adapte o tamanho ao jeito e ao tamanho da mensagem do cliente")
    if bool(contract.get("avoid_forced_cta", False)):
        lines.append("não force próximo passo quando isso não fizer sentido")
    if bool(contract.get("avoid_corporate_language", False)):
        lines.append("evite linguagem corporativa, institucional ou pomposa")
    if bool(contract.get("never_surface_bpcf_root", False)):
        lines.append("não verbalize raciocínio interno, causa-raiz ou bastidor técnico")
    if bool(contract.get("prefer_short_messages", False)):
        lines.append("prefira mensagem curta quando o turno permitir")
    if bool(contract.get("ask_business_context_first_if_missing", False)):
        lines.append("se o negócio ainda estiver abstrato, ancore primeiro no que a empresa vende ou entrega")
    if bool(contract.get("avoid_feature_dump", False)):
        lines.append("não despeje feature, interface ou funcionalidade em sequência")
    if bool(contract.get("business_context_before_operational_pain", False)):
        lines.append("entenda o negócio antes de aprofundar dor operacional")
    if bool(contract.get("allow_light_refinement_if_answer_is_generic", False)):
        lines.append("se a resposta vier ampla, refine com leveza em vez de repetir a pergunta")
    if bool(contract.get("scenario_before_features", False)):
        lines.append("mostre a cena primeiro; a feature só entra para sustentar a cena")
    if bool(contract.get("require_variation_in_checking", False)):
        lines.append("varie a forma de checar aderência; não reuse sempre a mesma moldura")

    return lines


def build_stage_personality_section(stage: StageDefinition) -> str:
    lines: list[str] = []

    global_tone = [clean_text(item) for item in (stage.global_tone or []) if clean_text(item)]
    dos = [clean_text(item) for item in (stage.dos or []) if clean_text(item)]
    donts = [clean_text(item) for item in (stage.donts or []) if clean_text(item)]
    contract_lines = _contract_lines(stage.response_contract or {})

    if global_tone:
        lines.append("presença deste estágio:")
        lines.extend(global_tone)
    if dos:
        lines.append("priorize neste estágio:")
        lines.extend(dos)
    if donts:
        lines.append("evite neste estágio:")
        lines.extend(donts)
    if contract_lines:
        lines.append("contrato real deste estágio:")
        lines.extend(contract_lines)

    if not lines:
        return ""
    return f"PERSONALIDADE DO ESTÁGIO\n{join_lines(lines)}"
