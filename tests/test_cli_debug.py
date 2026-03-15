from ana_saga_cli.cli import _render_hypothesis_debug, _render_scope_debug


def test_render_hypothesis_debug_with_empty_map() -> None:
    lines = _render_hypothesis_debug({})
    assert lines == ["[debug] mapa_nicho: -"]


def test_render_scope_debug_with_empty_summary() -> None:
    assert _render_scope_debug({}) == "[debug] lead_scope niche_specificity=unknown commercial_scope_ready=False"


def test_render_scope_debug_with_summary() -> None:
    assert _render_scope_debug({"niche_specificity": "generic", "commercial_scope_ready": False}) == (
        "[debug] lead_scope niche_specificity=generic commercial_scope_ready=False"
    )


def test_render_hypothesis_debug_with_context_map() -> None:
    lines = _render_hypothesis_debug(
        {
            "business_context": "Imobiliária com WhatsApp concentrando lead, visita e proposta.",
            "niche": "imobiliária",
            "segment": "locação e venda residencial",
            "offer_type": "imóveis e intermediação",
            "operation_model": "captação por anúncios e atendimento por WhatsApp",
            "priority_hypotheses": ["triagem inicial fraca"],
            "known_context_gaps": ["faixa principal de lead"],
            "diagnostic_clusters": [
                {
                    "cluster_name": "triagem de intenção",
                    "operational_front": "entrada do lead",
                    "problem": "lead de locação e compra entra no mesmo fluxo",
                    "cause": "não há separação de intenção na entrada",
                    "root_cause": "necessidades diferentes são tratadas como iguais",
                    "operational_effects": ["priorização ruim"],
                    "observable_signs": ["mesmo número para tudo"],
                    "saga_functions": ["Botões", "Qualificação de Lead"],
                    "resolution_logic": "separar intenção logo no início melhora a condução",
                }
            ],
        }
    )

    assert lines[0] == "[debug] mapa_nicho.contexto=Imobiliária com WhatsApp concentrando lead, visita e proposta."
    assert any("Qualificação de Lead" in line for line in lines)
    assert any("lead de locação e compra entra no mesmo fluxo" in line for line in lines)
