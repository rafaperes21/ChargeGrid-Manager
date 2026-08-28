# ChargeGrid-Manager

Plataforma de gestão de carregamento de veículos elétricos construída sobre o carregador
**GoodWe HCA G2**. Dois portais web (proprietário do estabelecimento e cliente final),
um backend único, e um módulo de IA/ML.

> **Nome do produto:** `ChargeGrid-Manager` (kebab-case) é o nome decidido pelo grupo.
> Usar exatamente essa grafia em `package.json`, slugs de deploy (Vercel/Railway) e domínio.
> Se precisar trocar de novo, atualizar aqui, no `README.md` e nos `package.json`.

---

## Contexto do desafio

O HCA G2 **não expõe API pública**. O SEMS+ (portal da GoodWe) só oferece modelo **Pull**.
Isso define toda a arquitetura de integração:

- Um **serviço de polling** em Python consulta o SEMS+ a cada 1–5 min e persiste
  potência/status de cada carregador.
- O **controle de sessão** (início/fim, cobrança) é do ChargeGrid-Manager, não do hardware.
  O gatilho é o cartão RFID: aproximou → abre sessão; desconectou → fecha e calcula valor.
- O HCA G2 apenas **autoriza** o carregamento via RFID físico cadastrado no SEMS+.
  Nós controlamos o lado financeiro e de dados.

Para o hackathon/demo, o SEMS+ é substituído por um **simulador** que gera dados realistas
seguindo a curva P(t) da atividade 5. O contrato de dados é idêntico — trocar simulador por
SEMS+ real deve ser mudar uma variável de ambiente, nada mais.

---

## Stack

| Camada | Tecnologia |
|---|---|
| Frontend (2 portais) | React + Vite + Tailwind CSS |
| Backend | Python 3.11 + FastAPI + SQLAlchemy + Alembic |
| Banco | PostgreSQL |
| IA/ML | scikit-learn / Prophet — microserviço FastAPI separado |
| Chatbot | Gemini API (free tier) + LangChain |
| Hospedagem | Vercel (frontends) + Railway (backend + IA + Postgres) |

---

## Estrutura do repositório

```
/backend                 API REST FastAPI — serve os dois frontends
  /app
    /api                 routers por domínio (auth, sessoes, tarifas, ...)
    /core                config, segurança, dependências
    /models              SQLAlchemy
    /schemas             Pydantic
    /services            regras de negócio (tarifação, fila, dimensionamento)
    /integracoes         cliente SEMS+ e serviço de polling
  /simulador             gerador de dados do hardware (substitui o SEMS+ na demo)
  /migrations            Alembic
  /tests
/frontend-proprietario   portal do estabelecimento
/frontend-cliente        portal do motorista
/ia                      microserviço ML (previsão, anomalias, segmentação)
/docs                    arquitetura, modelo de dados, decisões
/tasks/milestones        plano de execução — leia antes de começar qualquer coisa
/.claude/skills          conhecimento de domínio reutilizável
```

---

## Regras de trabalho neste repositório

### Antes de codar
1. Leia o milestone correspondente em `tasks/milestones/`. Ele define escopo, critérios de
   aceite e dependências. Não comece um milestone cujas dependências não fecharam.
2. Se a tarefa envolve dimensionamento elétrico, tarifação, simulação de hardware, prompts de
   chatbot ou ML, **carregue a skill correspondente** em `.claude/skills/` antes de escrever
   código. Elas contêm as fórmulas e regras que não estão no código.

### Convenções
- **Idioma:** código, nomes de variáveis, tabelas e endpoints em **inglês**.
  Comentários, docstrings, UI, mensagens ao usuário e documentação em **português**.
- **Dinheiro:** sempre `Decimal` no Python e `NUMERIC(12,4)` no Postgres. Nunca `float`.
  Energia em kWh com 3 casas; potência em kW com 3 casas.
- **Tempo:** tudo em UTC no banco (`TIMESTAMPTZ`). Conversão para `America/Sao_Paulo`
  só na borda de apresentação. Faixas de tarifa são definidas em horário local — cuidado.
- **Nada de regra de negócio no router.** Router valida entrada, chama `services/`, devolve
  schema. Regra de tarifação, fila e dimensionamento vive em `services/` e é testável sem HTTP.
- **Migrations:** toda mudança de modelo gera migration Alembic. Nunca `create_all` fora de teste.
- **Segredos:** só via variável de ambiente. `.env` nunca entra no git; mantenha `.env.example`
  atualizado a cada nova variável.

### Testes
- Regras de negócio (tarifação, fila, dimensionamento, cálculo de sessão) exigem teste unitário.
  São a parte que dá errado silenciosamente e vira prejuízo financeiro.
- Endpoints críticos: um teste de integração de caminho feliz + um de erro.
- Rodar: `cd backend && pytest`

### Comandos

Pra subir a stack inteira de uma vez (Postgres, backend, IA, worker de polling contínuo e os
dois frontends) — cuida de `.env`, venv, `npm install`, migrations e seed sozinho na primeira
vez, e é seguro rodar de novo depois (`--skip-setup` pula tudo isso e só abre os serviços):

```bash
./scripts/dev.sh                      # sobe tudo (Linux/macOS)
./scripts/dev.ps1                     # idem, no Windows
./scripts/dev.sh --only backend,ia    # só um subconjunto
```

Sem o worker `polling` no ar, nenhuma sessão evolui de `pending` pra `active` e a IA não tem
leitura nova pra aprender — ele já vem incluído por padrão nos dois scripts acima.

Ou individualmente:

```bash
cd backend && uvicorn app.main:app --reload
```

```bash
cd frontend-proprietario && npm run dev
```

```bash
cd backend && alembic revision --autogenerate -m "descricao" && alembic upgrade head
```

---

## Divisão do time

Time de 2 pessoas. Plano detalhado, com fases e pontos de sincronização, em
[`tasks/plano-2-pessoas.md`](tasks/plano-2-pessoas.md).

| Pessoa | Frente |
|---|---|
| 1 | Backend: modelos, auth, sessões, tarifação, simulador/polling, IA/ML, chatbots (lógica) |
| 2 | Frontend: Portal do Proprietário, Portal do Cliente, onboarding, chatbots (UI) |

O contrato entre as frentes é o **schema OpenAPI** do FastAPI (`/docs`). Quem mexe em endpoint
avisa; quem consome gera os tipos a partir dele.

---

## Pendências que dependem de informação externa

Estão marcadas com `TODO(datasheet)` no código e nas skills. São valores do HCA G2 que precisam
ser confirmados no datasheet oficial da GoodWe antes de virar número em orçamento entregue ao
cliente — principalmente potências nominais por modelo em 220/380 V brasileiros, corrente máxima
por fase e preço de aquisição.
