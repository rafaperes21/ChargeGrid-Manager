# M3 — Motor de tarifação e sessões

Status: em andamento — cálculo, sessão e fila concluídos; só falta o módulo dedicado de
planos/assinatura, deliberadamente em espera (ver nota abaixo)
Responsável: —
Depende de: M1, M2
Skill: `.claude/skills/tarifacao-e-sessoes/`

## Objetivo

O coração financeiro do produto. Tudo que envolve dinheiro passa por aqui, e erro aqui é
prejuízo real ou cliente cobrado a mais. **É o milestone que mais precisa de teste.**

## Escopo

### Tarifas
- [x] CRUD de `tariff_rules`: faixas pico / fora de pico / madrugada por dia da semana
- [x] Validação: faixas não se sobrepõem e cobrem 24 h; fallback documentado se houver buraco
- [x] Faixas que cruzam a meia-noite tratadas corretamente
- [ ] Regras especiais: desconto por plano, minutos gratuitos condicionais
      (ex.: primeira meia hora grátis nos fins de semana)
- [x] Definição em horário local (`America/Sao_Paulo`), persistência em UTC

### Sessões
- [x] Máquina de estados `pending → active → finished | error` — `services/sessions.py` +
      router `api/sessions.py`. `sync_session` recomputa o estado a partir das leituras
      persistidas a cada chamada (idempotente, sem cursor de progresso)
- [x] Abertura por RFID; timeout de 5 min sem potência → `error` sem cobrança
- [x] Acúmulo de kWh a partir das leituras do polling (trapézio, `energy_integration.py`)
- [x] Detecção de fim por potência zerada em N leituras consecutivas (constante de engenharia,
      não confirmada numericamente com o time — ver comentário em `sessions.py`)
- [x] Fechamento: aplica a ordem de cálculo da skill (bruto → promoção → desconto de plano →
      franquia → valor final) via `services/pricing.py` (função pura, sem I/O) e grava
      **snapshot** da tarifa aplicada em `charging_sessions`
- [x] Geração de recibo digital — `build_receipt`, derivado do snapshot, sem tabela nova;
      exposto em `GET /sessions/{id}/receipt`

### Planos e fila
- [ ] Assinatura, franquia em kWh, descontos de 15 % / 25 % — **em espera**: o time está
      definindo com o professor a melhor forma de modelar isso antes de implementar
      `services/plans.py`. Os modelos `Plan`/`Subscription` e o CRUD (`api/plans.py`) já
      existem; sem assinatura ativa, sessões e fila tratam o cliente como `avulso` (sem
      desconto, sem franquia) — não há regressão, só falta a lógica de ciclo dedicada
- [x] Fila: ordenação por prioridade de plano, depois ordem de chegada — `services/queue.py` +
      router `api/queue.py`
- [x] Reserva de 15 min ao liberar vaga; expirou → volta ao fim do próprio tier (mesma
      prioridade, chegada agora — nunca sai da fila por perder a vez)
- [ ] Reserva antecipada de 15 min retira a vaga da oferta da fila — mecanismo distinto do
      acima (cliente reservar um horário futuro sem estar na fila ao vivo), não modelado

## Plano de execução

Owner: Pessoa 1 (backend). Depende de M1 (schema, snapshot de tarifa) e M2 (`charger_readings`
fluindo). É o milestone com mais teste unitário exigido — não adiar os testes para o final.

1. **CRUD de `tariff_rules`** — `app/api/tariffs.py` + `app/services/tariff_rules.py`:
   faixas `peak`/`off_peak`/`overnight` por dia da semana, definidas em horário local
   (`America/Sao_Paulo`), persistidas em UTC. Validação de não-sobreposição e cobertura de
   24h no próprio CRUD; faixas cruzando meia-noite tratadas como dois intervalos ou lógica
   circular — é onde o bug aparece (skill `tarifacao-e-sessoes` §2).
2. **Motor de cálculo puro** — `app/services/pricing.py`, testável sem HTTP: ordem fixa
   bruto → minutos grátis (promoção) → desconto do plano (%) → franquia em kWh → valor final
   (skill §3). O desconto do plano incide sobre o valor já promocional, nunca sobre o bruto —
   não inverter a ordem.
3. **Máquina de estados de sessão** — `app/services/sessions.py`:
   `pending → active → finished | error`. `pending` com timeout de 5 min sem potência → `error`
   sem cobrança. `active` acumula `energy_kwh` a partir das leituras de M2 via trapézio
   (reaproveitar `energy_integration.py`). Fim detectado por potência zerada em N leituras
   consecutivas.
4. **Fechamento e snapshot** — ao fechar, gravar `tariff_rate_applied`, `plan_discount_pct`,
   `free_minutes_applied`, `tariff_rule_id` em `charging_sessions` (campos já existentes desde
   M1) e gerar recibo digital. Nunca recalcular extrato antigo lendo a tabela de tarifas atual.
5. **Planos e franquia** — `app/services/plans.py`: `avulso`/`mensal` (15%, franquia)
   /`trimestral` (25%, franquia maior), franquia abatida em kWh antes de virar dinheiro,
   sem acumular entre ciclos.
6. **Fila inteligente** — `app/services/queue.py`: ordenação `prioridade_do_plano DESC`,
   `entrou_na_fila_em ASC`, sem outro critério de desempate. Vaga liberou → notifica o primeiro
   e reserva 15 min; não respondeu → fim da fila do próprio tier. Reserva antecipada retira a
   vaga da oferta da fila.
7. **Testes unitários** — cobrir explicitamente os casos do critério de aceite abaixo antes de
   considerar o milestone fechado (virada de faixa, meia-noite, ordem promoção/desconto,
   franquia, fila entre planos, sessão `error` sem cobrança).
8. **Ponta a ponta com o simulador** — abrir sessão por RFID simulado, acumular via M2, fechar,
   conferir o valor contra o cálculo manual.

## Critérios de aceite

- [x] Suite de testes unitários cobrindo, no mínimo:
  - [x] sessão que atravessa a virada de faixa mantém a tarifa do início (tarifa resolvida
        uma única vez, em `started_at`, nunca recalculada no fechamento)
  - [x] faixa cruzando a meia-noite calcula certo (já coberto desde o CRUD de tarifas)
  - [x] promoção + desconto de plano aplicados na ordem correta (não acumulados sobre o bruto)
  - [x] franquia abatida em kWh antes da conversão em dinheiro
  - [x] franquia excedida cobra o excedente com desconto do plano
  - [ ] fila: assinante trimestral entra depois de um avulso e é atendido antes — a
        *ordenação* por prioridade está testada (`test_queue.py`); esse cenário específico
        (planos reais avulso vs. trimestral) depende do `plans.py` em espera
  - [x] sessão em `error` não gera cobrança (timeout sem potência e tarifa não configurada,
        os dois caminhos testados)
- [ ] Extrato de um mês fechado permanece idêntico depois de alterar a tabela de tarifas —
      coberto pelo *design* (snapshot gravado no fechamento, nunca relido da tabela atual),
      não por um teste dedicado que altere a tarifa depois e reconfira o extrato antigo
- [x] Sessão completa ponta a ponta: abre por RFID, acumula, fecha, valor confere com o
      cálculo manual — testado tanto com dados sintéticos (`test_sessions.py`) quanto ao vivo
      contra o servidor real, com o polling do M2 alimentando as leituras

## Religamento do front (27/08/2026)

Atualização: o front foi conectado nesta rodada, com confirmação explícita do usuário.
`SessaoPage.jsx`/`FilaPage.jsx`/`HistoricoPage.jsx` (cliente) e `FilaProprietarioPage.jsx`/
`RelatoriosPage.jsx`/`TarifasPage.jsx` (proprietário) consomem os endpoints reais agora — os
banners "em construção" citando M3 foram removidos. Ver M4/M5 pros detalhes tela por tela.
Dois endpoints novos nasceram desse religamento (não existiam quando M3/M2 fecharam):
`GET /sessions/mine` (histórico do cliente) e `GET /establishments/{id}/reports` (fechamento
financeiro por período, usado por `RelatoriosPage.jsx`). `GET /sessions/current` ganhou
`estimated_amount_due` (valor ao vivo projetado enquanto a sessão está `active`) e
`GET /sessions/{id}/receipt` ganhou a decomposição em R$ (bruto/promoção/desconto/franquia),
reconstruída do snapshot já persistido — nunca reprocessada contra tarifa/plano atuais.

## Armadilhas

- Recalcular extrato antigo lendo a tarifa atual é o bug clássico deste domínio. Snapshot.
- `float` em dinheiro. `Decimal`, sempre.
