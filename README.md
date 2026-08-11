# ChargeGrid Manager

Plataforma de gestão de carregamento de veículos elétricos sobre o **GoodWe HCA G2**.
Dois portais web — proprietário do estabelecimento e cliente final —, backend único e módulo
de IA para previsão de demanda, detecção de anomalias e segmentação de clientes.

> Nome provisório. Ver `CLAUDE.md` para trocar.

## O problema

O HCA G2 não expõe API pública e o portal SEMS+ da GoodWe só oferece modelo **Pull**.
O ChargeGrid Manager resolve isso com um serviço de polling que consulta o SEMS+
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

## Rodando localmente

Ainda não implementado — este repositório contém a estrutura e o plano. Os comandos abaixo
passam a valer ao final de M0:

```bash
docker compose up -d
```

```bash
cd backend && uvicorn app.main:app --reload
```

```bash
cd frontend-proprietario && npm run dev
```

## Limitações conhecidas

- A API do EV Charger da GoodWe não está disponível; a integração usa polling do SEMS+.
- Na demo, os dados de hardware vêm de um **simulador** que reproduz a curva P(t) real de
  carregamento. O contrato de dados é idêntico ao esperado do SEMS+.
- Potências nominais em rede 220/380 V e preços de aquisição dos modelos GW7K/GW11K/GW22K
  dependem de confirmação no datasheet oficial da GoodWe — marcados como `TODO(datasheet)`.
