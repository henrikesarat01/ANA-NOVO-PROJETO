# Pipeline V2 da ANA

## Objetivo

Reduzir o pipeline da ANA para um fluxo em que:

- cada etapa tenha uma responsabilidade clara;
- a LLM entre apenas onde existe nuance real para interpretar ou escrever;
- o código não escreva a fala da ANA;
- a decisão do turno exista em um contrato semântico único;
- a validação final seja estrutural, sem reescrever a resposta.

---

## Princípios

1. Cada passo faz uma coisa só.
2. O código decide contrato, não copy.
3. A LLM lê nuance humana e escreve a resposta final.
4. Saídas internas devem ser estruturadas e curtas.
5. Nenhuma camada intermediária injeta pergunta pronta.
6. O último passo pode validar forma, mas não reinventar conteúdo.

---

## Arquitetura V2

```text
📩 Mensagem do cliente
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ 1. State Update                                              │
│ 2. Semantic Read (IA curta e estruturada)                    │
│ 3. Turn Decision                                             │
│ 4. Capability / Pricing Resolution                           │
│ 5. Prompt + Final LLM                                        │
│ 6. Structural Validation + Trace                             │
└──────────────────────────────────────────────────────────────┘
       │
       ▼
💬 Resposta da ANA
```

---

## Etapas

### 1. State Update

**Função**

Atualizar o estado conhecido da conversa com memória, fatos já confirmados, etapa atual e lacunas objetivas.

**Entrada**

- mensagem atual do cliente;
- histórico recente;
- memória acumulada do lead;
- contexto conhecido da oferta.

**Saída**

Um `TurnState` enxuto, com fatos conhecidos, fatos faltantes, etapa atual e sinais objetivos do turno.

**Observação**

Essa etapa pode ser majoritariamente determinística, mas não deve tentar "entender o cliente inteiro" por heurística dura.

---

### 2. Semantic Read

**Função**

Usar uma chamada curta de IA para interpretar o turno do cliente em dimensão humana e conversacional.

**O que essa leitura deve resolver**

- intenção principal do cliente;
- nível de clareza ou confusão;
- tensão, resistência ou abertura;
- sinal de pedido de preço;
- se o cliente está buscando contexto, validação, comparação ou fechamento.

**Saída**

Uma estrutura curta e tipada, não texto livre. Exemplo de campos:

- `primary_intent`
- `clarity_level`
- `tension_level`
- `price_signal`
- `readiness_signal`
- `conversation_pull`

**Observação**

Essa camada existe porque tentar fazer isso "sem IA" tende a virar lista rígida de keywords.

---

### 3. Turn Decision

**Função**

Tomar a decisão central do turno. Aqui fica a fonte única da verdade sobre o que a ANA deve fazer agora.

**Saída**

Um contrato curto, por exemplo:

- `response_mode`
- `must_ask`
- `question_variable`
- `question_shape`
- `question_constraints`
- `pricing_posture`
- `stage_action`

**Exemplo de responsabilidade**

- decidir se é turno de saudar, perguntar, explicar, situar preço ou responder preço;
- decidir qual variável precisa ser destravada;
- decidir o formato da pergunta;
- definir postura de preço sem ainda escrever a fala.

**Observação**

Essa etapa deve ser determinística sobre contrato, mas rica o suficiente para não empurrar tudo para o prompt final.

---

### 4. Capability / Pricing Resolution

**Função**

Resolver o encaixe entre o caso do cliente, a capacidade relevante do SAGA e a postura comercial correta.

**O que entra aqui**

- catálogo de capacidades e funções;
- contrato de pricing da oferta;
- requisitos mínimos para abrir preço;
- variáveis comerciais faltantes;
- compatibilidade entre dor, operação e capacidade.

**Saída**

Uma resolução interna, sem texto client-facing, por exemplo:

- `active_capability`
- `supporting_capabilities`
- `pricing_allowed`
- `pricing_missing_variables`
- `pricing_reason`
- `fit_confidence`

**Observação**

Aqui desaparece a duplicação de pricing em duas passadas e também a disputa entre planner, policy e pricing.

---

### 5. Prompt + Final LLM

**Função**

Montar uma única instrução final, limpa e coerente, para a LLM escrever a fala da ANA.

**O prompt deve receber**

- filosofia e limites da ANA;
- estado atual da conversa;
- leitura semântica do cliente;
- contrato do turno;
- resolução de capability/pricing;
- restrições estruturais do turno.

**O prompt não deve receber**

- pergunta pronta escrita em Python;
- fallback textual de pricing;
- menu de opções para o cliente;
- múltiplas camadas repetindo a mesma decisão em formatos diferentes.

**Saída**

A resposta humana final da ANA.

---

### 6. Structural Validation + Trace

**Função**

Validar forma e registrar debug. Essa etapa não existe para "corrigir a copy"; ela existe para impedir quebra estrutural.

**O que pode validar**

- quantidade de perguntas;
- presença de pergunta quando `must_ask=true`;
- ausência de menu taxonômico quando proibido;
- ausência de preço quando `pricing_allowed=false`;
- limites de tamanho ou formato.

**O que não pode fazer**

- inventar nova pergunta;
- humanizar `question_variable`;
- reescrever a resposta com copy hardcoded;
- trocar o conteúdo sem passar novamente pela LLM.

**Fallback permitido**

No máximo uma passada de `LLM repair` para corrigir forma. Se ainda falhar, o turno fecha como inválido para o chamador.

---

## Contrato Central do Turno

O núcleo da arquitetura V2 é um contrato único, curto e reaproveitável. Ele substitui reconciliações tardias entre várias engines.

### Campos recomendados

- `response_mode`
  - Define o tipo macro de resposta do turno.
- `must_ask`
  - Diz se este turno obrigatoriamente precisa conter pergunta.
- `question_variable`
  - Chave semântica estável, como `uso_atual_do_whatsapp` ou `tipo_de_operacao`.
- `question_shape`
  - Formato da pergunta: `open_context`, `open_pain`, `fit_check` ou `approval_check`.
- `question_constraints`
  - Restrições estruturais, como `single_question`, `avoid_menu`, `avoid_taxonomy`.
- `pricing_posture`
  - Postura comercial do turno: bloquear, situar, qualificar ou responder.
- `stage_action`
  - Diz se mantém ou avança etapa.

### Regra importante

Esse contrato é interno. Ele não deve carregar frase pronta para o cliente.

---

## O Que Sai do Pipeline Atual

### Sai

- dupla reconciliação de `Conversation Policy`;
- dupla rodada de `Pricing Engine`;
- `Surface Planner` escrevendo forma client-facing;
- `Response Enforcer` cortando ou reescrevendo semântica;
- leitura do cliente em texto solto para uso operacional;
- heurística keyword-based para entender intenção comercial complexa.

### Fica, mas reposicionado

- análise do cliente continua existindo, mas concentrada em `Semantic Read`;
- estágio continua existindo, mas como parte do contrato do turno;
- pricing continua existindo, mas em resolução única;
- debug continua existindo, mas como trace enxuto e rastreável.

---

## Mapeamento do Pipeline Atual Para o V2

| Pipeline atual | Pipeline V2 |
|---|---|
| Lead Analyzer + parte da memória | State Update |
| Neural Router + Neural Analyzers + Counterparty + Neurobehavior | Semantic Read |
| Conversation Policy + Response Strategy + Stage Router | Turn Decision |
| Diagnostic Cluster + Arsenal + Pricing + BPCF | Capability / Pricing Resolution |
| Prompt Builder + LLM Final | Prompt + Final LLM |
| Response Enforcer + debug | Structural Validation + Trace |

---

## O Que Não Fazer

### 1. Não tentar substituir nuance humana por regra dura

Se o sistema tentar descobrir intenção, tensão e pedido implícito de preço só por string matching, ele volta a quebrar as regras da ANA.

### 2. Não deixar o contrato do turno pobre demais

`saudar | perguntar | explicar | responder preço` sozinho é simples, mas insuficiente. A ANA também precisa saber o que perguntar, com que shape e sob qual postura comercial.

### 3. Não usar texto livre como contrato operacional

Texto é bom para leitura humana. Para orquestração, piora consistência, testes e debug.

### 4. Não eliminar o fail-safe final

Remover o enforcer temático faz sentido. Remover toda validação estrutural não faz.

---

## Plano de Migração

### Fase 1

Criar o contrato central do turno e fazer `policy`, `strategy`, `stage` e `pricing` passarem a emitir esse contrato, sem texto pronto.

### Fase 2

Concentrar leitura humana do cliente em uma única etapa de `Semantic Read`, com saída estruturada e curta.

### Fase 3

Mover capability/pricing para uma resolução única baseada em registry e contrato externo da oferta.

### Fase 4

Reduzir o prompt final para uma única instrução coerente, sem conciliações paralelas.

### Fase 5

Deixar a validação final puramente estrutural, com no máximo uma rodada de `repair`.

---

## Regra de Ouro

> O código decide estrutura.
> A IA interpreta nuance.
> Só a LLM final escreve a ANA.
> A última camada valida forma, não inventa conteúdo.
