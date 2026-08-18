# M1 — Modelo de dados e backend core

Status: não iniciado
Responsável: —
Depende de: M0

## Objetivo

Esquema de banco estável e autenticação funcionando. Tudo depois disso encosta aqui — mudança
de modelo em M5 custa dez vezes mais que em M1. Gaste tempo no desenho.

## Entidades

```
establishments      estabelecimento (shopping/estacionamento/empresa), carga disponível, fase, limite kW
chargers            HCA G2: serial SEMS+, modelo, vaga, status, potência nominal
users               cliente final: email, veículo, RFID virtual, plano ativo, bloqueado?
companies           modo empresarial: frota, funcionários, centro de custo
plans               avulso / mensal / trimestral: franquia, desconto, prioridade
subscriptions       vínculo usuário↔plano com ciclo de cobrança
tariff_rules        faixa horária, dias da semana, preço/kWh, regras especiais
charging_sessions   início, fim, kWh, valor, SNAPSHOT da tarifa aplicada
charger_readings    série temporal do polling (matéria-prima da IA)
queue_entries       fila: usuário, estabelecimento, prioridade, entrada
invoices            faturas corporativas consolidadas (imutáveis)
alerts              anomalias e avisos do dashboard
```

## Escopo

- [ ] Modelos SQLAlchemy + migrations Alembic para tudo acima
- [ ] `Decimal`/`NUMERIC(12,4)` para dinheiro, `TIMESTAMPTZ` UTC para tempo (ver `CLAUDE.md`)
- [ ] Índices: `charger_readings(charger_id, timestamp)`, `charging_sessions(user_id, started_at)`,
      `charging_sessions(establishment_id, started_at)` — sem isso os relatórios travam
- [ ] Auth: JWT, login por e-mail/senha + Google OAuth
- [ ] Dois papéis: `owner` e `customer`. Dependência do FastAPI que barra acesso cruzado —
      um cliente **nunca** enxerga dado de outro cliente nem financeiro do estabelecimento
- [ ] CRUD de estabelecimentos, carregadores, usuários, planos
- [ ] Seed script com dados de demo coerentes
- [ ] OpenAPI publicado em `/docs` e avisado ao time — é o contrato com os frontends

## Plano de execução

Owner: Pessoa 1 (backend). Ordem pensada para não deixar a Pessoa 2 travada esperando.

1. **Desenho do schema antes de codar** — passar pelas 11 entidades listadas acima, fechar
   tipos (`Decimal`/`NUMERIC(12,4)` para dinheiro, `TIMESTAMPTZ` UTC para tempo, ver
   `CLAUDE.md`) e relacionamentos. Mudar isso depois de M5 custa dez vezes mais — é o ponto do
   milestone.
2. **Modelos SQLAlchemy** em `app/models/` (um módulo por domínio: `establishment.py`,
   `charger.py`, `user.py`, `tariff.py`, `session.py`, `queue.py`, `invoice.py`, `alert.py`).
   Incluir os campos de **snapshot de tarifa** em `charging_sessions`
   (`tariff_rate_applied`, `plan_discount_pct`, `free_minutes_applied`, `tariff_rule_id`) desde
   já — é a armadilha nº 1 do milestone.
3. **Migration inicial Alembic** (`alembic revision --autogenerate -m "schema inicial"`) +
   índices: `charger_readings(charger_id, timestamp)`,
   `charging_sessions(user_id, started_at)`, `charging_sessions(establishment_id, started_at)`.
4. **Auth** — JWT (`app/core/security.py`) + Google OAuth; endpoints em `app/api/auth.py`.
5. **Autorização `owner` vs `customer`** — dependência do FastAPI em `app/core/deps.py` que
   barra acesso cruzado. Escrever o teste de 403 (critério de aceite) junto com a dependência,
   não depois.
6. **CRUD básico** — `app/api/establishments.py`, `chargers.py`, `users.py`, `plans.py`.
   Sem regra de negócio no router (`CLAUDE.md`) — o que houver de lógica não trivial vai para
   `services/`.
7. **Seed script** — `backend/app/db/seed.py` (ou `scripts/seed.py`): um estabelecimento com
   carregadores, usuários e planos utilizáveis, coerente com os cenários que M2/M4/M5 vão
   precisar.
8. **Publicar OpenAPI** — subir o backend, conferir `/docs`, avisar a Pessoa 2 no sync da
   Fase 1 (`plano-2-pessoas.md`) para gerar os tipos do frontend.

## Critérios de aceite

- `alembic upgrade head` sobe do zero num banco vazio, sem erro.
- Teste automatizado prova que `customer` recebe 403 em rota de `owner`.
- Seed popula um estabelecimento com carregadores, usuários e planos utilizáveis.
- Os dois times de frontend conseguem gerar tipos a partir do OpenAPI.

## Armadilhas

- Não crie `charging_sessions` sem os campos de snapshot de tarifa. Adicionar depois obriga a
  reprocessar histórico e o extrato de meses passados deixa de bater.
- `charger_readings` cresce rápido. Índice desde o começo.
