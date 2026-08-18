# M3 — Motor de tarifação e sessões

Status: não iniciado
Responsável: —
Depende de: M1, M2
Skill: `.claude/skills/tarifacao-e-sessoes/`

## Objetivo

O coração financeiro do produto. Tudo que envolve dinheiro passa por aqui, e erro aqui é
prejuízo real ou cliente cobrado a mais. **É o milestone que mais precisa de teste.**

## Escopo

### Tarifas
- [ ] CRUD de `tariff_rules`: faixas pico / fora de pico / madrugada por dia da semana
- [ ] Validação: faixas não se sobrepõem e cobrem 24 h; fallback documentado se houver buraco
- [ ] Faixas que cruzam a meia-noite tratadas corretamente
- [ ] Regras especiais: desconto por plano, minutos gratuitos condicionais
      (ex.: primeira meia hora grátis nos fins de semana)
- [ ] Definição em horário local (`America/Sao_Paulo`), persistência em UTC

### Sessões
- [ ] Máquina de estados `pending → active → finished | error`
- [ ] Abertura por RFID; timeout de 5 min sem potência → `error` sem cobrança
- [ ] Acúmulo de kWh a partir das leituras do polling
- [ ] Detecção de fim por potência zerada em N leituras consecutivas
- [ ] Fechamento: aplica a ordem de cálculo da skill (bruto → promoção → desconto de plano →
      franquia → valor final) e grava **snapshot** da tarifa aplicada
- [ ] Geração de recibo digital

### Planos e fila
- [ ] Assinatura, franquia em kWh, descontos de 15 % / 25 %
- [ ] Fila: ordenação por prioridade de plano, depois ordem de chegada
- [ ] Reserva de 15 min ao liberar vaga; expirou → volta ao fim do próprio tier
- [ ] Reserva antecipada de 15 min retira a vaga da oferta da fila

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

- Suite de testes unitários cobrindo, no mínimo:
  - sessão que atravessa a virada de faixa mantém a tarifa do início
  - faixa cruzando a meia-noite calcula certo
  - promoção + desconto de plano aplicados na ordem correta (não acumulados sobre o bruto)
  - franquia abatida em kWh antes da conversão em dinheiro
  - franquia excedida cobra o excedente com desconto do plano
  - fila: assinante trimestral entra depois de um avulso e é atendido antes
  - sessão em `error` não gera cobrança
- Extrato de um mês fechado permanece idêntico depois de alterar a tabela de tarifas.
- Sessão completa ponta a ponta com o simulador: abre por RFID, acumula, fecha, valor confere
  com o cálculo manual.

## Armadilhas

- Recalcular extrato antigo lendo a tarifa atual é o bug clássico deste domínio. Snapshot.
- `float` em dinheiro. `Decimal`, sempre.
