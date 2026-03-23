# SAGA — Inventário de Funcionalidades

> Lista unificada de tudo que a plataforma SAGA faz hoje.  
> Cada item aparece uma só vez, mesmo que esteja presente em vários fluxos.

---

## Mensagens WhatsApp

- **Texto** - envia uma mensagem de texto simples para o contato
- **Imagem** - envia uma foto com legenda opcional
- **Vídeo** - envia um vídeo com legenda opcional
- **Áudio** - envia um áudio gravado, pode ser como mensagem de voz (aquele bolinha verde) ou como arquivo
- **Documento** - envia arquivos como PDF, planilha, DOC etc.
- **Localização** - envia um pin no mapa com endereço e nome do local
- **Contato** - envia um cartão de contato com nome, telefone etc.
- **Lista** - envia uma lista interativa onde o usuário abre e escolhe entre várias opções organizadas em seções
- **Botões** - envia até 3 botões clicáveis abaixo da mensagem para o usuário escolher
- **Carrossel** - envia vários cards lado a lado que o usuário desliza, cada card tem imagem, título, descrição e botões
- **Carousel Cards** - variante do carrossel que monta os cards de forma programática
- **Formulário** - envia um formulário nativo do WhatsApp onde o usuário preenche campos
- **Native Flow** - envia uma tela interativa nativa do WhatsApp (flows da Meta)
- **Reação** - envia um emoji de reação em cima de uma mensagem existente
- **Figurinha** - envia um sticker/figurinha animado ou estático

## Gerenciamento de Mensagens

- **Marcar como lida** - marca uma mensagem recebida como lida (dois checks azuis)
- **Apagar mensagem** - apaga uma mensagem já enviada para todos
- **Editar mensagem** - edita o texto de uma mensagem já enviada

## Gestão de Instâncias

- **QR Code** - gera o QR Code para o cliente escanear e conectar o WhatsApp dele à plataforma
- **Webhooks** - configura URLs para receber notificações quando algo acontece (mensagem recebida, status mudou etc.)

---

## Funcionalidades dos Fluxos

- **Botões Iniciais** - menu de entrada do fluxo com as opções principais que o cliente pode escolher
- **Carrossel de Produtos** - envia um carrossel deslizável com os produtos/itens disponíveis, cada card com foto, nome, preço e botão
- **Cardápio** - exibe os itens disponíveis (pratos, bebidas, produtos) organizados por categoria com preço
- **Detalhes do Produto** - mostra a ficha completa de um item: fotos, descrição, preço, especificações
- **Seleção de Pagamento** - oferece as formas de pagamento disponíveis (PIX, cartão etc.)
- **Pagamento PIX** - gera o QR Code do PIX para o cliente pagar direto pelo WhatsApp
- **Verificação de Pagamento** - verifica automaticamente se o PIX foi pago e avisa o cliente e o vendedor quando confirmado
- **Confirmação de Pedido** - mostra o resumo completo do pedido (itens, valor, endereço, pagamento) e pede confirmação antes de finalizar
- **Follow-up por Áudio** - quando o cliente abandona o fluxo, envia automaticamente um áudio de voz (como se fosse gravado na hora) para tentar recuperar
- **Acompanhamento de Abandono** - rastreia em qual etapa cada cliente parou e permite visualizar/recuperar esses contatos
- **Reserva de Mesa** - permite o cliente reservar mesa informando data, horário e número de pessoas
- **Eventos** - exibe a lista de eventos disponíveis e permite inscrição
- **Pedido Delivery** - fluxo completo de pedido para entrega com coleta de endereço
- **Gestão de Mesas** - controle de mesas e ocupação do estabelecimento
- **Agendamento de Visita** - permite o cliente agendar uma visita escolhendo data e horário
- **Falar com Atendente** - escalona a conversa para um atendente humano quando o bot não resolve
- **Qualificação por Quiz** - faz perguntas interativas para entender o perfil do lead automaticamente
- **Qualificação de Lead** - pontua o lead e classifica como quente, morno ou frio baseado nas respostas
- **Simulação de Financiamento** - calcula parcelas, entrada e prazo de financiamento dentro do WhatsApp
- **Acompanhamento de Obra** - mostra o status da obra com fotos e percentual de conclusão
- **Nutrição de Funil** - envia conteúdos automaticamente de acordo com o estágio do lead no funil
- **Recomendação Inteligente** - sugere automaticamente o produto/empreendimento mais adequado ao perfil do lead

## Editor Visual de Fluxos

- **Editor drag-and-drop** - interface visual onde se cria fluxos arrastando blocos e conectando com linhas, sem precisar programar
- **Nós de Mensagem** - blocos para enviar texto, imagem, áudio, vídeo e documento
- **Nós de Interação** - blocos de botões, listas e carrossel
- **Nós de Lógica** - blocos de condições (se/senão), delays (esperar X tempo) e webhooks (chamar API externa)
- **Preview em tempo real** - simula como o fluxo vai funcionar direto no editor antes de publicar
- **Exportação/Importação** - exporta o fluxo em JSON e importa fluxos existentes para editar

---

## Dashboard


- **KPIs em tempo real** - cards com os números principais: total de pedidos, faturamento, ticket médio, taxa de conversão, leads, abandonos, clientes únicos
- **Data Picker** - seletor de período com atalhos (hoje, ontem, últimos 7 dias) para filtrar todos os dados
- **Lista de Pedidos** - lista atualizada em tempo real com todos os pedidos finalizados e seus detalhes
- **Funil de Conversão** - gráfico de funil mostrando quantas pessoas passaram por cada etapa e onde desistiram
- **Kanban CRM** - quadro estilo Trello com cards representando cada lead, arrastáveis entre colunas de estágio
- **User Journey** - timeline visual mostrando tudo que um usuário fez: botões clicados, textos enviados, telas visitadas
- **Abandonos por Etapa** - mostra quantas pessoas abandonaram em cada etapa do funil, com lista dos telefones para recuperação
- **Disparos em Massa** - envio de mensagens em lote para grupos filtrados: todos, inativos, recorrentes, por produto ou leads que nunca compraram
- **Analytics de Produtos** - ranking dos produtos mais vendidos com quantidade, faturamento e tendências
- **Analytics de Pagamentos** - comparativo entre métodos de pagamento (PIX vs Cartão) com valores e taxas
- **Faturamento BI** - gráficos de evolução do faturamento por dia, semana e mês
- **Análise Temporal** - identifica horários de pico e dias da semana com mais vendas
- **Curva ABC** - classifica os produtos em A (top), B (médio) e C (baixo) por faturamento
- **Análise de Bebidas/Upsell** - mostra taxa de venda adicional, qual bebida mais combinou com cada prato
- **Clientes Únicos/Recorrentes** - separa clientes novos de recorrentes, mostra frequência, retenção e valor do cliente ao longo do tempo (LTV)
- **Conversão Econômica** - calcula quanto dinheiro foi perdido em cada etapa do funil (abandono × ticket médio)
- **Comparativo de Período** - compara os números da semana atual com a anterior
- **Análise por Bairro** - mostra pedidos, faturamento e ticket médio quebrados por bairro de entrega
- **Cohort Analysis** - análise de retenção: quantos clientes da semana X continuam comprando nas semanas seguintes
- **Timeline de Conversões** - gráfico diário mostrando a evolução de leads → qualificados → carrinho → conversão
- **Sazonalidade** - padrões por dia da semana com variação e tendência
- **Clientes em Risco (Churn)** - lista de clientes que não compram há muito tempo, com nível de risco (baixo/médio/alto)
- **Análise de Margem** - calcula custo, margem bruta, ponto de equilíbrio e lucro por produto
- **Pareto de Clientes** - mostra que os top 20% dos clientes representam X% do faturamento

---

## Tracking

- **Rastreamento de Sessão** - registra automaticamente quando um usuário inicia, interage e finaliza (ou abandona) um fluxo
- **Eventos de Interação** - grava cada ação do usuário: botão clicado, texto digitado, tela visitada, com timestamp
- **Registro de Conversão** - marca quando um lead vira cliente e registra o valor da venda
- **Registro de Abandono** - marca em qual exata etapa o usuário parou e saiu do fluxo
- **Analytics por Fluxo** - dados consolidados de funil, produtos vendidos e pagamentos para cada fluxo
