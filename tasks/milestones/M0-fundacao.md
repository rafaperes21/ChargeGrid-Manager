# M0 — Fundação do repositório

Status: não iniciado
Responsável: —
Depende de: —
Cobre as atividades 7 e 8 do desafio.

## Objetivo

Ter um repositório onde as cinco frentes possam trabalhar em paralelo sem pisar uma na outra,
com ambiente reproduzível em qualquer máquina do time.

## Escopo

- [ ] Decidir o nome do produto e propagar (`CLAUDE.md`, `README.md`, `package.json`)
- [ ] Repositório GitHub criado, com a estrutura de pastas do `CLAUDE.md`
- [ ] `README.md` na raiz: o que é o produto, como rodar, quem faz o quê
- [ ] Branch `main` protegida; trabalho em branch por feature, merge via PR
- [ ] `backend/`: projeto FastAPI mínimo com `/health`, `requirements.txt` (ou `pyproject.toml`)
- [ ] `frontend-proprietario/` e `frontend-cliente/`: Vite + React + Tailwind, tela em branco que sobe
- [ ] `ia/`: projeto FastAPI mínimo com `/health`
- [ ] `docker-compose.yml` com Postgres para desenvolvimento local
- [ ] `.env.example` em cada serviço, com todas as variáveis documentadas
- [ ] CI no GitHub Actions: lint + testes do backend a cada PR
- [ ] Desenhos das telas principais (Figma ou papel fotografado) commitados em `docs/`:
      dashboard do proprietário e sessão em andamento do cliente, no mínimo

## Critérios de aceite

- Qualquer pessoa do time clona, roda `docker compose up` + os comandos do README e tem
  os quatro serviços de pé em menos de 10 minutos, sem perguntar nada a ninguém.
- `GET /health` responde 200 no backend e no serviço de IA.
- Um PR de teste dispara o CI e ele passa.
- `.env` está no `.gitignore` e nenhum segredo foi commitado.

## Armadilhas

- Não deixe o desenho das telas para depois de começar o código. Metade do retrabalho de
  frontend em hackathon vem de não ter combinado a tela antes.
- Defina o nome agora. Renomear depois toca em deploy, domínio e slides.
