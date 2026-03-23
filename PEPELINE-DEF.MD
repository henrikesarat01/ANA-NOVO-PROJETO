# PEPELINE DEF

## Objetivo

Este documento define o fluxo completo ativo da ANA, da mensagem do cliente até a resposta final do sistema.

Ele separa 3 coisas:

- caminho crítico atual;
- contratos internos que cada etapa escreve;
- módulos legados que ainda existem no projeto, mas não participam mais do pipeline principal.

---

## Visão Geral

```text
Mensagem do cliente
    │
    ▼
1. ConversationService.respond
    │
    ▼
2. ConversationTurnRunner.run
    │
    ├─ 2.1 Start Turn
    ├─ 2.2 State Update
    ├─ 2.3 Semantic Read
    ├─ 2.4 Counterparty Read
    ├─ 2.5 Turn Decision
    ├─ 2.6 Capability / Pricing Resolution
    ├─ 2.7 Prompt Assembly
    ├─ 2.8 Final LLM
    ├─ 2.9 Structural Validation / Repair
    └─ 2.10 Trace + Debug Bundle + State Commit
    │
    ▼
Resposta final da ANA
```

---

## Entry Point

### 1. `ConversationService.respond`

**Arquivo**

- [conversation_service.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/sales/conversation_service.py)

**Função**

- Recebe a mensagem do cliente.
- Entrega o turno para o `ConversationTurnRunner`.
- Retorna um `ReplyResult`.

**Saída**

- `stage_id`
- `response`
- `diagnostics_count`
- `last_hits`
- `debug_trace`
- `neural_debug`
- `markdown_debug`

---

## Caminho Crítico Ativo

### 2.1 Start Turn

**Onde acontece**

- [conversation_turn_runner.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/sales/conversation_turn_runner.py)

**O que faz**

- abre a sessão de debug da LLM;
- registra a nova mensagem no histórico;
- limpa estados transitórios do turno anterior;
- cria o primeiro trace.

**State alterado**

- `state.turns`
- `state.turn_count`
- `state.response_strategy = {}`
- `state.neurobehavior_state = {}`
- `state.surface_guidance = {}`

**Trace**

- `pipeline.turn.received`

---

### 2.2 State Update

**Módulos**

- [lead_analyzer.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/sales/lead_analyzer.py)
- [offer_sales_architecture.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/sales/offer_sales_architecture.py)

**Função**

- atualizar o que já se sabe sobre o caso;
- atualizar lacunas reais de contexto;
- carregar o blueprint ativo da oferta;
- manter isso agnóstico, sem escrever fala final.

**Principais contratos escritos**

- `state.lead_summary`
- `state.offer_sales_architecture`

**Campos importantes de `lead_summary`**

- `known_context_count`
- `minimum_context_ready`
- `commercial_scope_ready`
- `pain_known`
- `impact_known`
- `next_question_focus`
- `narrative_summary`

**Trace**

- `pipeline.state_update`

---

### 2.3 Semantic Read

**Módulo**

- [semantic_read_engine.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/sales/semantic_read_engine.py)

**Função**

- fazer uma leitura curta e estruturada do turno;
- decidir domínio semântico do turno;
- decidir se a conversa ainda deve segurar, pode ir para contexto ou pode abrir comercial.

**Contrato escrito**

- `state.neural_state`

**Campos principais**

- `topic_domain`
- `transition_permission`
- `transition_reason`
- `emotional_state`
- `communicative_intent`
- `decision_style`
- `resistance_level`
- `trust_signal`
- `needs_simplification`
- `clarity_note`
- `literal_response_risk`

**Trace**

- `pipeline.semantic_read`

---

### 2.4 Counterparty Read

**Módulo**

- [counterparty_model.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/sales/counterparty_model.py)

**Função**

- transformar a leitura semântica em um modelo interno da contraparte;
- definir se o cliente está explorando, comparando, testando preço, resistindo ou avançando.

**Contrato escrito**

- `state.counterparty_model`

**Campos principais**

- `interaction_mode`
- `counterparty_intent`
- `decision_stage`
- `question_priority`
- `trust_level`
- `resistance_level`
- `conversation_tension`
- `neutral_mode`

**Trace**

- `pipeline.counterparty`

---

### 2.5 Turn Decision

**Módulos**

- [commercial_pricing_policy.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/sales/commercial_pricing_policy.py)
- [conversation_policy_engine.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/sales/conversation_policy_engine.py)
- lógica de estágio em [conversation_turn_runner.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/sales/conversation_turn_runner.py)

**Função**

- decidir o que a ANA deve fazer neste turno;
- decidir se pode falar preço, segurar preço, explicar ou perguntar;
- decidir qual variável perguntar e em qual shape;
- decidir para qual estágio a conversa vai.

**Contratos escritos**

- `state.pricing_policy`
- `state.response_policy`
- `state.stage_id`

**Campos principais de `pricing_policy`**

- `price_response_mode`
- `validation_missing`
- `minimum_pricing_question_variable`
- `minimum_pricing_question_shape`
- `pricing_readiness_stage`
- `allow_range_quote`
- `allow_precise_quote`

**Campos principais de `response_policy`**

- `response_mode`
- `question_goal`
- `question_type`
- `question_variable`
- `question_shape`
- `question_constraints`
- `question_budget`
- `must_ask`
- `social_opening_only`

**Decisão de estágio**

- social hold: mantém `etapa_01_abertura`
- pergunta de contexto: puxa `etapa_03_contextualizacao_permissao`
- pergunta de dor: puxa `etapa_04_diagnostico_situacional`
- pergunta de impacto: puxa `etapa_05_diagnostico_impacto`
- pergunta de fit: puxa `etapa_06_qualificacao_fit`
- resposta de preço: puxa `etapa_09_ancoragem_valor` ou `etapa_12_negociacao_condicoes`

**Trace**

- `pipeline.turn_decision`

---

### 2.6 Capability / Pricing Resolution

**Módulos**

- [knowledge/retriever.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/knowledge/retriever.py)
- [surface_response_planner.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/sales/surface_response_planner.py)

**Função**

- buscar capacidades/funções mais próximas do caso;
- escolher hero/support function quando houver contexto suficiente;
- definir abertura e brevidade da resposta;
- manter isso interno, sem montar a fala final.

**Contratos escritos**

- `arsenal_hits`
- `state.surface_guidance`

**Campos principais de `surface_guidance`**

- `hero_saga_function`
- `support_saga_function`
- `response_opening`
- `brevity_mode`
- `active_cluster_name`

**Trace**

- `pipeline.capability_pricing`

---

### 2.7 Prompt Assembly

**Módulos**

- [turn_director.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/sales/turn_director.py)
- [assembler.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/prompting/assembler.py)
- [turn_plan.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/prompting/sections/turn_plan.py)
- [context.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/prompting/sections/context.py)
- [stage.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/prompting/sections/stage.py)
- [guardrails.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/prompting/sections/guardrails.py)
- [neural.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/prompting/sections/neural.py)

**Função**

- consolidar tudo num `TurnIntent`;
- montar um prompt final curto, limpo e sem fala hardcoded;
- passar para a LLM apenas terreno, contexto e restrições.

**Contrato principal**

- `TurnIntent`

**Campos principais do `TurnIntent`**

- `response_mode`
- `question_intent`
- `question_variable`
- `question_shape`
- `question_constraints`
- `question_reason`
- `must_ask`
- `pricing_posture`
- `style_posture`
- `opening_shape`
- `client_context`
- `main_pain`
- `operational_scene`
- `hero_function`
- `support_function`

**Saídas**

- `instructions`
- `prompt_input`

**Trace**

- `pipeline.prompt`

---

### 2.8 Final LLM

**Módulos**

- [openai_client.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/llm/openai_client.py)
- [cerebras_client.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/llm/cerebras_client.py)
- [mock_client.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/llm/mock_client.py)

**Função**

- gerar a fala final da ANA.

**Importante**

- só a LLM fala com o cliente;
- o código não monta saudação, pergunta ou resposta final.

**Trace**

- `pipeline.llm.request`

---

### 2.9 Structural Validation / Repair

**Módulo**

- [response_enforcer.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/sales/response_enforcer.py)

**Função**

- validar a forma da resposta;
- nunca inventar conteúdo novo;
- disparar no máximo um repair se a forma vier quebrada.

**O que valida**

- orçamento de perguntas;
- presença de pergunta quando `must_ask=true`;
- excesso de perguntas;
- shape proibido de pergunta;
- hold social sem pergunta.

**Resultado**

- `EnforcementDecision`
  - `response`
  - `reason`
  - `needs_repair`
  - `violation_type`

**Repair**

- roda uma nova chamada LLM curta;
- mantém fatos e intenção;
- corrige só forma.

**Trace**

- `pipeline.llm.response`

---

### 2.10 Trace + Debug Bundle + State Commit

**Módulos**

- [conversation_trace_collector.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/sales/conversation_trace_collector.py)
- [conversation_debug_bundle_builder.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/sales/conversation_debug_bundle_builder.py)

**Função**

- salvar a resposta final no estado;
- consumir a sessão de debug da LLM;
- montar `neural_debug`;
- montar `markdown_debug`;
- devolver o resultado consolidado.

**State alterado**

- `state.turns`
- `state.last_assistant_message`

**Saída final**

- `ReplyResult`

---

## Ordem Real de Trace

Na prática, o trace do caminho crítico ativo aparece assim:

1. `pipeline.turn.received`
2. `pipeline.state_update`
3. `pipeline.semantic_read`
4. `pipeline.counterparty`
5. `pipeline.turn_decision`
6. `pipeline.capability_pricing`
7. `pipeline.prompt`
8. `pipeline.llm.request`
9. `pipeline.llm.response`

---

## Estado Que Vai Sendo Escrito

Ao longo do turno, os campos principais do `ConversationState` são preenchidos nesta ordem:

1. `turns`, `turn_count`
2. `lead_summary`
3. `offer_sales_architecture`
4. `neural_state`
5. `counterparty_model`
6. `pricing_policy`
7. `response_policy`
8. `stage_id`
9. `surface_guidance`
10. `last_assistant_message`

---

## O Que Está No Código Mas Fora Do Caminho Crítico

Esses módulos ainda existem no projeto, mas não fazem parte do pipeline principal atual da resposta:

- [diagnostic_cluster_mapper.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/sales/diagnostic_cluster_mapper.py)
- [bpcf_engine.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/sales/bpcf_engine.py)
- [neural_router.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/sales/neural_router.py)
- [neural_analyzers.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/sales/neural_analyzers.py)
- [neural_synthesizer.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/sales/neural_synthesizer.py)
- [neural_guardrails.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/sales/neural_guardrails.py)
- [neurobehavior_engine.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/sales/neurobehavior_engine.py)
- [response_strategy_engine.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/sales/response_strategy_engine.py)
- [stage_router.py](/Users/user/Desenvolvimento/ana_saga_cli/src/ana_saga_cli/sales/stage_router.py)

Eles podem continuar úteis como compatibilidade, exploração futura ou debug, mas não definem mais a fala final da ANA no fluxo principal.

---

## Regra Operacional Final

O pipeline definitivo da ANA deve obedecer a esta sequência:

- primeiro entender o estado;
- depois ler semanticamente o turno;
- depois decidir o contrato do turno;
- depois resolver capacidade e postura comercial;
- depois montar um único prompt coerente;
- depois deixar a LLM falar;
- por fim validar forma e registrar trace.

Se qualquer camada intermediária tentar escrever a ANA, o pipeline saiu do contrato.
