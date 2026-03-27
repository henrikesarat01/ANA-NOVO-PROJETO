from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from ana_saga_cli.config import AppConfig


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _json_block(payload: Any) -> str:
    normalized = _normalize(payload)
    return json.dumps(normalized, ensure_ascii=False, indent=2, sort_keys=True)


def _normalize(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    return value


class ConversationMarkdownLogger:
    _AUXILIARY_LAYER_TO_FILE = {
        "v2.descoberta_nicho": "descoberta_nicho",
        "v2.desconstrucao_primeiros_principios": "desconstrucao_primeiros_principios",
        "v2.validacao_preco_contexto": "validacao_preco_contexto",
        "v2.exploracao_preco_contexto": "exploracao_preco_contexto",
        "v2.contexto_uso": "contexto_uso",
        "v2.storytelling": "storytelling",
    }

    def __init__(
        self,
        root_dir: Path,
        config: AppConfig,
        *,
        file_path: Path | None = None,
        reuse_existing: bool = False,
    ) -> None:
        self.root_dir = root_dir
        self.config = config
        if file_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.file_path = self.root_dir / f"ana_debug_{timestamp}.md"
            self._write_header()
            return
        self.file_path = file_path
        if not (reuse_existing and self.file_path.exists()):
            self._write_header()

    def _write_header(self) -> None:
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = "\n".join(
            [
                "# ANA Conversation Debug",
                "",
                f"- created_at: {created_at}",
                f"- provider: {self.config.provider}",
                f"- model: {self.config.model}",
                f"- stage_debug: {str(bool(self.config.stage_debug)).lower()}",
                f"- stage_debug_scope: {self.config.stage_debug_scope}",
                "",
                "---",
                "",
            ]
        )
        self.file_path.write_text(content, encoding="utf-8")

    def append_turn(self, result: Any, naturality_report: Any | None = None) -> None:
        payload = getattr(result, "markdown_debug", {}) or {}
        turn = payload.get("turn", {}) if isinstance(payload.get("turn", {}), dict) else {}
        messages = payload.get("messages", {}) if isinstance(payload.get("messages", {}), dict) else {}

        sections = [
            f"## Turn {turn.get('turn_count', '?')}",
            "",
            f"- entry_stage: {_clean_text(turn.get('entry_stage', '-'))}",
            f"- final_stage: {_clean_text(turn.get('final_stage', '-'))}",
            f"- final_stage_title: {_clean_text(turn.get('final_stage_title', '-'))}",
            "",
            "### Client Message",
            "",
            messages.get("user", ""),
            "",
            "### ANA Response",
            "",
            messages.get("assistant", ""),
            "",
        ]

        if naturality_report is not None:
            sections.extend(
                [
                    "### Naturality",
                    "",
                    f"- score: {getattr(naturality_report, 'score', '-')}",
                    f"- passed: {getattr(naturality_report, 'passed', '-')}",
                    f"- findings: {' | '.join(getattr(naturality_report, 'findings', []) or ['-'])}",
                    "",
                ]
            )

        sections.extend(self._render_decision_rationale(payload))

        sections.extend(self._render_structured_sections(payload))
        with self.file_path.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(sections))
            handle.write("\n\n---\n\n")
        self._append_auxiliary_turns(payload)

    def append_system_event(self, title: str, lines: list[str], payload: Any | None = None) -> None:
        sections = [
            f"## {title}",
            "",
        ]
        sections.extend(line for line in lines if _clean_text(line))
        sections.append("")
        if payload is not None:
            sections.extend(
                [
                    "### Payload",
                    "",
                    "```json",
                    _json_block(payload),
                    "```",
                    "",
                ]
            )
        with self.file_path.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(sections))
            handle.write("\n\n---\n\n")

    def _append_auxiliary_turns(self, payload: dict[str, Any]) -> None:
        turn = payload.get("turn", {}) if isinstance(payload.get("turn", {}), dict) else {}
        turn_count = turn.get("turn_count", "?")
        messages = payload.get("messages", {}) if isinstance(payload.get("messages", {}), dict) else {}
        llm_calls = payload.get("llm_calls", []) if isinstance(payload.get("llm_calls", []), list) else []
        forensic = payload.get("forensic", {}) if isinstance(payload.get("forensic", {}), dict) else {}
        loaded_files = forensic.get("loaded_files", {}) if isinstance(forensic.get("loaded_files", {}), dict) else {}

        for call in llm_calls:
            if not isinstance(call, dict):
                continue
            layer = _clean_text(call.get("layer", ""))
            helper_name = self._AUXILIARY_LAYER_TO_FILE.get(layer)
            if not helper_name:
                continue
            file_path = self._auxiliary_file_path(helper_name)
            if not file_path.exists():
                self._write_auxiliary_header(file_path, helper_name)
            prompt_path = self._auxiliary_prompt_path(helper_name, loaded_files)
            sections = [
                f"## Turn {turn_count}",
                "",
                f"- helper: {helper_name}",
                f"- layer: {layer}",
                f"- prompt_path: {prompt_path}",
                f"- duration_ms: {call.get('duration_ms', 0)}",
                f"- error: {_clean_text(call.get('error', '')) or '-'}",
                "",
                "### Client Message",
                "",
                str(messages.get("user", "") or ""),
                "",
                "### Input",
                "",
                "```text",
                str(call.get("user_input", "") or ""),
                "```",
                "",
                "### Output Used",
                "",
                "```json",
                _json_block(call.get("output_used", "")),
                "```",
                "",
                "### Raw Response",
                "",
                "```text",
                str(call.get("raw_response", "") or ""),
                "```",
                "",
                "### Parsed Output",
                "",
                "```json",
                _json_block(call.get("parsed_output", {})),
                "```",
                "",
                "### Instructions",
                "",
                "```text",
                str(call.get("instructions", "") or ""),
                "```",
                "",
            ]
            with file_path.open("a", encoding="utf-8") as handle:
                handle.write("\n".join(sections))
                handle.write("\n\n---\n\n")

    def _auxiliary_file_path(self, helper_name: str) -> Path:
        return self.file_path.with_name(f"{self.file_path.stem}_{helper_name}.md")

    def _write_auxiliary_header(self, file_path: Path, helper_name: str) -> None:
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = "\n".join(
            [
                f"# ANA Auxiliary Debug — {helper_name}",
                "",
                f"- created_at: {created_at}",
                f"- provider: {self.config.provider}",
                f"- model: {self.config.model}",
                f"- source_debug_file: {self.file_path.name}",
                "",
                "---",
                "",
            ]
        )
        file_path.write_text(content, encoding="utf-8")

    def _auxiliary_prompt_path(self, helper_name: str, loaded_files: dict[str, Any]) -> str:
        key = f"{helper_name}_prompt_path"
        return str(loaded_files.get(key, "") or "")

    def _render_decision_rationale(self, payload: dict[str, Any]) -> list[str]:
        turn = payload.get("turn", {}) if isinstance(payload.get("turn", {}), dict) else {}
        lead_summary = payload.get("lead_summary", {}) if isinstance(payload.get("lead_summary", {}), dict) else {}
        neural = payload.get("neural", {}) if isinstance(payload.get("neural", {}), dict) else {}
        neurobehavior = neural.get("neurobehavior", {}) if isinstance(neural.get("neurobehavior", {}), dict) else {}
        counterparty = payload.get("counterparty_model", {}) if isinstance(payload.get("counterparty_model", {}), dict) else {}
        policy = payload.get("policy", {}) if isinstance(payload.get("policy", {}), dict) else {}
        policy_initial = policy.get("initial", {}) if isinstance(policy.get("initial", {}), dict) else {}
        policy_final = policy.get("final", {}) if isinstance(policy.get("final", {}), dict) else {}
        strategy = payload.get("response_strategy", {}) if isinstance(payload.get("response_strategy", {}), dict) else {}
        stage_router = payload.get("stage_router", {}) if isinstance(payload.get("stage_router", {}), dict) else {}
        surface = payload.get("surface_guidance", {}) if isinstance(payload.get("surface_guidance", {}), dict) else {}
        messages = payload.get("messages", {}) if isinstance(payload.get("messages", {}), dict) else {}

        grouped = [
            ("Leitura do Cliente", [
                self._stage_rationale(turn, stage_router),
                self._context_rationale(lead_summary, counterparty),
            ]),
            ("Decisão de Policy", [
                self._policy_rationale(policy_initial, policy_final),
            ]),
            ("Decisão Neurobehavioral", [
                self._neuro_rationale(neural, neurobehavior),
            ]),
            ("Decisão de Strategy", [
                self._strategy_rationale(strategy, surface),
                self._response_rationale(messages.get("assistant", ""), surface),
            ]),
            ("Discrepâncias ou Riscos", self._risk_rationales(payload)),
        ]

        sections: list[str] = []
        for title, bullets in grouped:
            filtered = [_clean_text(item) for item in bullets if _clean_text(item)]
            if not filtered:
                continue
            sections.append(f"#### {title}")
            sections.append("")
            sections.extend(f"- {item}" for item in filtered)
            sections.append("")

        if not sections:
            return []

        lines = ["### Por Que o ANA Decidiu Isso", ""]
        lines.extend(sections)
        return lines

    def _risk_rationales(self, payload: dict[str, Any]) -> list[str]:
        lead_summary = payload.get("lead_summary", {}) if isinstance(payload.get("lead_summary", {}), dict) else {}
        policy = payload.get("policy", {}) if isinstance(payload.get("policy", {}), dict) else {}
        policy_final = policy.get("final", {}) if isinstance(policy.get("final", {}), dict) else {}
        neural = payload.get("neural", {}) if isinstance(payload.get("neural", {}), dict) else {}
        neurobehavior = neural.get("neurobehavior", {}) if isinstance(neural.get("neurobehavior", {}), dict) else {}
        strategy = payload.get("response_strategy", {}) if isinstance(payload.get("response_strategy", {}), dict) else {}
        messages = payload.get("messages", {}) if isinstance(payload.get("messages", {}), dict) else {}

        risks: list[str] = []
        if not bool(lead_summary.get("commercial_scope_ready", False)) and _clean_text(policy_final.get("question_goal", "")) == "pricing":
            risks.append("A policy está puxando pricing sem escopo comercial pronto; vale revisar precedência de contexto vs preço.")
        if _clean_text(neurobehavior.get("dominant_barrier", "")) == "high_cognitive_load" and _clean_text(strategy.get("response_format", "")) in {"medium_explanation", "medium_with_question", "reframe_then_question"}:
            risks.append("Há carga cognitiva alta, mas o formato ainda está potencialmente longo para o turno.")
        if "pressure" in (strategy.get("avoid", []) if isinstance(strategy.get("avoid", []), list) else []) and "?" in _clean_text(messages.get("assistant", "")):
            risks.append("O turno quer evitar pressão, mas ainda terminou em pergunta; conferir se isso ajuda ou só prolonga a conversa.")
        if not risks:
            risks.append("Nenhuma discrepância estrutural forte detectada neste turno.")
        return risks

    def _stage_rationale(self, turn: dict[str, Any], stage_router: dict[str, Any]) -> str:
        entry_stage = _clean_text(turn.get("entry_stage", "-"))
        final_stage = _clean_text(turn.get("final_stage", "-"))
        final_title = _clean_text(turn.get("final_stage_title", "-"))
        reason = _clean_text(stage_router.get("reason", ""))
        source = _clean_text(stage_router.get("source", ""))
        if entry_stage and final_stage and entry_stage != final_stage:
            detail = f"A conversa avançou de {entry_stage} para {final_stage} ({final_title})"
        else:
            detail = f"A conversa permaneceu em {final_stage} ({final_title})"
        if source:
            detail = f"{detail}, com decisão do stage router via {source}"
        if reason:
            detail = f"{detail}, porque {reason}"
        return detail

    def _context_rationale(self, lead_summary: dict[str, Any], counterparty: dict[str, Any]) -> str:
        known_context = lead_summary.get("known_context_count", 0)
        next_focus = _clean_text(lead_summary.get("next_question_focus", ""))
        intent = _clean_text(counterparty.get("counterparty_intent", ""))
        decision_stage = _clean_text(counterparty.get("decision_stage", ""))
        tension = _clean_text(counterparty.get("conversation_tension", ""))
        parts = [f"O estado do cliente foi lido com contexto conhecido={known_context}"]
        if next_focus:
            parts.append(f"próximo foco={next_focus}")
        if intent:
            parts.append(f"intenção percebida={intent}")
        if decision_stage:
            parts.append(f"etapa de decisão={decision_stage}")
        if tension:
            parts.append(f"tensão dominante={tension}")
        return "; ".join(parts)

    def _neuro_rationale(self, neural: dict[str, Any], neurobehavior: dict[str, Any]) -> str:
        state = neural.get("state", {}) if isinstance(neural.get("state", {}), dict) else {}
        emotional_state = _clean_text(state.get("emotional_state", ""))
        communicative_intent = _clean_text(state.get("communicative_intent", ""))
        dominant_barrier = _clean_text(neurobehavior.get("dominant_barrier", ""))
        levers = neurobehavior.get("recommended_levers", []) if isinstance(neurobehavior.get("recommended_levers", []), list) else []
        suppressed = neurobehavior.get("suppressed_moves", []) if isinstance(neurobehavior.get("suppressed_moves", []), list) else []
        parts = []
        if emotional_state or communicative_intent:
            parts.append(f"Neuralmente, o turno foi lido como emoção={emotional_state or '-'} e intenção={communicative_intent or '-'}")
        if dominant_barrier:
            parts.append(f"a barreira dominante foi {dominant_barrier}")
        if levers:
            parts.append(f"por isso o sistema puxou as alavancas {_clean_text(' | '.join(levers[:4]))}")
        if suppressed:
            parts.append(f"e tentou evitar {_clean_text(' | '.join(suppressed[:4]))}")
        return "; ".join(parts)

    def _policy_rationale(self, policy_initial: dict[str, Any], policy_final: dict[str, Any]) -> str:
        response_mode = _clean_text(policy_final.get("response_mode", policy_initial.get("response_mode", "")))
        main_intention = _clean_text(policy_final.get("main_intention", policy_initial.get("main_intention", "")))
        question_goal = _clean_text(policy_final.get("question_goal", policy_initial.get("question_goal", "")))
        question_type = _clean_text(policy_final.get("question_type", policy_initial.get("question_type", "")))
        question_anchor = _clean_text(policy_final.get("question_anchor", policy_initial.get("question_anchor", "")))
        budget = policy_final.get("question_budget", policy_initial.get("question_budget", ""))
        parts = [f"A policy final escolheu response_mode={response_mode or '-'} e intenção={main_intention or '-'}"]
        if question_goal or question_type:
            parts.append(f"com question_goal={question_goal or '-'} e question_type={question_type or '-'}")
        if str(budget) != "":
            parts.append(f"mantendo question_budget={budget}")
        if question_anchor:
            parts.append(f"e ancorando a pergunta em: {question_anchor}")
        return "; ".join(parts)

    def _strategy_rationale(self, strategy: dict[str, Any], surface: dict[str, Any]) -> str:
        goal = _clean_text(strategy.get("message_goal", ""))
        response_format = _clean_text(strategy.get("response_format", ""))
        axis = _clean_text(strategy.get("persuasion_axis", ""))
        moves = strategy.get("tactical_moves", []) if isinstance(strategy.get("tactical_moves", []), list) else []
        opening = _clean_text(surface.get("response_opening", ""))
        brevity = _clean_text(surface.get("brevity_mode", ""))
        parts = [f"A strategy transformou isso em goal={goal or '-'}, format={response_format or '-'} e axis={axis or '-'}"]
        if moves:
            parts.append(f"usando os movimentos {_clean_text(' | '.join(moves[:4]))}")
        if opening or brevity:
            parts.append(f"e materializando na superfície como opening={opening or '-'} com brevity={brevity or '-'}")
        return "; ".join(parts)

    def _response_rationale(self, response: object, surface: dict[str, Any]) -> str:
        opening = _clean_text(surface.get("response_opening", ""))
        question_anchor = _clean_text(surface.get("question_anchor", ""))
        response_text = _clean_text(response)
        if not response_text:
            return ""
        preview = response_text[:180]
        detail = f"A resposta final saiu com opening={opening or '-'}"
        if question_anchor:
            detail = f"{detail}, guiada por question_anchor={question_anchor}"
        return f"{detail}; preview: {preview}"

    def _render_structured_sections(self, payload: dict[str, Any]) -> list[str]:
        ordered_sections = [
            ("Lead Summary", payload.get("lead_summary", {})),
            ("Offer Sales Architecture", payload.get("offer_sales_architecture", {})),
            ("Neural", payload.get("neural", {})),
            ("Counterparty Model", payload.get("counterparty_model", {})),
            ("Policy", payload.get("policy", {})),
            ("Response Strategy", payload.get("response_strategy", {})),
            ("Stage Router", payload.get("stage_router", {})),
            ("Diagnostic Hypotheses", payload.get("diagnostic_hypotheses", {})),
            ("Retrieval", payload.get("retrieval", {})),
            ("Pricing", payload.get("pricing", {})),
            ("BPCF", payload.get("bpcf", {})),
            ("Surface Guidance", payload.get("surface_guidance", {})),
            ("Offer Context", payload.get("offer_context", {})),
            ("Channel Context", payload.get("channel_context", {})),
            ("Forensic", payload.get("forensic", {})),
            ("LLM Calls", payload.get("llm_calls", [])),
            ("Prompt", payload.get("prompt", {})),
            ("Pipeline Trace", payload.get("pipeline_trace", [])),
        ]

        lines: list[str] = []
        for title, section_payload in ordered_sections:
            lines.extend(
                [
                    f"### {title}",
                    "",
                    "```json",
                    _json_block(section_payload),
                    "```",
                    "",
                ]
            )
        return lines
