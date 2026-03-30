## Demo de Produto Contextualizada

Este prompt nao responde ao cliente. Ele monta uma demonstracao interna do produto aplicada ao cenario real do cliente.

O objetivo e construir um modelo de apresentacao que mostre como o produto funcionaria dentro da operacao do cliente — no nicho dele, com o que ele vende, no jeito que o negocio dele funciona.

Isso nao e um pitch. Nao e uma lista de funcoes. Nao e um comparativo generico.
E uma simulacao concreta de como a operacao do cliente ficaria com o produto rodando.

Se o input trouxer `memoria_estavel`, use como base real sobre o negocio do cliente — o que ele vende, como funciona, quem opera, onde pesa.
Se o input trouxer `memoria_de_progressao`, use para saber o que ja foi dito na conversa e nao repetir camadas ja entregues.
Se o input trouxer `resultados_previos` com `descoberta_nicho`, use as funcoes ja ranqueadas como materia-prima. Nao refaca o ranqueamento.

## Bloco de Descontaminacao Lexical do Produto

Se o input trouxer `descricao_curta`, `descricao_longa` ou `funcoes`, trate isso como base semantica de consulta, nao como molde textual.

Trate o produto como fonte latente de sentido, nao como superficie textual reutilizavel.

Proibicoes duras:
- nao fazer parafrase semantica muito proxima
- nao fazer eco lexical
- nao fazer reempacotamento do wording
- nao preservar os nucleos lexicais dominantes do material
- nao manter a espinha lexical da redacao original
- nao fazer transposicao estrutural da frase-base
- nao preservar a ordem de apresentacao das ideias
- nao preservar a estrutura sintatica dominante do material

Procedimento obrigatorio:
1. faca primeiro uma leitura semantica abstrata
2. reduza o material a sentido latente, dinamica, implicacao e concretude
3. so depois escreva
4. escreva por relexicalizacao e mudanca de eixo perceptivo, nao por troca de sinonimo
5. se a saida ainda soar como versao reescrita do input, ela esta errada

Regras operacionais:
- nao cite os nomes dos campos
- nao copie a redacao original
- nao reaproveite sequencias de palavras marcantes do produto

## O que voce precisa construir

Monte uma simulacao de como o produto entraria na operacao do cliente.

A simulacao deve percorrer o caminho real que um cliente do negocio faria — desde o primeiro contato ate o pos-venda — mostrando em cada ponto o que o produto resolveria.

Pense assim: se voce fosse explicar para o dono daquele negocio como o dia a dia dele mudaria com o produto, o que voce mostraria?

Nao e sobre funcoes isoladas. E sobre a sequencia real de eventos que acontece naquele tipo de negocio e como cada momento ficaria diferente.

## Como pensar a simulacao

Primeiro entenda a operacao:
- o que o cliente vende, oferece ou opera
- como o publico dele chega e pede
- onde a operacao trava, perde tempo ou perde venda
- quem faz o que no dia a dia

Depois percorra o fluxo natural do negocio do cliente:
- alguem aparece interessado — como isso acontece hoje e como ficaria
- essa pessoa quer ver opcoes — como resolve hoje e como ficaria
- essa pessoa decide comprar — como fecha hoje e como ficaria
- essa pessoa some no meio — o que acontece hoje e o que mudaria
- a empresa quer falar com quem ja comprou ou sumiu — como faz hoje e como ficaria
- o dono quer ver como o negocio esta indo — como sabe hoje e como ficaria

Cada ponto do fluxo deve:
- partir da realidade daquele nicho, nao de uma descricao generica
- mostrar o antes concreto (como funciona sem o produto)
- mostrar o depois concreto (como ficaria com o produto)
- conectar funcoes reais do produto a momentos reais da operacao

## O que nao fazer

- nao listar funcoes soltas sem conexao com a operacao
- nao usar linguagem de pitch ou apresentacao comercial
- nao inventar detalhes que nao vieram no contexto
- nao repetir camadas que ja foram entregues na conversa
- nao montar a simulacao de forma generica que serviria pra qualquer negocio
- nao escrever texto para o cliente — isso e materia-prima interna
- nao usar tom conversacional
- nao incluir introducao, conclusao ou convite


## Além da operação interna

Não reduza o valor da oferta apenas ao que ela organiza dentro da rotina imediata.

Sempre que o produto tiver alcance mais amplo, considere também o que ela muda fora da execução visível do dia a dia.

Pense se a oferta:
- altera a forma como o negócio sustenta interesse ao longo do tempo
- reduz perdas que antes eram atribuídas a outros pontos do negócio
- melhora continuidade, percepção, aproveitamento, retorno ou clareza
- corrige efeitos que parecem nascer fora, mas também dependem da forma como a operação responde, acompanha ou mantém relação

Não trate essa camada como efeito colateral automático.
Só traga isso quando houver base real na própria natureza do produto.

Não transforme essa leitura em lista de setores.
Não cite áreas só para parecer estratégico.
Não use exemplos prontos como muleta.

A função aqui é perceber se a oferta, além de organizar a execução interna, também muda a forma como o negócio se sustenta, se reaproveita, se mantém presente, se torna compreensível ou evita perder valor entre uma ponta e outra.

Crie uma historia de auto impacto e contexto e narrativa forte

Se isso existir, incorpore essa dimensão como parte real do valor da oferta.
Se não existir, não force.

## Saida

Retorne somente YAML valido, sem markdown e sem texto extra.

Formato obrigatorio:

nicho_identificado: <o que o cliente vende, oferece ou opera>
operacao_resumida: <como a operacao funciona hoje em 1-2 linhas>
fluxo_simulado:
  - momento: <descricao curta do momento no fluxo do negocio>
    hoje: <como funciona hoje sem o produto>
    com_produto: <como ficaria com o produto rodando>
    funcoes_envolvidas:
      - <nome da funcao do produto que entra nesse momento>
    impacto: <o que muda na pratica para a operacao>
  - momento: <proximo momento do fluxo>
    hoje: <como funciona hoje>
    com_produto: <como ficaria>
    funcoes_envolvidas:
      - <nome da funcao>
    impacto: <o que muda>
gargalo_principal: <o ponto da operacao onde o produto faria mais diferenca>
visao_do_dono: <o que o dono do negocio veria de diferente no dia a dia com o produto rodando>

Regras:
- o fluxo deve ter entre 4 e 8 momentos, dependendo da complexidade do negocio
- cada momento deve ser especifico para aquele nicho, nao generico
- funcoes_envolvidas devem ser funcoes reais do produto carregado
- se o contexto nao for suficiente para montar a simulacao, devolva fluxo_simulado vazio
- nao incluir explicacao extra
- nao incluir frases para o cliente
