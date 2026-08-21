# ChargeGrid-Manager

Plataforma de gestão de carregamento de veículos elétricos sobre o **GoodWe HCA G2**.
Dois portais web — proprietário do estabelecimento e cliente final —, backend único e módulo
de IA para previsão de demanda, detecção de anomalias e segmentação de clientes.

## O problema

O HCA G2 não expõe API pública e o portal SEMS+ da GoodWe só oferece modelo **Pull**.
O ChargeGrid-Manager resolve isso com um serviço de polling que consulta o SEMS+
periodicamente e assume todo o controle de sessão, tarifação e dados — o hardware fica
responsável apenas por autorizar o carregamento via RFID.

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `backend/` | API FastAPI + serviço de polling + simulador do hardware |
| `frontend-proprietario/` | Portal do estabelecimento (React + Tailwind, desktop-first) |
| `frontend-cliente/` | Portal do motorista (React + Tailwind, mobile-first) |
| `ia/` | Microserviço de ML (Prophet, detecção de anomalias, K-Means) |
| `docs/` | Arquitetura, modelo de dados, telas |
| `tasks/milestones/` | Plano de execução — **comece por aqui** |
| `.claude/skills/` | Conhecimento de domínio: dimensionamento, tarifação, simulação, prompts, ML |

## Por onde começar

1. Leia [`CLAUDE.md`](CLAUDE.md) — convenções e decisões de arquitetura.
2. Leia [`tasks/README.md`](tasks/README.md) — os 10 milestones e o caminho crítico.
3. Comece por [`M0 — Fundação`](tasks/milestones/M0-fundacao.md).

## Quem faz o quê

Time de 2 pessoas — backend (dados, integrações, IA) e frontend (os dois portais). Divisão
completa, por fase e com pontos de sincronização, em
[`tasks/plano-2-pessoas.md`](tasks/plano-2-pessoas.md).

## Rodando localmente

Copie o `.env.example` de cada serviço para `.env` antes de rodar (raiz, `backend/`,
`frontend-cliente/`, `frontend-proprietario/`, `ia/`).

```bash
docker compose up -d
```

```bash
cd backend && python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --reload
```

```bash
cd ia && python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8001
```

```bash
cd frontend-proprietario && npm install && npm run dev
```

```bash
cd frontend-cliente && npm install && npm run dev
```

`GET /health` responde `{"status": "ok"}` no backend e no serviço de IA.

## Limitações conhecidas

- A API do EV Charger da GoodWe não está disponível; a integração usa polling do SEMS+.
- Na demo, os dados de hardware vêm de um **simulador** que reproduz a curva P(t) real de
  carregamento. O contrato de dados é idêntico ao esperado do SEMS+.
- Potências nominais em rede 220/380 V e preços de aquisição dos modelos GW7K/GW11K/GW22K
  dependem de confirmação no datasheet oficial da GoodWe — marcados como `TODO(datasheet)`.
