# Pipeline V3 da ANA

## De onde vem

- V1 (18 passos): funciona, mas engines disputam a fala e o prompt final vira colcha de retalhos.
- V2 (6 passos): direção certa, contratos bons, mas Semantic Read separado pode ser desperdício e Turn Decision "determinístico" vira espaguete se for código procedural.
- V3: pega os contratos da V2, junta Semantic Read com a resposta final, e usa tabela declarativa no lugar de if/elif.

---

## Princípios

1. A ANA só tem **uma voz**: o passo que escreve a fala. Nenhum outro módulo gera texto pro cliente.
2. Decisão de turno é **uma só**, num lugar só, sem reconciliação depois.
3. IA entra **uma vez** por turno — lê nuance e fala ao mesmo tempo.
4. Todo o resto é **estado, limite e contrato**. Código organiza, não interpreta.
5. Falha visível é melhor que fallback invisível.

---

## Pipeline

```text
📩 Mensagem do cliente
       │
       ▼
┌────────────────────────────────────────────────────────────┐
│                                                            │
│  1. STATE UPDATE (código)                                  │
│                                                            │
│     Consolida o que já sabe e o que falta.                 │
│     Não interpreta emoção. Não decide resposta.            │
│                                                            │
│     Entrada: mensagem + histórico + memória                │
│     Saída:   state_snapshot                                │
│                                                            │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  2. TURN DECISION (código + tabela declarativa)            │
│                                                            │
│     Uma única decisão por turno.                           │
│     Usa state_snapshot + tabela de regras.                 │
│     Não chama IA. Não gera fala.                           │
│                                                            │
│     Entrada: state_snapshot + decision_table               │
│     Saída:   turn_contract                                 │
│                                                            │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  3. CAPABILITY + PRICING (código)                          │
│                                                            │
│     Resolve a parte comercial com base no contrato.        │
│     Escolhe função relevante e postura de preço.           │
│     Não gera fala.                                         │
│                                                            │
│     Entrada: state_snapshot + turn_contract                │
│     Saída:   business_contract                             │
│                                                            │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  4. PROMPT + LLM (IA — única chamada)                      │
│                                                            │
│     A IA faz duas coisas numa chamada só:                  │
│     a) lê o cliente (intenção, emoção, resistência)        │
│     b) escreve a fala da ANA                               │
│                                                            │
│     A saída é estruturada:                                 │
│     { semantic_read: {...}, response: "..." }              │
│                                                            │
│     A leitura semântica fica registrada no trace.          │
│     A resposta vai pro cliente.                            │
│                                                            │
│     Entrada: state + turn_contract + business_contract     │
│     Saída:   semantic_read + raw_response                  │
│                                                            │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  5. STRUCTURAL GUARD + TRACE (código)                      │
│                                                            │
│     Valida forma, não conteúdo.                            │
│     Se a forma estiver errada, pede 1 repair ao LLM.      │
│     Se o repair falhar, manda a raw_response original.     │
│                                                            │
│     Entrada: raw_response + turn_contract                  │
│     Saída:   final_response + trace                        │
│                                                            │
└────────────────────────────────────────────────────────────┘
       │
       ▼
💬 Resposta da ANA
```

---

## Detalhe de cada passo

---

### 1. State Update

O que faz:
- Adiciona a mensagem ao histórico
- Atualiza contexto conhecido (nicho, porte, uso do WhatsApp, etc.)
- Atualiza contexto faltante (o que ainda precisa perguntar)
- Avança ou mantém o estágio da conversa
- Conta turnos

O que **não** faz:
- Não classifica emoção (isso é trabalho de IA)
- Não decide o que responder
- Não gera texto

Contrato de saída — `state_snapshot`:

```json
{
  "turn_number": 3,
  "stage_id": "contextualization",
  "known_context": {
    "nicho": "funerária",
    "porte": null,
    "uso_whatsapp": null,
    "dor_principal": null
  },
  "missing_variables": ["porte", "uso_whatsapp", "dor_principal"],
  "price_requested": false,
  "conversation_history": ["..."],
  "last_client_message": "cara, eu tenho uma funeraria"
}
```

Como sabe o que está preenchido e o que falta:
- Extração simples de entidades do histórico (regex + keywords básicas)
- Para casos ambíguos, deixa como `null` — a IA no passo 4 resolve

---

### 2. Turn Decision

O que faz:
- Recebe o `state_snapshot`
- Consulta uma tabela declarativa de regras
- Produz um contrato único que diz **o que** a ANA deve fazer neste turno

**Por que tabela declarativa e não if/elif:**

```yaml
# decision_table.yaml (exemplo simplificado)

- when:
    stage: opening
    turn_number: 1
  then:
    response_mode: greet
    must_ask: false
    pricing_posture: block

- when:
    stage: contextualization
    missing_variables_count: ">= 2"
    price_requested: false
  then:
    response_mode: ask
    question_goal: context
    question_variable: "first(missing_variables)"
    question_shape: open
    question_constraints: [single_question, no_menu, no_taxonomy]
    pricing_posture: block
    must_ask: true
    question_budget: 1

- when:
    stage: contextualization
    price_requested: true
    missing_variables_count: ">= 1"
  then:
    response_mode: ask
    question_goal: pricing_deflection
    question_variable: "first(missing_variables)"
    question_shape: open_context
    question_constraints: [single_question, no_menu, no_taxonomy]
    pricing_posture: deflect
    must_ask: true
    question_budget: 1

- when:
    stage: diagnostic
    missing_variables_count: 0
  then:
    response_mode: explain
    question_goal: null
    pricing_posture: range
    must_ask: false
```

Vantagens:
- Testável: cada regra é um caso de teste
- Legível: quem lê a tabela entende o comportamento
- Sem conflito: a primeira regra que bate vence
- Extensível: adicionar regra nova não quebra as outras

Contrato de saída — `turn_contract`:

```json
{
  "response_mode": "ask",
  "question_goal": "context",
  "question_variable": "uso_whatsapp",
  "question_shape": "open",
  "question_constraints": ["single_question", "no_menu", "no_taxonomy"],
  "pricing_posture": "block",
  "must_ask": true,
  "question_budget": 1
}
```

---

### 3. Capability + Pricing

O que faz:
- Baseado no `turn_contract` e no `state_snapshot`, escolhe qual função do SAGA é relevante agora
- Define a postura de preço concreta (bloquear, dar faixa, dar valor)
- Define o que muda se o cliente responder a pergunta

O que **não** faz:
- Não monta frase
- Não decide se pergunta ou explica (isso já foi decidido no passo 2)

Contrato de saída — `business_contract`:

```json
{
  "hero_function": "Carrossel de Produtos",
  "support_function": "Detalhes do Produto",
  "pricing_readiness": "A",
  "price_mode": "block",
  "next_unlock": "saber uso_whatsapp permite dar faixa de preço"
}
```

Implementação:
- Registry de capacidades do SAGA (YAML ou dicionário)
- Matching simples: nicho + dor → função
- Pricing readiness: checklist de variáveis preenchidas

---

### 4. Prompt + LLM (a única chamada de IA)

Essa é a diferença principal da V3 em relação à V2.

Na V2, a IA entra duas vezes:
1. Semantic Read (IA lê o cliente)
2. Final LLM (IA escreve a resposta)

Na V3, **uma chamada só faz os dois**:

```
Você é a ANA, assistente comercial do SAGA.

## Contexto do caso
- Cliente: dono de funerária
- Turno: 3
- Etapa: contextualização
- Já sabe: nicho = funerária
- Falta: porte, uso do WhatsApp, dor principal

## Seu contrato para este turno
- Modo: perguntar
- Objetivo: contexto
- Variável: uso_whatsapp
- Forma: pergunta aberta
- Restrições: uma pergunta só, sem menu, sem taxonomia
- Preço: não falar valor ainda

## Função relevante
- Carrossel de Produtos (não mencionar ainda)

## O que você deve fazer
1. Primeiro, analise internamente o cliente (formato JSON abaixo)
2. Depois, escreva sua fala

## Formato de resposta
{
  "semantic_read": {
    "communicative_intent": "...",
    "emotional_state": "...",
    "resistance_level": "...",
    "literal_response_risk": "..."
  },
  "response": "sua fala aqui"
}
```

Por que funciona:
- O GPT já vai ler a conversa inteira pra escrever a resposta — pedir a análise semântica junto não custa quase nada extra
- A análise semântica aparece **antes** da resposta no output, então o GPT usa ela como "pensamento" antes de falar
- Latência cai pela metade (1 chamada em vez de 2)
- Custo cai pela metade
- O semantic_read fica salvo no trace pra debug

**Quando isso NÃO funciona e precisa separar:**
- Se o Turn Decision (passo 2) precisar de `emotional_state` ou `resistance_level` pra decidir o `response_mode`. Nesse caso, a decisão depende da leitura semântica, e aí precisa ser separado.
- Na V3, o Turn Decision é baseado em estado + tabela, não em emoção. A emoção influencia o **tom** da resposta (que o GPT ajusta sozinho), não o **tipo** de ação.

---

### 5. Structural Guard + Trace

O que valida:
- `must_ask=true` mas a resposta não tem pergunta → repair
- Resposta tem mais de 1 pergunta → repair
- Pergunta em formato menu ("A, B ou C?") → repair
- Resposta ultrapassa limite de tamanho → repair

O que **não** faz:
- Não reescreve conteúdo
- Não troca a pergunta por outra
- Não injeta frase pronta
- Não faz mais de 1 tentativa de repair

Repair funciona assim:
```
Sua resposta anterior violou uma restrição estrutural:
[descreve a violação]

Reescreva mantendo a mesma intenção, corrigindo apenas:
[o que precisa mudar]
```

Se o repair também falhar:
- Manda a `raw_response` original
- Registra a falha no trace
- Não inventa fallback

Por que `raw_response` como fallback:
- Uma resposta com pergunta a mais é melhor que silêncio
- Uma resposta com menu é melhor que "desculpe, tive um problema"
- O trace registra a falha, então dá pra ver e corrigir a tabela de decisão depois

Trace registra:
```json
{
  "turn": 3,
  "state_snapshot": { "..." },
  "turn_contract": { "..." },
  "business_contract": { "..." },
  "semantic_read": { "..." },
  "raw_response": "...",
  "guard_violations": [],
  "repair_attempted": false,
  "final_response": "..."
}
```

Um turno inteiro cabe em ~30 linhas de trace. Contra as 2.000+ linhas de hoje.

---

## Comparação V1 × V2 × V3

| | V1 (18 passos) | V2 (6 passos) | V3 (5 passos) |
|---|---|---|---|
| Chamadas de IA por turno | 4+ | 2 | 1 (normal) ou 2 (repair) |
| Quem decide o turno | 8 engines em conflito | 1 decisão determinística | 1 decisão por tabela declarativa |
| Quem escreve a fala | GPT + enforcer reescrevendo | só GPT | só GPT |
| Leitura do cliente | engine separada (neural) | IA separada (semantic read) | embutida na mesma chamada |
| Reconciliação | policy 2x, pricing 2x | nenhuma | nenhuma |
| Validação final | enforcer que reescreve | validador estrutural | guard estrutural + fallback claro |
| Tamanho do trace por turno | 2.000+ linhas | ~200 linhas | ~30 linhas |
| Comportamento de falha | fallback hardcoded | "fail closed" (indefinido) | raw_response original |

---

## Mapeamento: código atual → V3

| Hoje (18 passos) | V3 | O que acontece |
|---|---|---|
| Lead Analyzer | State Update | vira consolidação de estado |
| Neural Router + Analyzers + Guardrails | Prompt (passo 4) | IA lê nuance dentro da chamada final |
| Counterparty Model + Neurobehavior | Prompt (passo 4) | análise embutida no semantic_read |
| Conversation Policy (2x) | Turn Decision | uma vez só, por tabela |
| Stage Router | Turn Decision | subdecisão na tabela |
| Response Strategy | Turn Decision | absorvido pelo response_mode |
| Surface Planner | removido | sem motivo de existir |
| Pricing Engine (2x) | Capability + Pricing | uma vez só |
| Diagnostic Cluster Mapper | Capability + Pricing | matching direto |
| Arsenal Retriever | Capability + Pricing | lookup simples |
| BPCF Engine | Capability + Pricing | lógica interna |
| Prompt Builder | Prompt + LLM | template direto |
| Response Enforcer | Structural Guard | só forma, não conteúdo |

---

## Estrutura de arquivos

```
src/ana_saga_cli/
├── pipeline/
│   ├── state_update.py          # passo 1
│   ├── turn_decision.py         # passo 2
│   ├── capability_pricing.py    # passo 3
│   ├── prompt_llm.py            # passo 4
│   ├── structural_guard.py      # passo 5
│   └── runner.py                # orquestra os 5 passos
├── data/
│   ├── decision_table.yaml      # regras do passo 2
│   ├── capability_registry.yaml # funções do SAGA
│   └── personality.md           # personalidade da ANA
├── domain/
│   ├── contracts.py             # state_snapshot, turn_contract, business_contract
│   └── stage_ids.py             # estágios da conversa
├── llm/
│   ├── base.py
│   └── openai_client.py
└── cli.py
```

---

## Decision Table: como funciona

A tabela vive em YAML. Cada regra tem `when` (condições) e `then` (contrato).

A engine percorre de cima pra baixo. **A primeira regra que bate, vence.** Sem conflito, sem reconciliação.

Ordem importa: regras mais específicas ficam em cima, mais genéricas embaixo.

```yaml
rules:

  # ─── Abertura ───
  - name: "saudação inicial"
    when:
      turn_number: 1
    then:
      response_mode: greet
      must_ask: false
      pricing_posture: block

  - name: "social hold (turnos 2-3)"
    when:
      turn_number: ["<=", 3]
      stage: opening
    then:
      response_mode: social
      must_ask: false
      pricing_posture: block

  # ─── Preço pedido cedo ───
  - name: "preço pedido sem contexto"
    when:
      price_requested: true
      missing_variables_count: [">=", 2]
    then:
      response_mode: ask
      question_goal: pricing_deflection
      question_variable: "$first_missing"
      question_shape: open_context
      question_constraints: [single_question, no_menu, no_taxonomy]
      pricing_posture: deflect
      must_ask: true
      question_budget: 1

  # ─── Contexto incompleto ───
  - name: "falta contexto"
    when:
      stage: contextualization
      missing_variables_count: [">=", 1]
    then:
      response_mode: ask
      question_goal: context
      question_variable: "$first_missing"
      question_shape: open
      question_constraints: [single_question, no_menu, no_taxonomy]
      pricing_posture: block
      must_ask: true
      question_budget: 1

  # ─── Diagnóstico ───
  - name: "contexto completo, hora de conectar"
    when:
      stage: diagnostic
      missing_variables_count: 0
    then:
      response_mode: explain
      question_goal: null
      pricing_posture: range
      must_ask: false

  # ─── Preço liberado ───
  - name: "pode falar preço"
    when:
      pricing_readiness: [">=", "C"]
    then:
      response_mode: price
      pricing_posture: precise
      must_ask: false

  # ─── Fallback ───
  - name: "caso não coberto"
    when: {}
    then:
      response_mode: ask
      question_goal: context
      question_variable: "$first_missing"
      question_shape: open
      question_constraints: [single_question]
      pricing_posture: block
      must_ask: true
      question_budget: 1
```

Testar uma regra = testar uma linha da tabela. Sem efeito colateral.

---

## Slot de memória entre conversas

O State Update tem um campo `conversation_memory` que hoje começa vazio a cada conversa.

Quando o sistema for pra produção com persistência, esse campo vira o ponto de entrada pra memória de longo prazo:

```json
{
  "conversation_memory": {
    "previous_conversations": 0,
    "known_from_before": {},
    "last_interaction": null
  }
}
```

Não precisa implementar agora. Mas o slot já existe no contrato, então não quebra nada quando chegar.

---

## Implementação

Corte limpo. Não migração gradual.

- Criar a pasta `pipeline/` do zero
- Não tocar no código atual até a V3 rodar
- Escrever testes primeiro (TDD) contra os contratos
- Quando os testes passarem e a conversa funcionar, deletar o código antigo

---

## Regra final

> Uma IA por turno.
> Uma decisão por turno.
> Uma voz por turno.
> Todo o resto é estado, limite e contrato.
