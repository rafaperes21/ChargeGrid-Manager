# M0 — Fundação do repositório

Status: em andamento — falta só validar branch protection e um PR de teste real (ver checklist)
Responsável: —
Depende de: —
Cobre as atividades 7 e 8 do desafio.

## Objetivo

Ter um repositório onde as cinco frentes possam trabalhar em paralelo sem pisar uma na outra,
com ambiente reproduzível em qualquer máquina do time.

## Escopo

- [x] Decidir o nome do produto e propagar (`CLAUDE.md`, `README.md`, `package.json`)
- [x] Repositório GitHub criado, com a estrutura de pastas do `CLAUDE.md`
- [x] `README.md` na raiz: o que é o produto, como rodar, quem faz o quê
- [ ] Branch `main` protegida; trabalho em branch por feature, merge via PR — **não verificado
      por aqui** (é config do GitHub, precisa confirmar em Settings → Branches); o fluxo
      branch-por-feature + PR já está documentado em `guiabranch.md` e foi seguido no PR #1
- [x] `backend/`: projeto FastAPI mínimo com `/health`, `requirements.txt` (ou `pyproject.toml`)
      — foi além do M0, já entrega M1 inteiro (models, auth JWT/Google, CRUD)
- [x] `frontend-proprietario/` e `frontend-cliente/`: Vite + React + Tailwind, tela em branco que sobe
- [x] `ia/`: projeto FastAPI mínimo com `/health`
- [x] `docker-compose.yml` com Postgres para desenvolvimento local — arquivo pronto; **não
      validado localmente** (Docker Desktop não estava rodando nas máquinas usadas até agora)
- [x] `.env.example` em cada serviço, com todas as variáveis documentadas
- [x] CI no GitHub Actions: lint + testes do backend a cada PR — `.github/workflows/ci.yml`
      cobre backend + ia + os dois frontends; falta confirmar que já rodou verde num PR real
- [x] Desenhos das telas principais commitados em `docs/telas/` (wireframes de baixa
      fidelidade, dashboard do proprietário e sessão do cliente) — e agora também um modelo de
      alta fidelidade das 10 telas dos dois portais + mockup dos assistentes de IA, ver
      `docs/telas/README.md`

## Plano de execução

Feito pelas duas pessoas juntas (ver `tasks/plano-2-pessoas.md`, Fase 0). Ordem pensada para
não bloquear ninguém.

1. **Nome do produto** — `ChargeGrid-Manager` (kebab-case) já decidido e propagado em
   `CLAUDE.md`, `README.md`, `tasks/README.md` e nas descrições de skill. Falta só levar para
   os `package.json` quando forem criados nos passos 4 e 5.
2. **Branch protection** — proteger `main` (exigir PR + CI verde antes de merge); comunicar o
   fluxo branch-por-feature no README.
3. **`docker-compose.yml`** — serviço `postgres` com volume nomeado e variáveis via `.env`.
   Serviços de app entram no compose (ou documentados no README) conforme os passos 4–6 forem
   existindo.
4. **`backend/` mínimo** (paralelo ao 5) — `pyproject.toml`/`requirements.txt` com FastAPI +
   Uvicorn + SQLAlchemy + Alembic; `app/main.py` com `GET /health`; `.env.example` com
   `DATABASE_URL` e o que mais for previsível.
5. **`ia/` mínimo** (paralelo ao 4) — mesmo padrão do passo 4, só `/health`. Sem modelo real
   ainda; isso é M8.
6. **`frontend-proprietario/` e `frontend-cliente/`** — `npm create vite@latest` (template
   React) + Tailwind, tela em branco que sobe com `npm run dev`; `package.json` já com o nome
   decidido no passo 1; `.env.example` (`VITE_API_URL`).
7. **Desenhos das telas** — dashboard do proprietário + sessão em andamento do cliente, em
   `docs/telas/`. Fazer **antes** de começar código de frontend de verdade (M4/M5) —
   é a armadilha nº 1 deste milestone.
8. **`.env.example` — auditoria final** — conferir que todo serviço (`backend/`, `ia/`, os dois
   frontends, raiz do compose) tem o arquivo atualizado e que `.env` real está fora do git
   (já confirmado no `.gitignore`).
9. **CI no GitHub Actions** — workflow em PR: lint + `pytest` do backend. Validar com um PR de
   teste.
10. **Fechamento do `README.md`** — seção "quem faz o quê" (linkar `tasks/plano-2-pessoas.md`)
    e atualizar "Rodando localmente" com os comandos reais depois dos passos 3–6.

## Critérios de aceite

- [ ] Qualquer pessoa do time clona, roda `docker compose up` + os comandos do README e tem
  os quatro serviços de pé em menos de 10 minutos, sem perguntar nada a ninguém. — não validado
  (Docker Desktop indisponível nas máquinas usadas até agora; `docker-compose.yml` está pronto)
- [x] `GET /health` responde 200 no backend e no serviço de IA — testado, `pytest` verde nos dois.
- [ ] Um PR de teste dispara o CI e ele passa — o workflow existe e cobre os 4 serviços; falta
  confirmar uma execução verde real no GitHub Actions.
- [x] `.env` está no `.gitignore` e nenhum segredo foi commitado.

## Armadilhas

- Não deixe o desenho das telas para depois de começar o código. Metade do retrabalho de
  frontend em hackathon vem de não ter combinado a tela antes.
- Defina o nome agora. Renomear depois toca em deploy, domínio e slides.
