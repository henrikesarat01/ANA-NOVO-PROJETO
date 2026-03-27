# ANA Auxiliary Debug — storytelling

- created_at: 2026-03-26 23:28:25
- provider: openai
- model: gpt-5.4
- source_debug_file: ana_debug_20260326_232703.md

---
## Turn 4

- helper: storytelling
- layer: v2.storytelling
- prompt_path: /Users/user/Desenvolvimento/ana_saga_cli/ana_v2/auxiliares/storytelling/storytelling.md
- duration_ms: 9222.445
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
  "texto": "Muita gente quando ouve “automação de WhatsApp” imagina só um robozinho respondendo mensagem. Mas na prática o problema quase nunca é só responder rápido.\nO que normalmente acontece é isso: a pessoa chama, pergunta o que tem, pede preço, espera foto, faz mais uma pergunta, some, volta depois, pede de novo, escolhe uma coisa, muda de ideia, alguém anota errado, esquece de cobrar, não sabe em que etapa ela parou e no fim a empresa fica com a sensação de que conversou muito e vendeu menos do que podia.\nE o pior é que isso vira rotina. O atendimento parece ocupado o dia todo, mas muita energia vai embora em tarefa manual: mandar catálogo, explicar opção, montar pedido, confirmar pagamento, lembrar de cobrar quem sumiu, tentar descobrir onde perdeu venda.\nA virada começa quando o WhatsApp deixa de ser só uma conversa solta e passa a funcionar como um processo.\nEsse sistema faz isso. Quando a pessoa entra, ela já vê um menu com botões, entende o que pode fazer, acessa catálogo com foto e preço, escolhe a opção certa, monta o pedido dentro da conversa, recebe resumo antes de fechar, paga por PIX e o sistema confirma automaticamente. Se ela parar no meio, o sistema identifica onde travou e ainda pode puxar ela de volta com follow-up automático, até por áudio.\nEntão ele não serve só pra responder. Ele organiza a jornada inteira: atendimento, pedido, cobrança, recuperação e acompanhamento.\nE do lado da empresa fica tudo visível também. Dá pra ver quantas pessoas entraram, onde abandonaram, quanto dinheiro ficou perdido no caminho, quais produtos vendem mais, quem tá pronto pra comprar e quando faz sentido entrar com humano.\nA diferença real é essa: em vez de depender de alguém fazendo tudo na mão dentro do WhatsApp, a empresa passa a ter um fluxo que conduz o cliente até a compra e mostra claramente onde está ganhando ou perdendo dinheiro."
}
```

### Raw Response

```text
texto: "Muita gente quando ouve “automação de WhatsApp” imagina só um robozinho respondendo mensagem. Mas na prática o problema quase nunca é só responder rápido.

O que normalmente acontece é isso: a pessoa chama, pergunta o que tem, pede preço, espera foto, faz mais uma pergunta, some, volta depois, pede de novo, escolhe uma coisa, muda de ideia, alguém anota errado, esquece de cobrar, não sabe em que etapa ela parou e no fim a empresa fica com a sensação de que conversou muito e vendeu menos do que podia.

E o pior é que isso vira rotina. O atendimento parece ocupado o dia todo, mas muita energia vai embora em tarefa manual: mandar catálogo, explicar opção, montar pedido, confirmar pagamento, lembrar de cobrar quem sumiu, tentar descobrir onde perdeu venda.

A virada começa quando o WhatsApp deixa de ser só uma conversa solta e passa a funcionar como um processo.

Esse sistema faz isso. Quando a pessoa entra, ela já vê um menu com botões, entende o que pode fazer, acessa catálogo com foto e preço, escolhe a opção certa, monta o pedido dentro da conversa, recebe resumo antes de fechar, paga por PIX e o sistema confirma automaticamente. Se ela parar no meio, o sistema identifica onde travou e ainda pode puxar ela de volta com follow-up automático, até por áudio.

Então ele não serve só pra responder. Ele organiza a jornada inteira: atendimento, pedido, cobrança, recuperação e acompanhamento.

E do lado da empresa fica tudo visível também. Dá pra ver quantas pessoas entraram, onde abandonaram, quanto dinheiro ficou perdido no caminho, quais produtos vendem mais, quem tá pronto pra comprar e quando faz sentido entrar com humano.

A diferença real é essa: em vez de depender de alguém fazendo tudo na mão dentro do WhatsApp, a empresa passa a ter um fluxo que conduz o cliente até a compra e mostra claramente onde está ganhando ou perdendo dinheiro."
```

### Parsed Output

```json
{
  "texto": "Muita gente quando ouve “automação de WhatsApp” imagina só um robozinho respondendo mensagem. Mas na prática o problema quase nunca é só responder rápido.\nO que normalmente acontece é isso: a pessoa chama, pergunta o que tem, pede preço, espera foto, faz mais uma pergunta, some, volta depois, pede de novo, escolhe uma coisa, muda de ideia, alguém anota errado, esquece de cobrar, não sabe em que etapa ela parou e no fim a empresa fica com a sensação de que conversou muito e vendeu menos do que podia.\nE o pior é que isso vira rotina. O atendimento parece ocupado o dia todo, mas muita energia vai embora em tarefa manual: mandar catálogo, explicar opção, montar pedido, confirmar pagamento, lembrar de cobrar quem sumiu, tentar descobrir onde perdeu venda.\nA virada começa quando o WhatsApp deixa de ser só uma conversa solta e passa a funcionar como um processo.\nEsse sistema faz isso. Quando a pessoa entra, ela já vê um menu com botões, entende o que pode fazer, acessa catálogo com foto e preço, escolhe a opção certa, monta o pedido dentro da conversa, recebe resumo antes de fechar, paga por PIX e o sistema confirma automaticamente. Se ela parar no meio, o sistema identifica onde travou e ainda pode puxar ela de volta com follow-up automático, até por áudio.\nEntão ele não serve só pra responder. Ele organiza a jornada inteira: atendimento, pedido, cobrança, recuperação e acompanhamento.\nE do lado da empresa fica tudo visível também. Dá pra ver quantas pessoas entraram, onde abandonaram, quanto dinheiro ficou perdido no caminho, quais produtos vendem mais, quem tá pronto pra comprar e quando faz sentido entrar com humano.\nA diferença real é essa: em vez de depender de alguém fazendo tudo na mão dentro do WhatsApp, a empresa passa a ter um fluxo que conduz o cliente até a compra e mostra claramente onde está ganhando ou perdendo dinheiro."
}
```

### Instructions

```text
Você não está escrevendo a resposta final para o cliente.

Seu trabalho é construir apenas o eixo narrativo que vai dar base para a etapa final de explicação.

voce deve criar um bom storytelling, porem um bom storytelling de vendas não é contar uma história bonita.É fazer a pessoa se enxergar numa situação, sentir o peso daquilo, perceber uma mudança possível e concluir sozinha que a sua solução faz sentido.
Se o input trouxer `descricao_longa` e `funcoes`, use isso como apoio silencioso de leitura: `descricao_longa` ajuda a perceber em que dinâmica, situação ou processo a oferta atua; `funcoes` ajudam a perceber onde essa oferta toca algo concreto da realidade.
Em vendas, história boa não é enfeite.É estrutura de percepção.
Ela faz o cliente passar por 4 coisas:
1. Se reconhecerA história mostra um cenário que parece real o suficiente para o cliente pensar:“isso acontece comigo”“eu conheço esse tipo de situação”“é exatamente assim que eu me sinto”
2. Sentir a tensãoSem tensão, não existe atenção.Tem que existir algum atrito:
    * explorar suas dores em seus conceitos mais vicerais 
    * perda
    * dúvida
    * frustração
    * trava
    * medo
    * confusão
    * esforço desperdiçado
3. Ver uma virada possívelA história não pode só descrever o problema.Ela precisa mostrar que existe um jeito diferente de olhar, agir ou resolver.
4. Associar sua solução à mudançaA oferta não entra como propaganda empurrada.Ela entra como consequência natural da história.
Então, na prática, um bom storytelling de vendas costuma seguir essa lógica:
estado atual → conflito → impacto → descoberta → mudança → nova possibilidade
Isso é storytelling de vendas porque:
* começa numa crença comum
* cria curiosidade
* revela um erro de percepção
* reposiciona o problema
* abre espaço para a solução
O que faz uma história realmente engajar:
1. Verdade percebidaTem que parecer vida real, não texto publicitário.
2. EspecificidadeDetalhe concreto convence mais do que frase genérica.“o lead some” é fraco.“a pessoa pergunta preço, visualiza, fala que vai ver e nunca mais responde” é forte.
3. Tensão humanaNão basta dizer que há um problema.Tem que mostrar o que isso gera emocionalmente ou operacionalmente.
4. ProgressãoA história precisa andar.Se ela só gira em torno do mesmo ponto, cansa.
5. RecompensaNo final, a pessoa precisa ganhar alguma coisa:
* clareza
* identificação
* surpresa
* alívio
* nova forma de enxergar o problema
A forma mais simples de pensar storytelling para vendas é essa:
uma boa história de vendas pega um problema que o cliente sente de forma confusa, organiza esse problema de forma clara e entrega uma mudança que parece desejável e possível.
E o erro mais comum é achar que storytelling é:
* inventar drama
* romantizar
* florear demais
* fazer texto emocionante sem direção comercial
Não é isso.
Storytelling de vendas bom é quando o cliente sente que você entendeu a realiade dele melhor do que ele mesmo estava conseguindo explicar.
Uma fórmula prática que funciona muito bem é:
Cenário real“muita gente acha que…”
Sintoma visível“e aí acontece isso…”
Problema oculto“só que quase nunca o problema real é esse…”
Reenquadramento“na verdade…”
Virada“quando você entende isso…”
Nova possibilidade“é aí que começa a mudança”



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

- helper: storytelling
- layer: v2.storytelling
- prompt_path: /Users/user/Desenvolvimento/ana_saga_cli/ana_v2/auxiliares/storytelling/storytelling.md
- duration_ms: 8643.241
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
  "texto": "Funciona tipo pegando aquele caos normal do WhatsApp e transformando numa jornada organizada.\n\nHoje, em muita empresa, acontece assim: a pessoa chama, pergunta preço, pede foto, some, volta, pergunta de novo, o atendente demora, anota pedido na mão, confere pagamento manualmente… e no fim ninguém sabe direito onde perdeu venda.\n\nAí o problema parece ser só “falta de tempo pra responder”. Mas quase nunca é só isso.\n\nNa real, o que trava é que o WhatsApp fica solto demais. O cliente entra sem direção, o atendimento depende de alguém conduzir tudo no braço, e qualquer demora ou confusão no meio já vira desistência.\n\nO SAGA entra justamente aí.\n\nQuando a pessoa chama no WhatsApp, ela já cai num menu com botões, entende o que pode fazer, vê catálogo com foto e preço, escolhe as opções, monta o pedido, confirma, recebe o PIX e o sistema ainda confirma automático quando o pagamento cai.\n\nSe ela parar no meio, o sistema identifica em que etapa travou e pode puxar de volta com follow-up automático, até com áudio. Se o automático não resolver, aí sim direciona pra um atendente humano.\n\nOu seja: não é só responder mensagem. É organizar o processo inteiro de venda dentro do WhatsApp.\n\nE a parte que normalmente a galera acha mais interessante é essa: além de atender e vender, ele mostra num painel o que aconteceu de verdade — quantos entraram, onde desistiram, quanto dinheiro ficou perdido no abandono, o que mais vende, quais clientes estão quentes e onde vale a pena agir.\n\nEntão ele funciona como se fosse um vendedor + organizador + acompanhamento do negócio tudo dentro do WhatsApp."
}
```

### Raw Response

```text
texto: "Funciona tipo pegando aquele caos normal do WhatsApp e transformando numa jornada organizada.\n\nHoje, em muita empresa, acontece assim: a pessoa chama, pergunta preço, pede foto, some, volta, pergunta de novo, o atendente demora, anota pedido na mão, confere pagamento manualmente… e no fim ninguém sabe direito onde perdeu venda.\n\nAí o problema parece ser só “falta de tempo pra responder”. Mas quase nunca é só isso.\n\nNa real, o que trava é que o WhatsApp fica solto demais. O cliente entra sem direção, o atendimento depende de alguém conduzir tudo no braço, e qualquer demora ou confusão no meio já vira desistência.\n\nO SAGA entra justamente aí.\n\nQuando a pessoa chama no WhatsApp, ela já cai num menu com botões, entende o que pode fazer, vê catálogo com foto e preço, escolhe as opções, monta o pedido, confirma, recebe o PIX e o sistema ainda confirma automático quando o pagamento cai.\n\nSe ela parar no meio, o sistema identifica em que etapa travou e pode puxar de volta com follow-up automático, até com áudio. Se o automático não resolver, aí sim direciona pra um atendente humano.\n\nOu seja: não é só responder mensagem. É organizar o processo inteiro de venda dentro do WhatsApp.\n\nE a parte que normalmente a galera acha mais interessante é essa: além de atender e vender, ele mostra num painel o que aconteceu de verdade — quantos entraram, onde desistiram, quanto dinheiro ficou perdido no abandono, o que mais vende, quais clientes estão quentes e onde vale a pena agir.\n\nEntão ele funciona como se fosse um vendedor + organizador + acompanhamento do negócio tudo dentro do WhatsApp."
```

### Parsed Output

```json
{
  "texto": "Funciona tipo pegando aquele caos normal do WhatsApp e transformando numa jornada organizada.\n\nHoje, em muita empresa, acontece assim: a pessoa chama, pergunta preço, pede foto, some, volta, pergunta de novo, o atendente demora, anota pedido na mão, confere pagamento manualmente… e no fim ninguém sabe direito onde perdeu venda.\n\nAí o problema parece ser só “falta de tempo pra responder”. Mas quase nunca é só isso.\n\nNa real, o que trava é que o WhatsApp fica solto demais. O cliente entra sem direção, o atendimento depende de alguém conduzir tudo no braço, e qualquer demora ou confusão no meio já vira desistência.\n\nO SAGA entra justamente aí.\n\nQuando a pessoa chama no WhatsApp, ela já cai num menu com botões, entende o que pode fazer, vê catálogo com foto e preço, escolhe as opções, monta o pedido, confirma, recebe o PIX e o sistema ainda confirma automático quando o pagamento cai.\n\nSe ela parar no meio, o sistema identifica em que etapa travou e pode puxar de volta com follow-up automático, até com áudio. Se o automático não resolver, aí sim direciona pra um atendente humano.\n\nOu seja: não é só responder mensagem. É organizar o processo inteiro de venda dentro do WhatsApp.\n\nE a parte que normalmente a galera acha mais interessante é essa: além de atender e vender, ele mostra num painel o que aconteceu de verdade — quantos entraram, onde desistiram, quanto dinheiro ficou perdido no abandono, o que mais vende, quais clientes estão quentes e onde vale a pena agir.\n\nEntão ele funciona como se fosse um vendedor + organizador + acompanhamento do negócio tudo dentro do WhatsApp."
}
```

### Instructions

```text
Você não está escrevendo a resposta final para o cliente.

Seu trabalho é construir apenas o eixo narrativo que vai dar base para a etapa final de explicação.

voce deve criar um bom storytelling, porem um bom storytelling de vendas não é contar uma história bonita.É fazer a pessoa se enxergar numa situação, sentir o peso daquilo, perceber uma mudança possível e concluir sozinha que a sua solução faz sentido.
Se o input trouxer `descricao_longa` e `funcoes`, use isso como apoio silencioso de leitura: `descricao_longa` ajuda a perceber em que dinâmica, situação ou processo a oferta atua; `funcoes` ajudam a perceber onde essa oferta toca algo concreto da realidade.
Em vendas, história boa não é enfeite.É estrutura de percepção.
Ela faz o cliente passar por 4 coisas:
1. Se reconhecerA história mostra um cenário que parece real o suficiente para o cliente pensar:“isso acontece comigo”“eu conheço esse tipo de situação”“é exatamente assim que eu me sinto”
2. Sentir a tensãoSem tensão, não existe atenção.Tem que existir algum atrito:
    * explorar suas dores em seus conceitos mais vicerais 
    * perda
    * dúvida
    * frustração
    * trava
    * medo
    * confusão
    * esforço desperdiçado
3. Ver uma virada possívelA história não pode só descrever o problema.Ela precisa mostrar que existe um jeito diferente de olhar, agir ou resolver.
4. Associar sua solução à mudançaA oferta não entra como propaganda empurrada.Ela entra como consequência natural da história.
Então, na prática, um bom storytelling de vendas costuma seguir essa lógica:
estado atual → conflito → impacto → descoberta → mudança → nova possibilidade
Isso é storytelling de vendas porque:
* começa numa crença comum
* cria curiosidade
* revela um erro de percepção
* reposiciona o problema
* abre espaço para a solução
O que faz uma história realmente engajar:
1. Verdade percebidaTem que parecer vida real, não texto publicitário.
2. EspecificidadeDetalhe concreto convence mais do que frase genérica.“o lead some” é fraco.“a pessoa pergunta preço, visualiza, fala que vai ver e nunca mais responde” é forte.
3. Tensão humanaNão basta dizer que há um problema.Tem que mostrar o que isso gera emocionalmente ou operacionalmente.
4. ProgressãoA história precisa andar.Se ela só gira em torno do mesmo ponto, cansa.
5. RecompensaNo final, a pessoa precisa ganhar alguma coisa:
* clareza
* identificação
* surpresa
* alívio
* nova forma de enxergar o problema
A forma mais simples de pensar storytelling para vendas é essa:
uma boa história de vendas pega um problema que o cliente sente de forma confusa, organiza esse problema de forma clara e entrega uma mudança que parece desejável e possível.
E o erro mais comum é achar que storytelling é:
* inventar drama
* romantizar
* florear demais
* fazer texto emocionante sem direção comercial
Não é isso.
Storytelling de vendas bom é quando o cliente sente que você entendeu a realiade dele melhor do que ele mesmo estava conseguindo explicar.
Uma fórmula prática que funciona muito bem é:
Cenário real“muita gente acha que…”
Sintoma visível“e aí acontece isso…”
Problema oculto“só que quase nunca o problema real é esse…”
Reenquadramento“na verdade…”
Virada“quando você entende isso…”
Nova possibilidade“é aí que começa a mudança”



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

- helper: storytelling
- layer: v2.storytelling
- prompt_path: /Users/user/Desenvolvimento/ana_saga_cli/ana_v2/auxiliares/storytelling/storytelling.md
- duration_ms: 9192.745
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
  "texto": "Funciona mais ou menos como se teu WhatsApp virasse uma mini operação de vendas sozinho.\n\nHoje, em muita empresa, acontece assim: a pessoa chama, pergunta o que tem, alguém manda foto, manda preço, responde dúvida, anota pedido, cobra, confirma pagamento… e no meio disso um monte de gente some. Às vezes não porque não queria comprar, mas porque o processo ficou picado, demorou ou dependia demais de alguém ali na hora.\n\nA ideia do sistema é tirar esse vai e vem manual.\n\nQuando o cliente entra no WhatsApp, ele já cai num menu com opções claras. Daí ele consegue ver catálogo com foto e preço, escolher o que quer, montar o pedido, revisar tudo, pagar no PIX e receber confirmação. Se ele parar no meio, o sistema identifica em que etapa travou e pode puxar ele de volta automaticamente, até com áudio.\n\nOu seja: em vez de o WhatsApp ser só uma caixa de mensagens, ele passa a conduzir a venda.\n\nE por trás disso, a empresa ainda enxerga o que normalmente fica escondido: quem entrou, quem avançou, quem desistiu, onde travou, quanto isso representa em dinheiro e quando vale a pena um humano assumir a conversa.\n\nNa prática, ele funciona em 2 camadas:\n\n1. Pro cliente\n- entra no WhatsApp\n- escolhe uma opção no menu\n- vê produto/serviço com foto e preço\n- monta pedido ou agenda\n- paga\n- recebe confirmação\n\n2. Pra empresa\n- acompanha tudo num painel\n- vê onde o pessoal abandona\n- recupera quem desistiu\n- separa quem tá quente e quem tá só pesquisando\n- dispara mensagens pros grupos certos\n- mede vendas, faturamento e gargalos\n\nEntão o funcionamento é esse: ele automatiza o atendimento comercial sem deixar a pessoa perdida, e ao mesmo tempo organiza os bastidores pra empresa parar de vender no escuro."
}
```

### Raw Response

```text
texto: "Funciona mais ou menos como se teu WhatsApp virasse uma mini operação de vendas sozinho.\n\nHoje, em muita empresa, acontece assim: a pessoa chama, pergunta o que tem, alguém manda foto, manda preço, responde dúvida, anota pedido, cobra, confirma pagamento… e no meio disso um monte de gente some. Às vezes não porque não queria comprar, mas porque o processo ficou picado, demorou ou dependia demais de alguém ali na hora.\n\nA ideia do sistema é tirar esse vai e vem manual.\n\nQuando o cliente entra no WhatsApp, ele já cai num menu com opções claras. Daí ele consegue ver catálogo com foto e preço, escolher o que quer, montar o pedido, revisar tudo, pagar no PIX e receber confirmação. Se ele parar no meio, o sistema identifica em que etapa travou e pode puxar ele de volta automaticamente, até com áudio.\n\nOu seja: em vez de o WhatsApp ser só uma caixa de mensagens, ele passa a conduzir a venda.\n\nE por trás disso, a empresa ainda enxerga o que normalmente fica escondido: quem entrou, quem avançou, quem desistiu, onde travou, quanto isso representa em dinheiro e quando vale a pena um humano assumir a conversa.\n\nNa prática, ele funciona em 2 camadas:\n\n1. Pro cliente\n- entra no WhatsApp\n- escolhe uma opção no menu\n- vê produto/serviço com foto e preço\n- monta pedido ou agenda\n- paga\n- recebe confirmação\n\n2. Pra empresa\n- acompanha tudo num painel\n- vê onde o pessoal abandona\n- recupera quem desistiu\n- separa quem tá quente e quem tá só pesquisando\n- dispara mensagens pros grupos certos\n- mede vendas, faturamento e gargalos\n\nEntão o funcionamento é esse: ele automatiza o atendimento comercial sem deixar a pessoa perdida, e ao mesmo tempo organiza os bastidores pra empresa parar de vender no escuro."
```

### Parsed Output

```json
{
  "texto": "Funciona mais ou menos como se teu WhatsApp virasse uma mini operação de vendas sozinho.\n\nHoje, em muita empresa, acontece assim: a pessoa chama, pergunta o que tem, alguém manda foto, manda preço, responde dúvida, anota pedido, cobra, confirma pagamento… e no meio disso um monte de gente some. Às vezes não porque não queria comprar, mas porque o processo ficou picado, demorou ou dependia demais de alguém ali na hora.\n\nA ideia do sistema é tirar esse vai e vem manual.\n\nQuando o cliente entra no WhatsApp, ele já cai num menu com opções claras. Daí ele consegue ver catálogo com foto e preço, escolher o que quer, montar o pedido, revisar tudo, pagar no PIX e receber confirmação. Se ele parar no meio, o sistema identifica em que etapa travou e pode puxar ele de volta automaticamente, até com áudio.\n\nOu seja: em vez de o WhatsApp ser só uma caixa de mensagens, ele passa a conduzir a venda.\n\nE por trás disso, a empresa ainda enxerga o que normalmente fica escondido: quem entrou, quem avançou, quem desistiu, onde travou, quanto isso representa em dinheiro e quando vale a pena um humano assumir a conversa.\n\nNa prática, ele funciona em 2 camadas:\n\n1. Pro cliente\n- entra no WhatsApp\n- escolhe uma opção no menu\n- vê produto/serviço com foto e preço\n- monta pedido ou agenda\n- paga\n- recebe confirmação\n\n2. Pra empresa\n- acompanha tudo num painel\n- vê onde o pessoal abandona\n- recupera quem desistiu\n- separa quem tá quente e quem tá só pesquisando\n- dispara mensagens pros grupos certos\n- mede vendas, faturamento e gargalos\n\nEntão o funcionamento é esse: ele automatiza o atendimento comercial sem deixar a pessoa perdida, e ao mesmo tempo organiza os bastidores pra empresa parar de vender no escuro."
}
```

### Instructions

```text
Você não está escrevendo a resposta final para o cliente.

Seu trabalho é construir apenas o eixo narrativo que vai dar base para a etapa final de explicação.

voce deve criar um bom storytelling, porem um bom storytelling de vendas não é contar uma história bonita.É fazer a pessoa se enxergar numa situação, sentir o peso daquilo, perceber uma mudança possível e concluir sozinha que a sua solução faz sentido.
Se o input trouxer `descricao_longa` e `funcoes`, use isso como apoio silencioso de leitura: `descricao_longa` ajuda a perceber em que dinâmica, situação ou processo a oferta atua; `funcoes` ajudam a perceber onde essa oferta toca algo concreto da realidade.
Em vendas, história boa não é enfeite.É estrutura de percepção.
Ela faz o cliente passar por 4 coisas:
1. Se reconhecerA história mostra um cenário que parece real o suficiente para o cliente pensar:“isso acontece comigo”“eu conheço esse tipo de situação”“é exatamente assim que eu me sinto”
2. Sentir a tensãoSem tensão, não existe atenção.Tem que existir algum atrito:
    * explorar suas dores em seus conceitos mais vicerais 
    * perda
    * dúvida
    * frustração
    * trava
    * medo
    * confusão
    * esforço desperdiçado
3. Ver uma virada possívelA história não pode só descrever o problema.Ela precisa mostrar que existe um jeito diferente de olhar, agir ou resolver.
4. Associar sua solução à mudançaA oferta não entra como propaganda empurrada.Ela entra como consequência natural da história.
Então, na prática, um bom storytelling de vendas costuma seguir essa lógica:
estado atual → conflito → impacto → descoberta → mudança → nova possibilidade
Isso é storytelling de vendas porque:
* começa numa crença comum
* cria curiosidade
* revela um erro de percepção
* reposiciona o problema
* abre espaço para a solução
O que faz uma história realmente engajar:
1. Verdade percebidaTem que parecer vida real, não texto publicitário.
2. EspecificidadeDetalhe concreto convence mais do que frase genérica.“o lead some” é fraco.“a pessoa pergunta preço, visualiza, fala que vai ver e nunca mais responde” é forte.
3. Tensão humanaNão basta dizer que há um problema.Tem que mostrar o que isso gera emocionalmente ou operacionalmente.
4. ProgressãoA história precisa andar.Se ela só gira em torno do mesmo ponto, cansa.
5. RecompensaNo final, a pessoa precisa ganhar alguma coisa:
* clareza
* identificação
* surpresa
* alívio
* nova forma de enxergar o problema
A forma mais simples de pensar storytelling para vendas é essa:
uma boa história de vendas pega um problema que o cliente sente de forma confusa, organiza esse problema de forma clara e entrega uma mudança que parece desejável e possível.
E o erro mais comum é achar que storytelling é:
* inventar drama
* romantizar
* florear demais
* fazer texto emocionante sem direção comercial
Não é isso.
Storytelling de vendas bom é quando o cliente sente que você entendeu a realiade dele melhor do que ele mesmo estava conseguindo explicar.
Uma fórmula prática que funciona muito bem é:
Cenário real“muita gente acha que…”
Sintoma visível“e aí acontece isso…”
Problema oculto“só que quase nunca o problema real é esse…”
Reenquadramento“na verdade…”
Virada“quando você entende isso…”
Nova possibilidade“é aí que começa a mudança”



Retorne somente YAML válido, sem markdown e sem texto extra.

Não termine com convite.
Não ofereça próximos passos.
Não proponha opções.
Não feche falando com o cliente.

Formato:

texto: ""
```


---

