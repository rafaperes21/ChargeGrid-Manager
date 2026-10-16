# ChargeGrid-Manager

Plataforma de gestão de carregamento de veículos elétricos sobre o **GoodWe HCA G2**.
Dois portais web — proprietário do estabelecimento e cliente final —, backend único, módulo
de IA para previsão de demanda, precificação sugerida e detecção de anomalias, e gestão de
energia do eletroposto com **geração solar + bateria** (simuladas) e **controle de demanda**.

## O problema

O HCA G2 não expõe API pública e o portal SEMS+ da GoodWe só oferece modelo **Pull**.
O ChargeGrid-Manager resolve isso com um serviço de polling que consulta o SEMS+
periodicamente e assume todo o controle de sessão, tarifação e dados — o hardware fica
responsável apenas por autorizar o carregamento via RFID.

## Entregas acadêmicas
- [Sprint 4 — SERS (FIAP): solução final integrada](docs/sers-sprint4.md) · [resultados quantitativos](docs/resultados/cenarios.md) (dados simulados)
- [Sprint 3 — SERS (FIAP)](docs/sers-sprint3.md)

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `backend/` | API FastAPI + serviço de polling (EMS: controle de demanda, despacho solar/bateria) + simulador do hardware |
| `backend/scripts/` | `cenarios.py` — resultados quantitativos A (sem o sistema) × B (com o sistema) |
| `frontend-proprietario/` | Portal do estabelecimento (React + Tailwind, desktop-first) |
| `frontend-cliente/` | Portal do motorista (React + Tailwind, mobile-first) |
| `ia/` | Microserviço de ML (Prophet, precificação sugerida, detecção de anomalias por regras) |
| `docs/` | Arquitetura, modelo de dados, telas, entregas da disciplina, `resultados/` e `img/` |
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

Pré-requisitos: Docker (Postgres), Python 3.11, Node 20. Para os assistentes virtuais:
[Ollama](https://ollama.com) com o modelo `llama3.1:8b` (`ollama pull llama3.1:8b`) — sem ele
o resto do sistema funciona e o assistente responde dizendo a causa (Ollama parado ou modelo
não baixado). O `dev.sh`/`dev.ps1` confere isso na subida e avisa com o comando que resolve.

### Caminho rápido — um comando só

```powershell
.\scripts\dev.ps1        # Windows (PowerShell)
```

```bash
./scripts/dev.sh         # Mac/Linux
```

Idempotente: cria os `.env` que faltarem, sobe o Postgres, cria/instala os venvs (Python 3.11)
e `node_modules` que faltarem, roda migration+seed (inclui inversor solar e bateria simulados)+
gerador de histórico+histórico de fluxo de energia no backend, e abre os serviços (backend, IA,
worker de polling e os dois frontends). Rodar de novo não duplica nada nem reinstala do
zero.

Flags úteis: `-Only backend,ia` (ou `--only backend,ia`) sobe só o que interessa para o vídeo
da IA, sem os frontends; `-SkipSetup`/`--skip-setup` só abre os serviços já instalados;
`-Recreate`/`--recreate` apaga e recria venv/`node_modules` (útil se o venv ficou com a versão
errada de Python — veja a nota sobre Python 3.11 abaixo). No Windows, cada serviço abre em uma
janela de terminal separada; no Mac/Linux, todos rodam nesta mesma janela com log prefixado
por serviço, e `Ctrl+C` encerra todos de uma vez.

O passo a passo abaixo é o que o script automatiza — use-o para entender o que está
acontecendo, rodar um passo isolado, ou depurar algo que o script não cobriu.

### Passo a passo manual

> No Windows, troque `.venv/bin/` por `.venv/Scripts/` em todos os comandos abaixo
> (PowerShell ou Git Bash — funciona nos dois, sem precisar ativar o venv). O venv **precisa**
> ser Python 3.11 especificamente (`py -3.11 -m venv .venv` no Windows,
> `python3.11 -m venv .venv` no Mac/Linux) — versões mais novas quebram o Prophet/cmdstanpy da
> IA.

Copie o `.env.example` de cada serviço para `.env` antes de rodar (raiz, `backend/`,
`frontend-cliente/`, `frontend-proprietario/`, `ia/`).

### 1. Banco de dados

```bash
docker compose up -d
```

### 2. Backend

```bash
cd backend
python3.11 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/alembic upgrade head
.venv/bin/python -m app.db.seed          # 1 estabelecimento + 4 carregadores + inversor/bateria
.venv/bin/uvicorn app.main:app --reload  # sobe em :8000
```

O seed imprime o `establishment id` — guarde-o, é usado no passo 4.

### 3. Simulador — gera histórico para a IA

Sem isso a previsão de demanda não tem dado suficiente (mínimo de 4 semanas) e o detector de
anomalias não tem nada para pegar. Roda em segundos, não precisa do backend no ar:

```bash
cd backend
.venv/bin/python -m simulador.historical_generator --seed 42
```

Gera 60–90 dias de leituras (`charger_readings`) para os carregadores já seedados, com
`--seed` fixo para reprodutibilidade, e imprime no final onde cada uma das 4 anomalias de
demonstração (potência zerada, acima da nominal, offline, energia regredindo) foi injetada —
útil para saber o que apontar na gravação. Rodar de novo sem `--force` não duplica dados.

Histórico do fluxo de energia (solar, bateria, rede) a partir dessas leituras — dados simulados:

```bash
.venv/bin/python -m simulador.energy_backfill --days 60
```

### 3b. Worker de polling (EMS)

Sem ele nenhuma sessão evolui de `pending` para `active` e a tela "Fluxo de energia" não recebe
leitura nova. A cada ciclo: lê solar/bateria, aplica o controle de demanda, lê os carregadores,
despacha solar → bateria → rede e grava o fluxo.

```bash
.venv/bin/python -m app.integracoes.polling
```

### 4. Serviço de IA

```bash
cd ia
python3.11 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --reload --port 8001
```

Abra `http://localhost:8001/docs` e chame (usando o `establishment id` do passo 2):

- `GET /anomalies/establishments/{id}?lookback_hours=2160` — alertas com evidência.
- `GET /forecast/establishments/{id}/demand?horizon_hours=48` — mapa de calor com Prophet.

Na primeira chamada de `/forecast`, o Prophet treina de verdade (leva alguns segundos) e o
`cmdstanpy` roda um binário pré-compilado — não precisa de toolchain C++/RTools instalado,
graças ao pin de versão em `ia/requirements.txt`.

### 5. Frontends

```bash
cd frontend-proprietario && npm install && npm run dev
```

```bash
cd frontend-cliente && npm install && npm run dev
```

Portas fixas: **cliente em `http://localhost:5173`** e **proprietário em `http://localhost:5174`**
(se a porta estiver ocupada, o Vite falha com erro em vez de trocar de porta). Logins de
demonstração criados pelo seed, só para ambiente local: proprietário `dono@chargegrid.demo` e
cliente `cliente@chargegrid.demo`, senha `demo1234`. Cada portal só aceita o seu perfil — a conta
do dono no portal do cliente (ou o contrário) é recusada no login com aviso.

### 6. Resultados quantitativos (dados simulados)

```bash
cd backend
.venv/bin/python -m scripts.cenarios     # docs/resultados/*.csv|.md e docs/img/*.png
```

Mesmo `--seed` → mesma saída. Fontes do fator de emissão (MCTI) e das tarifas (ANEEL) estão
no próprio script e em [docs/sers-sprint4.md](docs/sers-sprint4.md).

### Verificação rápida

`GET /health` responde `{"status": "ok"}` no backend (`:8000`) e no serviço de IA (`:8001`).

## Limitações conhecidas

- A API do EV Charger da GoodWe não está disponível; a integração usa polling do SEMS+, que é
  Pull-only — os setpoints de potência e de bateria só têm efeito no simulador.
- Inversor solar e bateria são **simulados** (premissas de dimensionamento, não datasheet).
- Assistentes rodam em LLM local (`llama3.1:8b`): 30–100 s por resposta em CPU.
- Na demo, os dados de hardware vêm de um **simulador** que reproduz a curva P(t) real de
  carregamento. O contrato de dados é idêntico ao esperado do SEMS+.
- Potências nominais em rede 220/380 V e preços de aquisição dos modelos GW7K/GW11K/GW22K
  dependem de confirmação no datasheet oficial da GoodWe — marcados como `TODO(datasheet)`.
