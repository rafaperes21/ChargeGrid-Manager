# Modelo de dados

> Documento vivo. Preencher o diagrama ER durante M1.

## Entidades

| Tabela | Papel | Observações críticas |
|---|---|---|
| `establishments` | estabelecimento | carga disponível (kW), fase, limite de potência |
| `chargers` | HCA G2 | serial do SEMS+, modelo, vaga, potência nominal |
| `users` | cliente final | modelo do veículo, RFID virtual, bloqueado? |
| `companies` | modo empresarial | frota, funcionários, centro de custo |
| `plans` | avulso/mensal/trimestral | franquia (kWh), desconto (%), prioridade na fila |
| `subscriptions` | usuário ↔ plano | ciclo de cobrança, franquia consumida |
| `tariff_rules` | faixas horárias | dias da semana, hora início/fim, preço/kWh |
| `charging_sessions` | sessão | **snapshot** da tarifa aplicada — não recalcular pelo histórico |
| `charger_readings` | série temporal | matéria-prima da IA; nunca agregar na ingestão |
| `queue_entries` | fila | prioridade do plano + ordem de chegada |
| `invoices` | fatura corporativa | **imutável**; correção via nota de ajuste |
| `alerts` | anomalias e avisos | severidade + leitura que disparou |

## Regras transversais

- Dinheiro: `NUMERIC(12,4)`. Nunca `float`, nunca `REAL`.
- Tempo: `TIMESTAMPTZ` em UTC. Faixas de tarifa definidas em `America/Sao_Paulo`.
- Energia: kWh com 3 casas. Potência: kW com 3 casas.

## Índices obrigatórios

```sql
CREATE INDEX ON charger_readings (charger_id, timestamp DESC);
CREATE INDEX ON charging_sessions (user_id, started_at DESC);
CREATE INDEX ON charging_sessions (establishment_id, started_at DESC);
```

`charger_readings` cresce rápido (n_carregadores × 1440/intervalo por dia). Índice desde o
começo, senão os relatórios financeiros e o treino do modelo travam.

## A preencher

- [ ] Diagrama ER (dbdiagram.io ou Mermaid)
- [ ] Dicionário de dados campo a campo, após M1
