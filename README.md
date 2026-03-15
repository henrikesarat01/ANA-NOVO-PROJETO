# ANA SAGA CLI — rebuild

Rebuild limpo do agente de negociação avançada, pronto para testar no terminal, sem acoplamento com WhatsApp.

## O que entra aqui

- motor de etapas com personalidades novas
- motor BPCF contínuo
- lookup do arsenal SAGA
- base factual do inventário de funcionalidades
- CLI para conversar no terminal
- modo `mock` para smoke test sem API
- modo `openai` para testar com modelo real
- suíte de checks de naturalidade

## Arquitetura

```text
src/ana_saga_cli/
  config.py
  cli.py
  domain/
  knowledge/
  sales/
  llm/
  prompting/
  evals/
  data/
```

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Testar em modo mock

```bash
PYTHONPATH=src ANA_PROVIDER=mock python -m ana_saga_cli.cli
```

## Testar com OpenAI

Preencha `OPENAI_API_KEY` no ambiente ou no `.env`, depois:

```bash
PYTHONPATH=src ANA_PROVIDER=openai ANA_MODEL=gpt-5.4 python -m ana_saga_cli.cli
```

## Rodar bateria de naturalidade

```bash
PYTHONPATH=src ANA_PROVIDER=mock python scripts/run_naturality_suite.py
```

ou com modelo real:

```bash
PYTHONPATH=src ANA_PROVIDER=openai ANA_MODEL=gpt-5.4 python scripts/run_naturality_suite.py
```

## O que observar nos testes

- resposta curta quando o cliente fala pouco
- ausência de tom corporativo
- ausência de CTA forçado em toda resposta
- uma intenção principal por turno
- conexão problema → característica → SAGA sem verbalizar causa/raiz
- perguntas leves e no máximo uma por turno

## Observação

O modo `mock` serve para validar a orquestração e os guardrails.  
A naturalidade final deve ser testada com modelo real.
