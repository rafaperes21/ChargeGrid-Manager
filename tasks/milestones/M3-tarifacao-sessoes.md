# M3 — Motor de tarifação e sessões

Status: concluído — cálculo, sessão, fila e planos fechados. O módulo de planos, que ficava
em espera aguardando alinhamento com o professor, foi desbloqueado em 27/08/2026 (ver nota
"Planos padronizados" abaixo) com uma decisão diferente da originalmente cogitada: catálogo
fixo definido pela plataforma, não um `services/plans.py` de ciclo/franquia configurável.
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
- [x] Catálogo fixo de planos (`avulso`/`mensal` 15%/`trimestral` 25%) definido pela
      plataforma em `services/plan_catalog.py` — decisão do professor, ver nota abaixo
- [x] Fila: ordenação por prioridade de plano, depois ordem de chegada — `services/queue.py` +
      router `api/queue.py`, prioridade resolvida via `plan_catalog.get_tier(plan.kind)`
- [x] Reserva de 15 min ao liberar vaga; expirou → volta ao fim do próprio tier (mesma
      prioridade, chegada agora — nunca sai da fila por perder a vez)
- [x] Reserva antecipada (cliente reservar um horário futuro sem estar na fila ao vivo) —
      modelada em `services/reservations.py`, ver `M10-motion-mapa-3d.md` Prioridade 2

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
5. **Planos e franquia** — `app/services/plan_catalog.py`: catálogo fixo `avulso`/`mensal`
   (15%, franquia)/`trimestral` (25%, franquia maior) definido pela plataforma, franquia
   abatida em kWh antes de virar dinheiro, sem acumular entre ciclos. Proprietário só liga/
   desliga (`Plan.enabled`) — nunca define valor (ver nota "Planos padronizados" abaixo).
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
  - [x] fila: assinante com plano de maior prioridade entra depois de um avulso e é
        atendido antes — `test_join_queue_ordena_por_prioridade_depois_ordem_de_chegada`,
        agora usando o catálogo fixo (`PlanKind.trimestral`) em vez de prioridade arbitrária
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

**Correção de contrato (motion design, mesma rodada):** `GET /sessions/current` podia devolver
a própria sessão com `status` já `finished`/`error` no exato poll em que `sync_session` fecha
ela (o objeto muda de status dentro da mesma chamada, antes do próximo poll parar de
encontrá-la pelo filtro `pending`/`active`). Isso vazava um status terminal pro cliente numa
resposta 200, quebrando a suposição de "pending/active ou 404" que o frontend (tela de
confirmação de sessão encerrada) dependia. Corrigido: o endpoint agora sempre 404 se, depois de
`sync_session`, o status não for mais `pending`/`active` — quem quiser o resultado fechado usa
`GET /sessions/{id}/receipt`. Teste:
`test_read_current_session_404_no_mesmo_poll_que_fecha_a_sessao`.

## Planos padronizados e pagamento declarativo (27/08/2026)

Feedback direto do professor, trazido pelo usuário nesta rodada: o modelo original — cada
proprietário define livremente preço/desconto/franquia por plano — é confuso. Decisão:
**catálogo fixo definido pela plataforma**, o proprietário só escolhe quais níveis oferece.
Isso desbloqueia o item que ficava em espera (ver [[project-plans-py-em-espera]], agora
superado) — mas com uma modelagem diferente da originalmente cogitada (não é o
`services/plans.py` de ciclo/franquia livre citado no plano de execução acima).

- `services/plan_catalog.py`: `PLAN_CATALOG` com os 3 níveis (`avulso`/`mensal` 15%+50kWh/
  `trimestral` 25%+180kWh, valores da skill `tarifacao-e-sessoes` §4). `Plan` (model) perdeu
  `name`/`price`/`discount_pct`/`free_kwh_allowance`/`priority` — restou só `kind` + `enabled`
  (unique em `establishment_id, kind`). Toda leitura desses valores (sessão, fila) passa a
  consultar `plan_catalog.get_tier(kind)`, nunca a coluna (que não existe mais).
- `provision_plans_for_establishment` cria as 3 linhas na criação do estabelecimento
  (`avulso` habilitado, `mensal`/`trimestral` desabilitados) — migration `517ddb444cd5`
  fez o backfill pros estabelecimentos que já existiam antes desta mudança.
- `PATCH /plans/{id}` (só `enabled`) substitui o antigo `POST /plans` de criação livre.
  `UsuariosPlanosPage.jsx` virou lista de toggles, sem formulário de valores.
- **Pagamento** (gap que o professor também apontou — não existia forma de pagamento em
  lugar nenhum do sistema): `Establishment.accepted_payment_methods` (CSV, mesmo padrão de
  `TariffRule.days_of_week`) configurável em `TarifasPage.jsx`; `ChargingSession.payment_method`
  declarativo (`PATCH /sessions/current/payment-method`, cliente escolhe enquanto
  pending/active) — nunca processa pagamento de verdade, sem gateway/PCI/simulação de
  latência, mesmo espírito do snapshot de tarifa. Aparece como mais uma linha na timeline
  animada de confirmação de sessão encerrada (`SessaoPage.jsx`, Prioridade 1 do M10).
- 162 testes backend passando (`test_plan_catalog.py`, `test_plans_api.py` novos; ajustes em
  `test_queue.py`/`test_sessions.py` que criavam `Plan` com os campos antigos).

## Armadilhas

- Recalcular extrato antigo lendo a tarifa atual é o bug clássico deste domínio. Snapshot.
- `float` em dinheiro. `Decimal`, sempre.
