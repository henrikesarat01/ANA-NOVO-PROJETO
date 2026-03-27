# ANA Auxiliary Debug — contexto_uso

- created_at: 2026-03-26 23:28:25
- provider: openai
- model: gpt-5.4
- source_debug_file: ana_debug_20260326_232703.md

---
## Turn 4

- helper: contexto_uso
- layer: v2.contexto_uso
- prompt_path: /Users/user/Desenvolvimento/ana_saga_cli/ana_v2/auxiliares/contexto_uso/contexto_uso.md
- duration_ms: 9473.268
- error: -

### Client Message

legal cara, e como é esse sistema ai ?

### Input

```text
mensagem_atual_do_cliente: legal cara, e como é esse sistema ai ?
historico_recente:
- role: cliente
  content: e ai meu brother, como vai ?
- role: ANA
  content: E aí meu brother, tudo certo por aqui 😄 e contigo?
- role: cliente
  content: maravilha, tu ta programando agora ? kkk
- role: ANA
  content: kkkk pior que sim 😅 mexendo nuns negócios aqui agora mesmo.
- role: cliente
  content: top mano, e voce ta criando aquelas automacao de whatsapp ?
- role: ANA
  content: tô sim kkk mexendo bastante com isso ultimamente 😄
produto:
  descricao_curta: 'Sistema que organiza o WhatsApp da empresa pra atender, mostrar
    produto, montar pedido, cobrar, recuperar quem desistiu e mostrar tudo num painel.

    '
  descricao_longa: 'O SAGA pega o WhatsApp da empresa e faz ele funcionar de um jeito
    onde o cliente entra, já vê o que tem disponível com foto e preço, escolhe o que
    quer, preenche o que precisa, faz o pedido, paga e recebe confirmação — tudo sem
    precisar de alguém do outro lado fazendo na mão. Se a pessoa para no meio, o sistema
    manda um áudio fazendo follow-up. Se ela avança, o sistema marca e classifica.
    Se ela fecha, registra tudo. E a empresa vê num painel o que vendeu, o que travou,
    quem parou onde, quanto dinheiro perdeu e onde vale a pena entrar na conversa.

    '
  funcoes:
  - nome: menu de entrada com botões
    beneficio: o cliente já sabe o que pode fazer sem precisar perguntar
  - nome: catálogo visual em carrossel com foto, preço e botão
    beneficio: o cliente vê o que tem, quanto custa e escolhe na hora — sem ninguém
      precisar mandar foto e preço um por um
  - nome: listas interativas com opções organizadas
    beneficio: organiza muitas opções de um jeito fácil de escolher sem poluir a conversa
  - nome: montagem automática do pedido
    beneficio: o pedido se monta sozinho conforme o cliente escolhe — sem ninguém
      anotando na mão
  - nome: resumo e confirmação do pedido antes de fechar
    beneficio: evita erro e retrabalho porque o cliente vê tudo que escolheu antes
      de confirmar
  - nome: geração de PIX e confirmação automática quando o pagamento cai
    beneficio: o pagamento acontece e confirma sem ninguém ficar perguntando "já pagou?"
  - nome: envio de foto, vídeo, áudio, documento, localização e contato
    beneficio: manda qualquer tipo de conteúdo que o atendimento precisar, tudo pelo
      sistema
  - nome: recuperação de quem desistiu por áudio de voz automático
    beneficio: quem parou no meio recebe um áudio puxando de volta — sem ninguém precisar
      lembrar ou ligar
  - nome: acompanhamento de em qual etapa cada pessoa parou
    beneficio: a empresa sabe exatamente onde as pessoas estão desistindo e pode agir
      em cima disso
  - nome: qualificação do lead com pontuação e classificação automática
    beneficio: separa quem está pronto pra comprar de quem ainda está só olhando —
      sem ninguém analisando conversa por conversa
  - nome: recomendação do produto ou serviço certo pro perfil do cliente
    beneficio: aumenta a chance de venda porque sugere o que faz sentido pra aquela
      pessoa, não qualquer coisa
  - nome: agendamento e reserva direto pelo WhatsApp
    beneficio: o cliente marca horário ou reserva sem precisar ligar, mandar email
      ou esperar resposta
  - nome: direcionamento pra atendente humano quando o automático não resolve
    beneficio: o cliente não fica preso no automático quando precisa de uma pessoa
      de verdade
  - nome: disparo de mensagem pra vários clientes de uma vez com filtro
    beneficio: manda mensagem só pra quem faz sentido — quem sumiu, quem nunca comprou,
      quem já voltou — sem mandar pra todo mundo igual
  - nome: nutrição automática de conteúdo ao longo do tempo
    beneficio: mantém o contato com o lead sem ninguém precisar lembrar de mandar
      mensagem
  - nome: painel com números em tempo real
    beneficio: a empresa vê na hora quantos pedidos tem, quanto faturou, quantos abandonaram
      e quantos clientes novos chegaram
  - nome: funil de conversão
    beneficio: mostra em qual etapa as pessoas estão parando — fica claro onde a empresa
      está perdendo gente
  - nome: quadro kanban com leads
    beneficio: cada pessoa vira um card que a empresa arrasta conforme avança — dá
      pra ver todo mundo de uma vez e saber quem precisa de atenção
  - nome: jornada do cliente
    beneficio: mostra tudo que a pessoa fez do começo ao fim — o que clicou, o que
      mandou, onde parou — sem precisar perguntar nada
  - nome: abandonos por etapa com lista de telefones
    beneficio: além de saber onde as pessoas param, já mostra os telefones pra empresa
      poder ir atrás e tentar recuperar
  - nome: disparos em massa com filtro inteligente
    beneficio: a empresa consegue falar com o grupo certo na hora certa — quem sumiu
      há 30 dias, quem comprou 2 vezes, quem nunca fechou
  - nome: ranking de produtos ou serviços
    beneficio: mostra o que vende mais e o que não sai — ajuda a decidir no que apostar
      e o que mudar
  - nome: análise de pagamentos
    beneficio: mostra quanto entrou por cada forma de pagamento e se tem alguma que
      trava mais que outra
  - nome: evolução de faturamento
    beneficio: mostra se o dinheiro está subindo, caindo ou parado — por dia, semana
      e mês
  - nome: horários de pico
    beneficio: mostra em que hora e dia da semana a empresa mais vende — ajuda a saber
      quando botar mais gente ou mais esforço
  - nome: curva ABC
    beneficio: separa o que dá dinheiro de verdade do que só ocupa espaço — os 20%
      que fazem 80% do faturamento ficam claros
  - nome: análise de venda adicional
    beneficio: mostra quando o cliente compra algo a mais junto e qual combinação
      mais acontece — ajuda a montar ofertas melhores
  - nome: clientes novos vs quem já voltou
    beneficio: mostra se a empresa está vivendo só de gente nova ou se o pessoal está
      voltando — e quanto cada cliente vale ao longo do tempo
  - nome: dinheiro perdido por abandono
    beneficio: calcula em reais quanto a empresa deixou de ganhar por causa de gente
      que desistiu em cada etapa — torna o prejuízo visível
  - nome: comparativo de período
    beneficio: compara essa semana com a passada, esse mês com o anterior — mostra
      se está melhorando ou piorando
  - nome: análise por região
    beneficio: mostra de onde vêm mais pedidos e onde o ticket é maior — ajuda a saber
      onde concentrar esforço
  - nome: retenção de clientes
    beneficio: mostra quantos clientes continuaram comprando ao longo do tempo — dá
      pra ver se o pessoal volta ou some depois da primeira compra
  - nome: evolução diária de conversões
    beneficio: mostra dia a dia quantos entraram, quantos avançaram e quantos compraram
      — dá pra ver tendência
  - nome: sazonalidade
    beneficio: mostra se existe um padrão que se repete — quais dias vendem mais,
      quais vendem menos
  - nome: clientes em risco
    beneficio: lista quem não compra há muito tempo antes de perder de vez — dá tempo
      de agir
  - nome: análise de margem
    beneficio: mostra quanto sobra de verdade depois de tirar o custo — e quanto precisa
      vender por dia pra fechar a conta
  - nome: pareto de clientes
    beneficio: mostra que poucos clientes fazem a maior parte do faturamento — ajuda
      a saber quem tratar como ouro
  - nome: integração com outros sistemas da empresa
    beneficio: se a empresa já usa outro sistema (ERP, loja virtual, planilha, agenda
      etc.), o SAGA pode se conectar e trocar informações — sem precisar ficar copiando
      dado de um lugar pro outro
  - nome: pixel de conversão
    beneficio: marca cada venda que acontece pelo WhatsApp e avisa as plataformas
      de anúncio (Meta, Google etc.) que aquela venda veio de lá — a empresa sabe
      qual anúncio está trazendo resultado de verdade e onde vale colocar mais dinheiro
  - nome: conversões personalizadas no pixel
    beneficio: a empresa escolhe o que quer rastrear como conversão — pode ser por
      produto vendido, por categoria, por valor, por etapa alcançada, por tipo de
      cliente ou qualquer combinação que fizer sentido pro negócio dela. Isso permite
      que os anúncios sejam otimizados não só pra "vendeu ou não vendeu", mas pra
      exatamente o tipo de venda que a empresa mais quer
  - nome: rastreamento de eventos no pixel
    beneficio: além da venda final, marca cada passo que o cliente deu — viu o catálogo,
      escolheu produto, iniciou pedido, chegou no pagamento — e manda tudo pro Meta
      e Google. Assim os anúncios ficam mais inteligentes porque a plataforma aprende
      o perfil de quem avança, não só de quem compra

```

### Output Used

```json
{
  "texto": "quando o cliente manda mensagem num horário corrido e a equipe já tá atendendo um monte de conversa ao mesmo tempo, normalmente começa aquele vai e volta básico: perguntar o que a pessoa quer, mandar foto, passar preço, explicar opção, anotar pedido, confirmar dado, cobrar, checar pagamento. no começo parece só rotina. mas no meio disso sempre entra outra conversa, alguém responde fora de ordem, um cliente visualiza e some, outro fica esperando retorno, e quem tá atendendo começa a decidir tudo no improviso pra dar conta.\n\nnesse ponto, o whatsapp deixa de ser só canal de atendimento e vira um lugar onde muita coisa depende de memória, atenção e velocidade. se responder rápido demais, passa coisa errada. se demora, a pessoa esfria. se para pra organizar, acumula conversa. e no fim do dia fica aquela sensação de que teve gente interessada, teve pedido quase fechado, teve pagamento pra confirmar, teve cliente que desistiu no meio — mas ninguém consegue ver direito onde travou, quem ficou pra trás e quanto disso virou dinheiro perdido sem fazer barulho.\n\né esse tipo de operação que começa a pesar quando a empresa vende, atende e cobra pelo whatsapp, mas já não consegue mais sustentar tudo no braço."
}
```

### Raw Response

```text
texto: "quando o cliente manda mensagem num horário corrido e a equipe já tá atendendo um monte de conversa ao mesmo tempo, normalmente começa aquele vai e volta básico: perguntar o que a pessoa quer, mandar foto, passar preço, explicar opção, anotar pedido, confirmar dado, cobrar, checar pagamento. no começo parece só rotina. mas no meio disso sempre entra outra conversa, alguém responde fora de ordem, um cliente visualiza e some, outro fica esperando retorno, e quem tá atendendo começa a decidir tudo no improviso pra dar conta.\n\nnesse ponto, o whatsapp deixa de ser só canal de atendimento e vira um lugar onde muita coisa depende de memória, atenção e velocidade. se responder rápido demais, passa coisa errada. se demora, a pessoa esfria. se para pra organizar, acumula conversa. e no fim do dia fica aquela sensação de que teve gente interessada, teve pedido quase fechado, teve pagamento pra confirmar, teve cliente que desistiu no meio — mas ninguém consegue ver direito onde travou, quem ficou pra trás e quanto disso virou dinheiro perdido sem fazer barulho.\n\né esse tipo de operação que começa a pesar quando a empresa vende, atende e cobra pelo whatsapp, mas já não consegue mais sustentar tudo no braço."
```

### Parsed Output

```json
{
  "texto": "quando o cliente manda mensagem num horário corrido e a equipe já tá atendendo um monte de conversa ao mesmo tempo, normalmente começa aquele vai e volta básico: perguntar o que a pessoa quer, mandar foto, passar preço, explicar opção, anotar pedido, confirmar dado, cobrar, checar pagamento. no começo parece só rotina. mas no meio disso sempre entra outra conversa, alguém responde fora de ordem, um cliente visualiza e some, outro fica esperando retorno, e quem tá atendendo começa a decidir tudo no improviso pra dar conta.\n\nnesse ponto, o whatsapp deixa de ser só canal de atendimento e vira um lugar onde muita coisa depende de memória, atenção e velocidade. se responder rápido demais, passa coisa errada. se demora, a pessoa esfria. se para pra organizar, acumula conversa. e no fim do dia fica aquela sensação de que teve gente interessada, teve pedido quase fechado, teve pagamento pra confirmar, teve cliente que desistiu no meio — mas ninguém consegue ver direito onde travou, quem ficou pra trás e quanto disso virou dinheiro perdido sem fazer barulho.\n\né esse tipo de operação que começa a pesar quando a empresa vende, atende e cobra pelo whatsapp, mas já não consegue mais sustentar tudo no braço."
}
```

### Instructions

```text
Você não está escrevendo a resposta final para o cliente.

Seu trabalho é construir apenas o contexto de uso que vai dar base para a etapa final de explicação.

voce deve criar um bom contexto de uso, porem um bom contexto de uso de vendas não é contar uma história bonita. É fazer a pessoa se enxergar numa situação, sentir o peso daquilo, perceber onde a oferta passa a fazer sentido e visualizar o que muda quando ela entra.
Se o input trouxer `descricao_longa` e `funcoes`, use isso como apoio silencioso de leitura: `descricao_longa` ajuda a perceber em que dinâmica, situação ou processo a oferta atua; `funcoes` ajudam a perceber onde essa oferta toca algo concreto da realidade.




Um bom contexto de uso não explica nada.
Ele coloca a pessoa dentro de um momento real da própria vida.
contexto de uso é estrutura de vivência.
Você não fala sobre solução.Você mostra o momento em que algo começa a fazer falta.

💡 Como pensar um bom contexto de uso
É quando a pessoa lê e pensa:
* “isso já aconteceu comigo”
* “eu faço exatamente assim”
* “é nesse ponto que tudo se perde”
Não é sobre o que algo faz.É sobre quando a realidade começa a falhar.
🔥 O que um contexto de uso precisa ter
1. Situação específica (tempo + ação)
Tem que ser um recorte real.
❌ “quando algo acontece…”✅ “quando você tá no meio de uma coisa e alguém te chama pra resolver outra”

2. Estado mental da pessoa
O que está passando na cabeça dela naquele momento?
* pressa
* distração
* dúvida
* sobrecarga
* tentativa de resolver rápido

3. Fricção invisível
Algo pequeno que quebra o fluxo.
* interrupção
* falta de clareza
* excesso de coisas acontecendo
* dependência de memória
* decisão adiada

4. Ponto de trava (micro-decisão)
O momento onde tudo poderia avançar… mas não avança.
“faço isso agora ou depois?”“resolvo direito ou só respondo rápido?”“deixo pra lá por enquanto?”

5. Consequência silenciosa
O que acontece depois… sem alarde.
* algo que não foi concluído
* algo que se perdeu no meio
* algo que vai precisar ser refeito
* sensação de desorganização
* acúmulo invisível

⚡ Estrutura prática
Você pode montar assim:
Momento“quando…”
Situação“você tá…”
Fricção“e aí…”
Trava“nesse ponto…”
Consequência“e no fim…”


🧠 Por que isso engaja
Porque ativa reconhecimento imediato:
* memória real
* sensação de familiaridade
* percepção de padrão repetido
A pessoa não precisa entender.Ela já viveu aquilo.

⚠️ Erros comuns
❌ Ser genérico demais❌ Não ter momento específico❌ Não ter fricção real❌ Não mostrar consequência❌ Parecer exemplo inventado

🧩 Resumo simples
Um bom contexto de uso:
pega um momento comum da vida, mostra onde existe uma quebra que normalmente passa despercebida e faz a pessoa perceber aquilo com mais clareza do que ela mesma percebia.


Retorne somente YAML válido, sem markdown e sem texto extra.

Não termine com convite.
Não ofereça próximos passos.
Não proponha opções.
Não feche falando com o cliente.

Formato:

texto: ""
```


---

## Turn 4

- helper: contexto_uso
- layer: v2.contexto_uso
- prompt_path: /Users/user/Desenvolvimento/ana_saga_cli/ana_v2/auxiliares/contexto_uso/contexto_uso.md
- duration_ms: 11142.27
- error: -

### Client Message

oloco, massa heim, e como é que ele funciona ?

### Input

```text
mensagem_atual_do_cliente: oloco, massa heim, e como é que ele funciona ?
historico_recente:
- role: cliente
  content: e ai meu brother, como vai ?
- role: ANA
  content: E aí meu brother, tudo certo por aqui 😄 e contigo?
- role: cliente
  content: maravilha, tu ta programando agora ? kkk
- role: ANA
  content: kkkk pior que sim 😅 mexendo nuns negócios aqui agora mesmo.
- role: cliente
  content: top mano, e voce ta criando aquelas automacao de whatsapp ?
- role: ANA
  content: tô sim kkk mexendo bastante com isso ultimamente 😄
produto:
  descricao_curta: 'Sistema que organiza o WhatsApp da empresa pra atender, mostrar
    produto, montar pedido, cobrar, recuperar quem desistiu e mostrar tudo num painel.

    '
  descricao_longa: 'O SAGA pega o WhatsApp da empresa e faz ele funcionar de um jeito
    onde o cliente entra, já vê o que tem disponível com foto e preço, escolhe o que
    quer, preenche o que precisa, faz o pedido, paga e recebe confirmação — tudo sem
    precisar de alguém do outro lado fazendo na mão. Se a pessoa para no meio, o sistema
    manda um áudio fazendo follow-up. Se ela avança, o sistema marca e classifica.
    Se ela fecha, registra tudo. E a empresa vê num painel o que vendeu, o que travou,
    quem parou onde, quanto dinheiro perdeu e onde vale a pena entrar na conversa.

    '
  funcoes:
  - nome: menu de entrada com botões
    beneficio: o cliente já sabe o que pode fazer sem precisar perguntar
  - nome: catálogo visual em carrossel com foto, preço e botão
    beneficio: o cliente vê o que tem, quanto custa e escolhe na hora — sem ninguém
      precisar mandar foto e preço um por um
  - nome: listas interativas com opções organizadas
    beneficio: organiza muitas opções de um jeito fácil de escolher sem poluir a conversa
  - nome: montagem automática do pedido
    beneficio: o pedido se monta sozinho conforme o cliente escolhe — sem ninguém
      anotando na mão
  - nome: resumo e confirmação do pedido antes de fechar
    beneficio: evita erro e retrabalho porque o cliente vê tudo que escolheu antes
      de confirmar
  - nome: geração de PIX e confirmação automática quando o pagamento cai
    beneficio: o pagamento acontece e confirma sem ninguém ficar perguntando "já pagou?"
  - nome: envio de foto, vídeo, áudio, documento, localização e contato
    beneficio: manda qualquer tipo de conteúdo que o atendimento precisar, tudo pelo
      sistema
  - nome: recuperação de quem desistiu por áudio de voz automático
    beneficio: quem parou no meio recebe um áudio puxando de volta — sem ninguém precisar
      lembrar ou ligar
  - nome: acompanhamento de em qual etapa cada pessoa parou
    beneficio: a empresa sabe exatamente onde as pessoas estão desistindo e pode agir
      em cima disso
  - nome: qualificação do lead com pontuação e classificação automática
    beneficio: separa quem está pronto pra comprar de quem ainda está só olhando —
      sem ninguém analisando conversa por conversa
  - nome: recomendação do produto ou serviço certo pro perfil do cliente
    beneficio: aumenta a chance de venda porque sugere o que faz sentido pra aquela
      pessoa, não qualquer coisa
  - nome: agendamento e reserva direto pelo WhatsApp
    beneficio: o cliente marca horário ou reserva sem precisar ligar, mandar email
      ou esperar resposta
  - nome: direcionamento pra atendente humano quando o automático não resolve
    beneficio: o cliente não fica preso no automático quando precisa de uma pessoa
      de verdade
  - nome: disparo de mensagem pra vários clientes de uma vez com filtro
    beneficio: manda mensagem só pra quem faz sentido — quem sumiu, quem nunca comprou,
      quem já voltou — sem mandar pra todo mundo igual
  - nome: nutrição automática de conteúdo ao longo do tempo
    beneficio: mantém o contato com o lead sem ninguém precisar lembrar de mandar
      mensagem
  - nome: painel com números em tempo real
    beneficio: a empresa vê na hora quantos pedidos tem, quanto faturou, quantos abandonaram
      e quantos clientes novos chegaram
  - nome: funil de conversão
    beneficio: mostra em qual etapa as pessoas estão parando — fica claro onde a empresa
      está perdendo gente
  - nome: quadro kanban com leads
    beneficio: cada pessoa vira um card que a empresa arrasta conforme avança — dá
      pra ver todo mundo de uma vez e saber quem precisa de atenção
  - nome: jornada do cliente
    beneficio: mostra tudo que a pessoa fez do começo ao fim — o que clicou, o que
      mandou, onde parou — sem precisar perguntar nada
  - nome: abandonos por etapa com lista de telefones
    beneficio: além de saber onde as pessoas param, já mostra os telefones pra empresa
      poder ir atrás e tentar recuperar
  - nome: disparos em massa com filtro inteligente
    beneficio: a empresa consegue falar com o grupo certo na hora certa — quem sumiu
      há 30 dias, quem comprou 2 vezes, quem nunca fechou
  - nome: ranking de produtos ou serviços
    beneficio: mostra o que vende mais e o que não sai — ajuda a decidir no que apostar
      e o que mudar
  - nome: análise de pagamentos
    beneficio: mostra quanto entrou por cada forma de pagamento e se tem alguma que
      trava mais que outra
  - nome: evolução de faturamento
    beneficio: mostra se o dinheiro está subindo, caindo ou parado — por dia, semana
      e mês
  - nome: horários de pico
    beneficio: mostra em que hora e dia da semana a empresa mais vende — ajuda a saber
      quando botar mais gente ou mais esforço
  - nome: curva ABC
    beneficio: separa o que dá dinheiro de verdade do que só ocupa espaço — os 20%
      que fazem 80% do faturamento ficam claros
  - nome: análise de venda adicional
    beneficio: mostra quando o cliente compra algo a mais junto e qual combinação
      mais acontece — ajuda a montar ofertas melhores
  - nome: clientes novos vs quem já voltou
    beneficio: mostra se a empresa está vivendo só de gente nova ou se o pessoal está
      voltando — e quanto cada cliente vale ao longo do tempo
  - nome: dinheiro perdido por abandono
    beneficio: calcula em reais quanto a empresa deixou de ganhar por causa de gente
      que desistiu em cada etapa — torna o prejuízo visível
  - nome: comparativo de período
    beneficio: compara essa semana com a passada, esse mês com o anterior — mostra
      se está melhorando ou piorando
  - nome: análise por região
    beneficio: mostra de onde vêm mais pedidos e onde o ticket é maior — ajuda a saber
      onde concentrar esforço
  - nome: retenção de clientes
    beneficio: mostra quantos clientes continuaram comprando ao longo do tempo — dá
      pra ver se o pessoal volta ou some depois da primeira compra
  - nome: evolução diária de conversões
    beneficio: mostra dia a dia quantos entraram, quantos avançaram e quantos compraram
      — dá pra ver tendência
  - nome: sazonalidade
    beneficio: mostra se existe um padrão que se repete — quais dias vendem mais,
      quais vendem menos
  - nome: clientes em risco
    beneficio: lista quem não compra há muito tempo antes de perder de vez — dá tempo
      de agir
  - nome: análise de margem
    beneficio: mostra quanto sobra de verdade depois de tirar o custo — e quanto precisa
      vender por dia pra fechar a conta
  - nome: pareto de clientes
    beneficio: mostra que poucos clientes fazem a maior parte do faturamento — ajuda
      a saber quem tratar como ouro
  - nome: integração com outros sistemas da empresa
    beneficio: se a empresa já usa outro sistema (ERP, loja virtual, planilha, agenda
      etc.), o SAGA pode se conectar e trocar informações — sem precisar ficar copiando
      dado de um lugar pro outro
  - nome: pixel de conversão
    beneficio: marca cada venda que acontece pelo WhatsApp e avisa as plataformas
      de anúncio (Meta, Google etc.) que aquela venda veio de lá — a empresa sabe
      qual anúncio está trazendo resultado de verdade e onde vale colocar mais dinheiro
  - nome: conversões personalizadas no pixel
    beneficio: a empresa escolhe o que quer rastrear como conversão — pode ser por
      produto vendido, por categoria, por valor, por etapa alcançada, por tipo de
      cliente ou qualquer combinação que fizer sentido pro negócio dela. Isso permite
      que os anúncios sejam otimizados não só pra "vendeu ou não vendeu", mas pra
      exatamente o tipo de venda que a empresa mais quer
  - nome: rastreamento de eventos no pixel
    beneficio: além da venda final, marca cada passo que o cliente deu — viu o catálogo,
      escolheu produto, iniciou pedido, chegou no pagamento — e manda tudo pro Meta
      e Google. Assim os anúncios ficam mais inteligentes porque a plataforma aprende
      o perfil de quem avança, não só de quem compra

```

### Output Used

```json
{
  "texto": "quando entra mensagem no WhatsApp bem na hora que a equipe tá fazendo outra coisa, normalmente vira aquela mistura: um cliente pedindo preço, outro querendo ver foto, outro perguntando se tem disponível, alguém tentando fechar, outro sumindo no meio.\nvocê responde um, para pra procurar imagem, volta, manda valor, espera, anota pedido por cima, confere se entendeu certo, pergunta de novo o que a pessoa escolheu, manda chave pix, depois precisa checar se pagou. nisso já entrou mais conversa, a tela desce, alguém fica sem resposta e você começa a atender no impulso, só pra não deixar parado.\né nesse ponto que o WhatsApp começa a pesar. não porque falta movimento, mas porque cada venda depende de lembrar o que cada pessoa viu, em que etapa parou, quem tava só olhando, quem já tava pronto pra pagar e quem desistiu no meio sem ninguém perceber.\ne no fim do dia fica aquela sensação de que teve conversa demais pra pouca clareza. entrou gente, teve interesse, teve pedido quase fechado, teve pagamento pra conferir, teve cliente que sumiu… mas boa parte do que travou não fez barulho. só foi ficando pelo caminho."
}
```

### Raw Response

```text
texto: "quando entra mensagem no WhatsApp bem na hora que a equipe tá fazendo outra coisa, normalmente vira aquela mistura: um cliente pedindo preço, outro querendo ver foto, outro perguntando se tem disponível, alguém tentando fechar, outro sumindo no meio.

você responde um, para pra procurar imagem, volta, manda valor, espera, anota pedido por cima, confere se entendeu certo, pergunta de novo o que a pessoa escolheu, manda chave pix, depois precisa checar se pagou. nisso já entrou mais conversa, a tela desce, alguém fica sem resposta e você começa a atender no impulso, só pra não deixar parado.

é nesse ponto que o WhatsApp começa a pesar. não porque falta movimento, mas porque cada venda depende de lembrar o que cada pessoa viu, em que etapa parou, quem tava só olhando, quem já tava pronto pra pagar e quem desistiu no meio sem ninguém perceber.

e no fim do dia fica aquela sensação de que teve conversa demais pra pouca clareza. entrou gente, teve interesse, teve pedido quase fechado, teve pagamento pra conferir, teve cliente que sumiu… mas boa parte do que travou não fez barulho. só foi ficando pelo caminho."
```

### Parsed Output

```json
{
  "texto": "quando entra mensagem no WhatsApp bem na hora que a equipe tá fazendo outra coisa, normalmente vira aquela mistura: um cliente pedindo preço, outro querendo ver foto, outro perguntando se tem disponível, alguém tentando fechar, outro sumindo no meio.\nvocê responde um, para pra procurar imagem, volta, manda valor, espera, anota pedido por cima, confere se entendeu certo, pergunta de novo o que a pessoa escolheu, manda chave pix, depois precisa checar se pagou. nisso já entrou mais conversa, a tela desce, alguém fica sem resposta e você começa a atender no impulso, só pra não deixar parado.\né nesse ponto que o WhatsApp começa a pesar. não porque falta movimento, mas porque cada venda depende de lembrar o que cada pessoa viu, em que etapa parou, quem tava só olhando, quem já tava pronto pra pagar e quem desistiu no meio sem ninguém perceber.\ne no fim do dia fica aquela sensação de que teve conversa demais pra pouca clareza. entrou gente, teve interesse, teve pedido quase fechado, teve pagamento pra conferir, teve cliente que sumiu… mas boa parte do que travou não fez barulho. só foi ficando pelo caminho."
}
```

### Instructions

```text
Você não está escrevendo a resposta final para o cliente.

Seu trabalho é construir apenas o contexto de uso que vai dar base para a etapa final de explicação.

voce deve criar um bom contexto de uso, porem um bom contexto de uso de vendas não é contar uma história bonita. É fazer a pessoa se enxergar numa situação, sentir o peso daquilo, perceber onde a oferta passa a fazer sentido e visualizar o que muda quando ela entra.
Se o input trouxer `descricao_longa` e `funcoes`, use isso como apoio silencioso de leitura: `descricao_longa` ajuda a perceber em que dinâmica, situação ou processo a oferta atua; `funcoes` ajudam a perceber onde essa oferta toca algo concreto da realidade.




Um bom contexto de uso não explica nada.
Ele coloca a pessoa dentro de um momento real da própria vida.
contexto de uso é estrutura de vivência.
Você não fala sobre solução.Você mostra o momento em que algo começa a fazer falta.

💡 Como pensar um bom contexto de uso
É quando a pessoa lê e pensa:
* “isso já aconteceu comigo”
* “eu faço exatamente assim”
* “é nesse ponto que tudo se perde”
Não é sobre o que algo faz.É sobre quando a realidade começa a falhar.
🔥 O que um contexto de uso precisa ter
1. Situação específica (tempo + ação)
Tem que ser um recorte real.
❌ “quando algo acontece…”✅ “quando você tá no meio de uma coisa e alguém te chama pra resolver outra”

2. Estado mental da pessoa
O que está passando na cabeça dela naquele momento?
* pressa
* distração
* dúvida
* sobrecarga
* tentativa de resolver rápido

3. Fricção invisível
Algo pequeno que quebra o fluxo.
* interrupção
* falta de clareza
* excesso de coisas acontecendo
* dependência de memória
* decisão adiada

4. Ponto de trava (micro-decisão)
O momento onde tudo poderia avançar… mas não avança.
“faço isso agora ou depois?”“resolvo direito ou só respondo rápido?”“deixo pra lá por enquanto?”

5. Consequência silenciosa
O que acontece depois… sem alarde.
* algo que não foi concluído
* algo que se perdeu no meio
* algo que vai precisar ser refeito
* sensação de desorganização
* acúmulo invisível

⚡ Estrutura prática
Você pode montar assim:
Momento“quando…”
Situação“você tá…”
Fricção“e aí…”
Trava“nesse ponto…”
Consequência“e no fim…”


🧠 Por que isso engaja
Porque ativa reconhecimento imediato:
* memória real
* sensação de familiaridade
* percepção de padrão repetido
A pessoa não precisa entender.Ela já viveu aquilo.

⚠️ Erros comuns
❌ Ser genérico demais❌ Não ter momento específico❌ Não ter fricção real❌ Não mostrar consequência❌ Parecer exemplo inventado

🧩 Resumo simples
Um bom contexto de uso:
pega um momento comum da vida, mostra onde existe uma quebra que normalmente passa despercebida e faz a pessoa perceber aquilo com mais clareza do que ela mesma percebia.


Retorne somente YAML válido, sem markdown e sem texto extra.

Não termine com convite.
Não ofereça próximos passos.
Não proponha opções.
Não feche falando com o cliente.

Formato:

texto: ""
```


---

## Turn 4

- helper: contexto_uso
- layer: v2.contexto_uso
- prompt_path: /Users/user/Desenvolvimento/ana_saga_cli/ana_v2/auxiliares/contexto_uso/contexto_uso.md
- duration_ms: 7443.618
- error: -

### Client Message

oloco, massa heim, e como é que ele funciona ?

### Input

```text
mensagem_atual_do_cliente: oloco, massa heim, e como é que ele funciona ?
historico_recente:
- role: cliente
  content: e ai meu brother, como vai ?
- role: ANA
  content: E aí meu brother, tudo certo por aqui 😄 e contigo?
- role: cliente
  content: maravilha, tu ta programando agora ? kkk
- role: ANA
  content: kkkk pior que sim 😅 mexendo nuns negócios aqui agora mesmo.
- role: cliente
  content: top mano, e voce ta criando aquelas automacao de whatsapp ?
- role: ANA
  content: tô sim kkk mexendo bastante com isso ultimamente 😄
produto:
  descricao_curta: 'Sistema que organiza o WhatsApp da empresa pra atender, mostrar
    produto, montar pedido, cobrar, recuperar quem desistiu e mostrar tudo num painel.

    '
  descricao_longa: 'O SAGA pega o WhatsApp da empresa e faz ele funcionar de um jeito
    onde o cliente entra, já vê o que tem disponível com foto e preço, escolhe o que
    quer, preenche o que precisa, faz o pedido, paga e recebe confirmação — tudo sem
    precisar de alguém do outro lado fazendo na mão. Se a pessoa para no meio, o sistema
    manda um áudio fazendo follow-up. Se ela avança, o sistema marca e classifica.
    Se ela fecha, registra tudo. E a empresa vê num painel o que vendeu, o que travou,
    quem parou onde, quanto dinheiro perdeu e onde vale a pena entrar na conversa.

    '
  funcoes:
  - nome: menu de entrada com botões
    beneficio: o cliente já sabe o que pode fazer sem precisar perguntar
  - nome: catálogo visual em carrossel com foto, preço e botão
    beneficio: o cliente vê o que tem, quanto custa e escolhe na hora — sem ninguém
      precisar mandar foto e preço um por um
  - nome: listas interativas com opções organizadas
    beneficio: organiza muitas opções de um jeito fácil de escolher sem poluir a conversa
  - nome: montagem automática do pedido
    beneficio: o pedido se monta sozinho conforme o cliente escolhe — sem ninguém
      anotando na mão
  - nome: resumo e confirmação do pedido antes de fechar
    beneficio: evita erro e retrabalho porque o cliente vê tudo que escolheu antes
      de confirmar
  - nome: geração de PIX e confirmação automática quando o pagamento cai
    beneficio: o pagamento acontece e confirma sem ninguém ficar perguntando "já pagou?"
  - nome: envio de foto, vídeo, áudio, documento, localização e contato
    beneficio: manda qualquer tipo de conteúdo que o atendimento precisar, tudo pelo
      sistema
  - nome: recuperação de quem desistiu por áudio de voz automático
    beneficio: quem parou no meio recebe um áudio puxando de volta — sem ninguém precisar
      lembrar ou ligar
  - nome: acompanhamento de em qual etapa cada pessoa parou
    beneficio: a empresa sabe exatamente onde as pessoas estão desistindo e pode agir
      em cima disso
  - nome: qualificação do lead com pontuação e classificação automática
    beneficio: separa quem está pronto pra comprar de quem ainda está só olhando —
      sem ninguém analisando conversa por conversa
  - nome: recomendação do produto ou serviço certo pro perfil do cliente
    beneficio: aumenta a chance de venda porque sugere o que faz sentido pra aquela
      pessoa, não qualquer coisa
  - nome: agendamento e reserva direto pelo WhatsApp
    beneficio: o cliente marca horário ou reserva sem precisar ligar, mandar email
      ou esperar resposta
  - nome: direcionamento pra atendente humano quando o automático não resolve
    beneficio: o cliente não fica preso no automático quando precisa de uma pessoa
      de verdade
  - nome: disparo de mensagem pra vários clientes de uma vez com filtro
    beneficio: manda mensagem só pra quem faz sentido — quem sumiu, quem nunca comprou,
      quem já voltou — sem mandar pra todo mundo igual
  - nome: nutrição automática de conteúdo ao longo do tempo
    beneficio: mantém o contato com o lead sem ninguém precisar lembrar de mandar
      mensagem
  - nome: painel com números em tempo real
    beneficio: a empresa vê na hora quantos pedidos tem, quanto faturou, quantos abandonaram
      e quantos clientes novos chegaram
  - nome: funil de conversão
    beneficio: mostra em qual etapa as pessoas estão parando — fica claro onde a empresa
      está perdendo gente
  - nome: quadro kanban com leads
    beneficio: cada pessoa vira um card que a empresa arrasta conforme avança — dá
      pra ver todo mundo de uma vez e saber quem precisa de atenção
  - nome: jornada do cliente
    beneficio: mostra tudo que a pessoa fez do começo ao fim — o que clicou, o que
      mandou, onde parou — sem precisar perguntar nada
  - nome: abandonos por etapa com lista de telefones
    beneficio: além de saber onde as pessoas param, já mostra os telefones pra empresa
      poder ir atrás e tentar recuperar
  - nome: disparos em massa com filtro inteligente
    beneficio: a empresa consegue falar com o grupo certo na hora certa — quem sumiu
      há 30 dias, quem comprou 2 vezes, quem nunca fechou
  - nome: ranking de produtos ou serviços
    beneficio: mostra o que vende mais e o que não sai — ajuda a decidir no que apostar
      e o que mudar
  - nome: análise de pagamentos
    beneficio: mostra quanto entrou por cada forma de pagamento e se tem alguma que
      trava mais que outra
  - nome: evolução de faturamento
    beneficio: mostra se o dinheiro está subindo, caindo ou parado — por dia, semana
      e mês
  - nome: horários de pico
    beneficio: mostra em que hora e dia da semana a empresa mais vende — ajuda a saber
      quando botar mais gente ou mais esforço
  - nome: curva ABC
    beneficio: separa o que dá dinheiro de verdade do que só ocupa espaço — os 20%
      que fazem 80% do faturamento ficam claros
  - nome: análise de venda adicional
    beneficio: mostra quando o cliente compra algo a mais junto e qual combinação
      mais acontece — ajuda a montar ofertas melhores
  - nome: clientes novos vs quem já voltou
    beneficio: mostra se a empresa está vivendo só de gente nova ou se o pessoal está
      voltando — e quanto cada cliente vale ao longo do tempo
  - nome: dinheiro perdido por abandono
    beneficio: calcula em reais quanto a empresa deixou de ganhar por causa de gente
      que desistiu em cada etapa — torna o prejuízo visível
  - nome: comparativo de período
    beneficio: compara essa semana com a passada, esse mês com o anterior — mostra
      se está melhorando ou piorando
  - nome: análise por região
    beneficio: mostra de onde vêm mais pedidos e onde o ticket é maior — ajuda a saber
      onde concentrar esforço
  - nome: retenção de clientes
    beneficio: mostra quantos clientes continuaram comprando ao longo do tempo — dá
      pra ver se o pessoal volta ou some depois da primeira compra
  - nome: evolução diária de conversões
    beneficio: mostra dia a dia quantos entraram, quantos avançaram e quantos compraram
      — dá pra ver tendência
  - nome: sazonalidade
    beneficio: mostra se existe um padrão que se repete — quais dias vendem mais,
      quais vendem menos
  - nome: clientes em risco
    beneficio: lista quem não compra há muito tempo antes de perder de vez — dá tempo
      de agir
  - nome: análise de margem
    beneficio: mostra quanto sobra de verdade depois de tirar o custo — e quanto precisa
      vender por dia pra fechar a conta
  - nome: pareto de clientes
    beneficio: mostra que poucos clientes fazem a maior parte do faturamento — ajuda
      a saber quem tratar como ouro
  - nome: integração com outros sistemas da empresa
    beneficio: se a empresa já usa outro sistema (ERP, loja virtual, planilha, agenda
      etc.), o SAGA pode se conectar e trocar informações — sem precisar ficar copiando
      dado de um lugar pro outro
  - nome: pixel de conversão
    beneficio: marca cada venda que acontece pelo WhatsApp e avisa as plataformas
      de anúncio (Meta, Google etc.) que aquela venda veio de lá — a empresa sabe
      qual anúncio está trazendo resultado de verdade e onde vale colocar mais dinheiro
  - nome: conversões personalizadas no pixel
    beneficio: a empresa escolhe o que quer rastrear como conversão — pode ser por
      produto vendido, por categoria, por valor, por etapa alcançada, por tipo de
      cliente ou qualquer combinação que fizer sentido pro negócio dela. Isso permite
      que os anúncios sejam otimizados não só pra "vendeu ou não vendeu", mas pra
      exatamente o tipo de venda que a empresa mais quer
  - nome: rastreamento de eventos no pixel
    beneficio: além da venda final, marca cada passo que o cliente deu — viu o catálogo,
      escolheu produto, iniciou pedido, chegou no pagamento — e manda tudo pro Meta
      e Google. Assim os anúncios ficam mais inteligentes porque a plataforma aprende
      o perfil de quem avança, não só de quem compra

```

### Output Used

```json
{
  "texto": "Quando a conversa começa a entrar no volume real do dia, é aí que o WhatsApp da empresa mostra onde trava.\nVocê tá atendendo uma pessoa que quer saber preço, outra pedindo foto, outra perguntando prazo, outra querendo fechar, e no meio disso alguém some bem na hora de pagar. Aí você responde o que dá, manda catálogo picado, procura informação em conversa antiga, tenta lembrar quem tava pronto pra comprar e quem só tava perguntando.\nNesse ponto, o problema não aparece como uma coisa grande. Ele aparece como detalhe: mensagem que ficou pra depois, pedido montado pela metade, cliente que até queria comprar mas cansou de esperar, pagamento que você ainda vai conferir, retorno que ninguém lembrou de fazer.\nE no fim, o WhatsApp vai ficando cheio, a operação parece ocupada o dia inteiro, mas uma parte das vendas vai escapando justamente nos momentos mais simples: quando a pessoa queria ver opção rápido, escolher sem depender de alguém, fechar sem espera, pagar sem confirmação manual e seguir sem sumir no meio da conversa.\nÉ nesse tipo de rotina que ele entra."
}
```

### Raw Response

```text
texto: "Quando a conversa começa a entrar no volume real do dia, é aí que o WhatsApp da empresa mostra onde trava.

Você tá atendendo uma pessoa que quer saber preço, outra pedindo foto, outra perguntando prazo, outra querendo fechar, e no meio disso alguém some bem na hora de pagar. Aí você responde o que dá, manda catálogo picado, procura informação em conversa antiga, tenta lembrar quem tava pronto pra comprar e quem só tava perguntando.

Nesse ponto, o problema não aparece como uma coisa grande. Ele aparece como detalhe: mensagem que ficou pra depois, pedido montado pela metade, cliente que até queria comprar mas cansou de esperar, pagamento que você ainda vai conferir, retorno que ninguém lembrou de fazer.

E no fim, o WhatsApp vai ficando cheio, a operação parece ocupada o dia inteiro, mas uma parte das vendas vai escapando justamente nos momentos mais simples: quando a pessoa queria ver opção rápido, escolher sem depender de alguém, fechar sem espera, pagar sem confirmação manual e seguir sem sumir no meio da conversa.

É nesse tipo de rotina que ele entra."
```

### Parsed Output

```json
{
  "texto": "Quando a conversa começa a entrar no volume real do dia, é aí que o WhatsApp da empresa mostra onde trava.\nVocê tá atendendo uma pessoa que quer saber preço, outra pedindo foto, outra perguntando prazo, outra querendo fechar, e no meio disso alguém some bem na hora de pagar. Aí você responde o que dá, manda catálogo picado, procura informação em conversa antiga, tenta lembrar quem tava pronto pra comprar e quem só tava perguntando.\nNesse ponto, o problema não aparece como uma coisa grande. Ele aparece como detalhe: mensagem que ficou pra depois, pedido montado pela metade, cliente que até queria comprar mas cansou de esperar, pagamento que você ainda vai conferir, retorno que ninguém lembrou de fazer.\nE no fim, o WhatsApp vai ficando cheio, a operação parece ocupada o dia inteiro, mas uma parte das vendas vai escapando justamente nos momentos mais simples: quando a pessoa queria ver opção rápido, escolher sem depender de alguém, fechar sem espera, pagar sem confirmação manual e seguir sem sumir no meio da conversa.\nÉ nesse tipo de rotina que ele entra."
}
```

### Instructions

```text
Você não está escrevendo a resposta final para o cliente.

Seu trabalho é construir apenas o contexto de uso que vai dar base para a etapa final de explicação.

voce deve criar um bom contexto de uso, porem um bom contexto de uso de vendas não é contar uma história bonita. É fazer a pessoa se enxergar numa situação, sentir o peso daquilo, perceber onde a oferta passa a fazer sentido e visualizar o que muda quando ela entra.
Se o input trouxer `descricao_longa` e `funcoes`, use isso como apoio silencioso de leitura: `descricao_longa` ajuda a perceber em que dinâmica, situação ou processo a oferta atua; `funcoes` ajudam a perceber onde essa oferta toca algo concreto da realidade.




Um bom contexto de uso não explica nada.
Ele coloca a pessoa dentro de um momento real da própria vida.
contexto de uso é estrutura de vivência.
Você não fala sobre solução.Você mostra o momento em que algo começa a fazer falta.

💡 Como pensar um bom contexto de uso
É quando a pessoa lê e pensa:
* “isso já aconteceu comigo”
* “eu faço exatamente assim”
* “é nesse ponto que tudo se perde”
Não é sobre o que algo faz.É sobre quando a realidade começa a falhar.
🔥 O que um contexto de uso precisa ter
1. Situação específica (tempo + ação)
Tem que ser um recorte real.
❌ “quando algo acontece…”✅ “quando você tá no meio de uma coisa e alguém te chama pra resolver outra”

2. Estado mental da pessoa
O que está passando na cabeça dela naquele momento?
* pressa
* distração
* dúvida
* sobrecarga
* tentativa de resolver rápido

3. Fricção invisível
Algo pequeno que quebra o fluxo.
* interrupção
* falta de clareza
* excesso de coisas acontecendo
* dependência de memória
* decisão adiada

4. Ponto de trava (micro-decisão)
O momento onde tudo poderia avançar… mas não avança.
“faço isso agora ou depois?”“resolvo direito ou só respondo rápido?”“deixo pra lá por enquanto?”

5. Consequência silenciosa
O que acontece depois… sem alarde.
* algo que não foi concluído
* algo que se perdeu no meio
* algo que vai precisar ser refeito
* sensação de desorganização
* acúmulo invisível

⚡ Estrutura prática
Você pode montar assim:
Momento“quando…”
Situação“você tá…”
Fricção“e aí…”
Trava“nesse ponto…”
Consequência“e no fim…”


🧠 Por que isso engaja
Porque ativa reconhecimento imediato:
* memória real
* sensação de familiaridade
* percepção de padrão repetido
A pessoa não precisa entender.Ela já viveu aquilo.

⚠️ Erros comuns
❌ Ser genérico demais❌ Não ter momento específico❌ Não ter fricção real❌ Não mostrar consequência❌ Parecer exemplo inventado

🧩 Resumo simples
Um bom contexto de uso:
pega um momento comum da vida, mostra onde existe uma quebra que normalmente passa despercebida e faz a pessoa perceber aquilo com mais clareza do que ela mesma percebia.


Retorne somente YAML válido, sem markdown e sem texto extra.

Não termine com convite.
Não ofereça próximos passos.
Não proponha opções.
Não feche falando com o cliente.

Formato:

texto: ""
```


---

