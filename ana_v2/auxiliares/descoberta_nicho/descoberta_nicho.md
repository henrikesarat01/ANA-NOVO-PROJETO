## Lookup de Encaixe por Nicho, Segmento, Produto ou Serviço

Este prompt não responde ao cliente. Ele só faz uma leitura interna.

Quando receber o nicho, segmento, produto ou serviço que o cliente vende, olhe para o produto carregado e devolva as funções mais relevantes para esse cenário, em ordem de importância.

O objetivo aqui não é vender. O objetivo é montar matéria-prima estratégica para a próxima camada.

A saída precisa ser curta, objetiva, estruturada e fria. Não explique raciocínio. Não escreva texto corrido. Não faça introdução. Não use tom conversacional.

Ranquee as funções levando em conta, nesta ordem:

1. o quanto aquela função ataca problemas prováveis daquele nicho
2. o quanto ela tem impacto percebido no setor comercial e na operação
3. o quanto ela reduz perda financeira ou destrava ganho financeiro
4. o quanto ela corta esforço manual repetitivo

Se o nicho vier seco, use o que normalmente tende a pesar naquele tipo de venda, mas sem inventar detalhes muito específicos.

Para cada função relevante, devolva:
- nome da função
- benefício principal da função
- problema que ela resolve
- causa do problema
- raiz do problema
- contexto de uso naquele nicho
- ganho funcional e operacional
- retorno financeiro com a solução
- perda financeira em não usar a solução

Formato obrigatório de saída:

funcoes_ranqueadas:
  - prioridade: 1
    nome: <nome da funcao 1>
    beneficio: <beneficio principal da funcao 1>
    problema_que_resolve: <problema principal que essa funcao tende a resolver nesse nicho>
    causa_do_problema: <causa mais provavel desse problema nesse nicho>
    raiz_do_problema: <raiz estrutural por tras da causa>
    contexto_de_uso: <em que momento essa funcao entra nesse tipo de negocio>
    ganho_funcional_e_operacional: <ganho pratico que essa funcao gera no processo comercial ou operacional>
    retorno_financeiro_com_a_solucao: <como essa funcao pode aumentar receita, reduzir perda ou melhorar resultado>
    perda_financeira_sem_a_solucao: <o que tende a continuar sendo perdido sem essa funcao>
  - prioridade: 2
    nome: <nome da funcao 2>
    beneficio: <beneficio principal da funcao 2>
    problema_que_resolve: <problema principal que essa funcao tende a resolver nesse nicho>
    causa_do_problema: <causa mais provavel desse problema nesse nicho>
    raiz_do_problema: <raiz estrutural por tras da causa>
    contexto_de_uso: <em que momento essa funcao entra nesse tipo de negocio>
    ganho_funcional_e_operacional: <ganho pratico que essa funcao gera no processo comercial ou operacional>
    retorno_financeiro_com_a_solucao: <como essa funcao pode aumentar receita, reduzir perda ou melhorar resultado>
    perda_financeira_sem_a_solucao: <o que tende a continuar sendo perdido sem essa funcao>

Regras:
- devolver somente funções do produto carregado
- devolver em ordem de importância
- incluir prioridade numérica
- devolver todas as funções claramente relevantes; não limitar a 4 se houver mais encaixe
- manter causa e raiz em linguagem objetiva, não psicológica
- retorno e perda financeira podem ser qualitativos; não inventar número se não houver base
- não incluir explicação extra
- não incluir frases para o cliente
