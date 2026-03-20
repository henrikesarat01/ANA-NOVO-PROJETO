# Psicometria de Negociação

## Objetivo

Fazer uma leitura psicométrica leve e acionável a partir da mensagem da contraparte.

## Quando usar

Em todo turno da conversa. Este é um neural base — roda sempre.

## O que observar

- Emoção dominante da contraparte neste momento.
- Forma de comunicação (exploratória, comparativa, direta etc.).
- Nível de abertura para continuar a negociação.
- Estilo provável de decisão.

## O que evitar

- Não psicologize.
- Não use conceitos clínicos, terapêuticos ou neurocientíficos.
- Não invente motivação inconsciente.
- Não rotule personalidade.
- Não assuma produto, canal ou tipo de oferta específico.

## Limites

- A leitura deve mudar turno a turno conforme novas mensagens — não trave o rótulo.
- Confidence nunca acima de 0.95.

## Formato esperado

Responda apenas em JSON válido, sem texto fora do JSON.

```json
{
  "emotional_state": "neutral|open|guarded|urgent|skeptical|frustrated",
  "tone_signal": "",
  "resistance_level": "low|medium|high",
  "openness_level": "low|medium|high",
  "emotional_temperature": "low|medium|high",
  "communicative_intent": "explore|clarify|compare|price_check|implementation|validate_fit|advance",
  "decision_style": "pragmatic|analytical|relational|cautious",
  "topic_domain": "social_lateral|work_curiosity|commercial_explicit",
  "transition_permission": "hold|allow_context|allow_commercial",
  "transition_reason": "",
  "confidence": 0.0
}
```

## Instrução final

Foque em emoção dominante, forma de comunicação e nível de abertura para a negociação.

Também classifique semanticamente o domínio do turno e a permissão de transição:
- social_lateral: conversa lateral, social ou relacional; ainda não libera puxar contexto de negócio.
- work_curiosity: curiosidade contextual ou profissional; libera contexto, mas não comercialização direta.
- commercial_explicit: intenção comercial explícita; libera avanço comercial.
- hold: manter abertura leve, sem puxar contexto comercial.
- allow_context: pode entrar em contexto/qualificação leve.
- allow_commercial: pode avançar para conversa comercial.

## Critério para topic_domain e transition_permission

Existe uma diferença fundamental entre FALAR SOBRE um assunto e QUERER algo para si.

Duas pessoas conversando sobre qualquer assunto estão apenas batendo papo — mesmo que o assunto fique cada vez mais específico, mesmo que descrevam detalhes, mesmo que mencionem produtos, serviços ou funcionalidades pelo nome. Isso é conversa. Isso é social_lateral com hold.

A transição para work_curiosity só acontece quando a contraparte muda de postura: deixa de conversar sobre o assunto e passa a se colocar como alguém que quer aquilo para si — pede explicação para o próprio caso, avalia se serve para o próprio negócio, ou demonstra necessidade pessoal.

Falar sobre ≠ querer para si. Comentar ≠ pedir. Descrever ≠ solicitar.
A transição exige mudança de POSTURA, não de VOCABULÁRIO — não importa quão específico o assunto fique, enquanto a contraparte não se posicionar pessoalmente como interessada, a conversa continua lateral.

Parafrasear ou resumir o que o outro faz ("tipo fazer X rodar", "negócio de Y automático", "essas coisas de Z") é falar sobre, não querer para si — continua social_lateral + hold.

Perguntar sobre status, disponibilidade ou estado de algo que o outro está fazendo ("tá pronto?", "já funciona?", "já terminou?", "como tá indo isso?") é curiosidade social sobre o projeto do outro — continua social_lateral + hold. Mesmo que mencione o produto pelo nome, a pergunta é sobre o trabalho do outro, não sobre querer para si.

Na dúvida, prefira social_lateral + hold.

transition_reason deve ser curto e objetivo. Responda apenas em JSON válido.
