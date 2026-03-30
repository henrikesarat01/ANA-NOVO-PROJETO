# Auxiliares — ANA v2

Os auxiliares agora foram organizados por **família de função**, e não mais só por nome solto.
Isso deixa mais claro o papel de cada prompt e facilita adicionar novos frameworks sem misturar tudo.

## Famílias Ativas

### Orquestração

- `orquestracao/cerebro_conversa/cerebro_conversa.md`
  papel: ler o turno atual e decidir qual capacidade principal deve governar a próxima resposta

### Leituras de Contexto

- `leituras_de_contexto/contexto_uso/contexto_uso.md`
  papel: montar um recorte plausível de realidade para apoiar explicações

- `leituras_de_contexto/descoberta_nicho/descoberta_nicho.md`
  papel: entender o que mais encaixa da oferta no nicho, segmento, produto ou serviço do cliente

### Modelos Mentais

- `modelos_mentais/desconstrucao_primeiros_principios/desconstrucao_primeiros_principios.md`
  papel: reduzir o caso a poucas causas e tensões úteis

- `modelos_mentais/storytelling/storytelling.md`
  papel: gerar eixo narrativo de conflito, curiosidade e virada

- `modelos_mentais/tecnicas_feynman/tecnicas_feynman.md`
  papel: simplificar explicações sem esvaziar o entendimento

### Frameworks de Negociação

- `frameworks_negociacao/spin_selling.md`
  papel: organizar a leitura de negociação por situação, problema, implicação e lógica da mudança

### Preço

- `preco/exploracao_preco_contexto/exploracao_preco_contexto.md`
  papel: explorar o melhor movimento conversacional antes de falar preço

- `preco/preco_contexto/preco_contexto.md`
  papel: filosofia de condução humana em conversas de preço com pouco contexto

- `preco/validacao_preco_contexto/validacao_preco_contexto.md`
  papel: validar o que já basta e o que ainda importa antes de falar valor

## Legado

Os prompts antigos de `decisor_etapas/` continuam no repositório como referência histórica.
O fluxo ativo hoje usa `orquestracao/cerebro_conversa/cerebro_conversa.md`.

## Princípio de Manutenção

Antes de criar um novo auxiliar, a pergunta certa é:

- ele é uma leitura de contexto?
- ele é um modelo mental?
- ele é uma capacidade de preço?
- ele é orquestração?

Se não encaixar em nenhuma dessas famílias, a taxonomia provavelmente ainda precisa evoluir.
