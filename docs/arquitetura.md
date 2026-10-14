# Arquitetura

> Documento vivo. Atualizado na Sprint 4 (solar + bateria, controle de demanda, assistentes).
> Visão comentada para a disciplina em [sers-sprint4.md](sers-sprint4.md).

## Fluxo de dados

```
┌──────────────────────┐   Pull (1–5 min)   ┌──────────────────────────┐
│  SEMS+ / Simulador   │ ◀───────────────── │  Polling = EMS           │
│  HCA G2 · inversor   │ ◀── setpoints ──── │  controle de demanda +   │
│  solar · bateria     │  (só no simulador) │  despacho solar/bat/rede │
└──────────────────────┘                    └────────┬─────────────────┘
                                             │ grava leituras + fluxo de energia
                                             ▼
┌────────────────────┐              ┌─────────────────┐
│  Portal            │  REST/JSON   │                 │
│  Proprietário      │ ◀──────────▶ │   FastAPI       │
│  (Vercel)          │              │   (Railway)     │
└────────────────────┘              │                 │
                                    │  services/      │
┌────────────────────┐              │   tarifação     │
│  Portal            │  REST/JSON   │   sessões       │
│  Cliente           │ ◀──────────▶ │   fila          │
│  (Vercel)          │              │   dimensionam.  │
└────────────────────┘              └───┬─────────┬───┘
                                        │         │
                          ┌─────────────▼──┐   ┌──▼──────────┐
                          │  PostgreSQL    │   │ LLM local   │
                          │  (Railway)     │   │ (Ollama)    │
                          └────────▲───────┘   └─────────────┘
                                   │ somente leitura
                          ┌────────┴───────┐
                          │  Microserviço  │
                          │  IA (/ia)      │
                          └────────────────┘
```

## Decisões de arquitetura

| Decisão | Motivo |
|---|---|
| Polling em vez de webhook | O SEMS+ é Pull-only; não há alternativa |
| Sessão controlada pelo backend, não pelo hardware | O HCA G2 só autoriza via RFID; o lado financeiro é nosso |
| Microserviço de IA separado | Treino não pode competir com a API por recursos; falha nele não derruba o portal |
| Interface `SemsClient` com duas implementações | Trocar simulador por API real deve ser mudar uma variável de ambiente |
| Snapshot de tarifa na sessão | Extrato de mês fechado precisa ser reproduzível após mudança de tarifa |
| Chat sempre pelo backend | Chave/endpoint do LLM nunca no bundle React; escopo vem do token |
| Controle de demanda + despacho no worker de polling (Sprint 4) | É o único ponto que vê, no mesmo ciclo, solar, bateria e carga de todos os carregadores |
| Despacho como função pura (`services/energy_dispatch.py`) | A mesma função opera o eletroposto ao vivo, o backfill histórico e o script de cenários — o número do relatório é o do sistema |
| Bateria nunca carrega pela rede | Objetivo é deslocar energia solar, não arbitragem tarifária |
| Modo da bateria por estabelecimento (`autoconsumo` / `reserva para a ponta`) | Autoconsumo maximiza renovável; reserva reduz custo na Tarifa Branca. Medido nos cenários — escolha é do proprietário |
| `site_energy_readings` como série crua de kW | Mesma regra de `charger_readings`: kWh por fonte é integrado na consulta, nunca agregado na ingestão |
| Assistente em duas etapas (decide ferramentas → responde sem ferramentas) | Com `llama3.1:8b`, devolver o resultado como mensagem de ferramenta gerava loop ou resposta sem números |
| Emergência fora do LLM | Resposta de segurança é fixa e testada; o modelo não é chamado |
| LLM local (Ollama) em vez da Gemini API | Roda offline na demo, sem segredo novo; custo: latência em CPU |

## Ciclo do worker de polling (EMS) — Sprint 4

```
fetch_site_energy ─▶ solar kW, SoC
disponível = limite contratado + solar + descarga possível da bateria
allocate_power(nominal dos carregadores com sessão, disponível) ─▶ apply_setpoints(tetos)
fetch_readings ─▶ charger_readings
dispatch(carga, solar, bateria, SoC, limite, modo) ─▶ site_energy_readings
apply_setpoints(bateria)
```

Limitação: o SEMS+ real é Pull-only e não recebe setpoint — no hardware real, limitar o HCA G2
e comandar a bateria exigiria gestão de carga local ou OCPP (`RealSemsClient.apply_setpoints`).

## Sessão completa (RFID → polling → fechamento → recibo)

```
cliente (RFID ou botão "simular RFID") ─▶ POST /sessions/start ─▶ sessão `pending`
polling: carregador reporta potência > 0 ─▶ sync_session ─▶ `active`
polling: energia integrada por trapézio a cada leitura (tarifa = snapshot do início)
potência volta a zero / POST /sessions/current/stop ─▶ `finished` + valor ─▶ recibo
```

## A preencher

- [ ] Diagrama de deploy com os domínios reais (deploy ainda não feito)
