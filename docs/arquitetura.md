# Arquitetura

> Documento vivo. Preencher os diagramas durante M0 e revisar em M9.

## Fluxo de dados

```
┌──────────────┐   Pull (1–5 min)   ┌─────────────────┐
│  SEMS+ /     │ ◀───────────────── │  Polling        │
│  Simulador   │                    │  (Python async) │
└──────────────┘                    └────────┬────────┘
                                             │ grava leituras
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
                          │  PostgreSQL    │   │ Gemini API  │
                          │  (Railway)     │   │ + LangChain │
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
| Chat sempre pelo backend | Chave da Gemini no bundle React é chave vazada |

## A preencher

- [ ] Diagrama de sequência de uma sessão completa (RFID → polling → fechamento → recibo)
- [ ] Diagrama de deploy com os domínios reais
