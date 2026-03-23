# Pipeline da ANA

---

## Arquitetura atual (18 passos)

```
📩 Mensagem do cliente
       │
       ▼
┌─────────────────────────────────────────────────┐
│  1. Lead Analyzer                               │
│  2. Offer Sales Architecture                    │
│  3. Neural Router + Analyzers                   │
│  4. Counterparty Model                          │
│  5. Neurobehavior Engine                        │
│  6. Conversation Policy (1ª)                    │
│  7. Response Strategy                           │
│  8. Stage Router                                │
│  9. Diagnostic Cluster Mapper                   │
│ 10. Arsenal Retriever                           │
│ 11. Pricing Engine (1ª)                         │
│ 12. BPCF Engine                                 │
│ 13. Surface Planner                             │
│ 14. Pricing Engine (2ª)                         │
│ 15. Conversation Policy (2ª)                    │
│ 16. Prompt Builder                              │
│ 17. LLM (GPT-5.4)                              │
│ 18. Response Enforcer                           │
└─────────────────────────────────────────────────┘
       │
       ▼
💬 Resposta da ANA
```

**Problema:** muita gente decidindo ao mesmo tempo. Um diz "pergunta", outro diz "explica", outro diz "segura preço". No final a ANA recebe uma instrução confusa e fala coisa estranha.

---

## Nova arquitetura (5 passos)

```
📩 Mensagem do cliente
       │
       ▼
┌─────────────────────────────────────────────────┐
│                                                 │
│  1. ENTENDER                                    │
│     Lê a mensagem e atualiza o que sabe:        │
│     - Quem é o cliente (nicho, porte)           │
│     - O que ele já contou (contexto)            │
│     - O que ainda falta saber                   │
│     - Se pediu preço ou não                     │
│     - Em que momento a conversa está            │
│                                                 │
│     Tudo isso é código simples, sem IA.         │
│     Só organiza o que já tem.                   │
│                                                 │
├─────────────────────────────────────────────────┤
│                                                 │
│  2. DECIDIR                                     │
│     Uma única decisão com 4 opções:             │
│                                                 │
│     "saudar"  → é o primeiro contato,           │
│                  só responde a saudação          │
│                                                 │
│     "perguntar" → falta info importante,        │
│                    faz UMA pergunta              │
│                                                 │
│     "explicar" → já tem contexto,               │
│                   conecta o SAGA ao caso         │
│                                                 │
│     "responder preço" → tem info suficiente,    │
│                          pode falar valor        │
│                                                 │
│     Também decide simples, sem IA.              │
│     Regra clara, sem conflito.                  │
│                                                 │
├─────────────────────────────────────────────────┤
│                                                 │
│  3. LER O CLIENTE (IA)                          │
│     Uma chamada de IA que responde:             │
│     - Como o cliente está se sentindo?          │
│     - O que ele quis dizer de verdade?          │
│     - Qual o melhor tom pra responder?          │
│                                                 │
│     Uma resposta curta em texto, não JSON.      │
│     Serve de contexto pro passo 4.              │
│                                                 │
├─────────────────────────────────────────────────┤
│                                                 │
│  4. MONTAR INSTRUÇÃO + RESPONDER (IA)           │
│     Junta tudo numa instrução limpa:            │
│     - Quem é a ANA (personalidade)              │
│     - Momento da conversa (etapa)               │
│     - O que decidiu fazer (passo 2)             │
│     - Como o cliente está (passo 3)             │
│     - O que não fazer (limites)                 │
│                                                 │
│     Manda pro GPT. Ele escreve a fala.          │
│     Uma instrução, sem contradição.             │
│                                                 │
├─────────────────────────────────────────────────┤
│                                                 │
│  5. REGISTRAR                                   │
│     Salva tudo pra debug:                       │
│     - O que entendeu                            │
│     - O que decidiu                             │
│     - O que a IA leu do cliente                 │
│     - O que montou de instrução                 │
│     - O que a ANA respondeu                     │
│                                                 │
└─────────────────────────────────────────────────┘
       │
       ▼
💬 Resposta da ANA
```

---

## Por que funciona melhor

| Hoje (18 passos) | Nova (5 passos) |
|---|---|
| 8 engines decidem ao mesmo tempo | 1 decisão clara, sem conflito |
| Cada engine gera um JSON gigante | Dados simples passando de um passo pro outro |
| Policy roda 2 vezes tentando conciliar | Roda 1 vez porque não tem o que conciliar |
| Pricing roda 2 vezes | Roda 1 vez dentro do passo 2 |
| ResponseEnforcer corta resposta quebrada | Não precisa — a instrução já é limpa |
| Prompt com 5.000+ caracteres de instrução | Prompt curto, direto, sem repetição |
| Debug com 9.000 linhas por conversa | Debug com ~200 linhas por conversa |
| 4+ chamadas de IA por turno | 2 chamadas de IA por turno |

---

## Regra de ouro

> Cada passo faz **uma coisa só**.
> Nenhum passo contradiz o anterior.
> A IA só entra onde **precisa pensar** (ler emoção, escrever fala).
> Todo o resto é **regra simples no código**.
