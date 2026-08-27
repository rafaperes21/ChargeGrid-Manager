# M2 — Simulador de hardware e polling

Status: concluído (com uma decisão de escopo registrada abaixo)
Responsável: —
Depende de: M1
Skill: `.claude/skills/integracao-sems-simulador/`

## Objetivo

Ter dados fluindo. Nada no produto — dashboard, sessão, IA, relatório — funciona ou demonstra
sem isso. **É o gargalo escondido do projeto; comece cedo.**

## Escopo

- [x] Interface `SemsClient` + `SimulatedSemsClient` e `RealSemsClient` (stub), escolhidos
      por `SEMS_SOURCE` no `.env` (`app/integracoes/sems_client.py`, `get_sems_client()`)
- [x] Schema `ChargerReading` conforme a skill — `ChargerReadingContract` em
      `app/schemas/charger_reading.py` (reaproveita o `ChargerStatus` do resto do app em vez
      de duplicar o enum; só `livre/carregando/problema/offline` saem de uma leitura real,
      `reservado` é estado de negócio nosso)
- [x] Serviço de polling assíncrono, intervalo configurável — `app/integracoes/polling.py`
      (`PollingService`, `POLL_INTERVAL_SECONDS`, default 60s). Desligado por padrão
      (`POLLING_ENABLED=false`): roda via `python -m app.integracoes.polling` (worker
      separado) ou junto do FastAPI (`lifespan` em `app/main.py`) se a env var for `true`
- [x] Persistência idempotente em `charger_readings` — índice único `(charger_id, timestamp)`
      via migration + checagem antes de inserir (check-then-insert, não upsert de dialeto
      específico — mesmo comportamento em Postgres e SQLite dos testes)
- [x] Integração de energia por **trapézio** entre leituras (`backend/simulador/energy.py`,
      com teste dedicado) — movida para `app/services/energy_integration.py` durante o M3,
      reaproveitada tanto pelo simulador quanto pelo motor de sessão
- [x] Tolerância a falha: `PollingService` conta falhas consecutivas do `SemsClient` e marca
      todos os carregadores `offline` após N (`POLLING_OFFLINE_AFTER_FAILURES`, default 3),
      sem derrubar a API — testado com um `SemsClient` fake que sempre falha
- [x] Simulador com curva P(t): rampa → platô → taper acima de 80 % → fim, com ruído de ±2 %
      (`backend/simulador/curve_engine.py`)
- [x] Limite pelo OBC do veículo, não só pelo carregador (`backend/simulador/vehicles.py`)
- [x] Perfis de dia típico por tipo de estabelecimento (`backend/simulador/profiles.py`)
- [x] Geração de **60–90 dias de histórico retroativo** (`historical_generator.py`)
- [x] Cenários injetáveis: pico com fila cheia, falha de equipamento, pico anormal de consumo
      (`backend/simulador/anomalies.py`)
- [x] `--seed` para reprodutibilidade (`historical_generator.py --seed`)

## Nota de implementação — leitura ao vivo correlacionada com sessão real

O `SimulatedSemsClient` não sorteia sessões de carregamento por conta própria (o que o
`historical_generator.py` faz para o histórico retroativo). A cada tick, ele pergunta se o
carregador tem uma `ChargingSession` `pending`/`active` aberta (M3) e, se tiver, gera o ponto
da curva P(t) correspondente ao tempo decorrido desde `started_at`; sem sessão aberta, o
carregador fica ocioso (`livre`, potência zero). Isso é deliberado, não um atalho: quem
controla início/fim de sessão é o ChargeGrid-Manager, não o hardware (`CLAUDE.md`), e fazer o
simulador inventar carregamentos por conta própria estaria simulando esse contrato errado.

Efeito prático: rodar o polling e abrir uma sessão via `POST /sessions/start` já é suficiente
para ela evoluir sozinha (`pending → active → finished`, com `energy_kwh`/`amount_due`
calculados) — sem precisar inserir `charger_readings` na mão. Validado ao vivo contra o
servidor real antes de fechar este milestone.

**Fica de fora, deliberadamente**: tráfego "ambiente" (carregadores carregando sozinhos por
probabilidade horária/perfil de estabelecimento, sem ninguém logado testando) — alimentaria o
dashboard e o treino da IA fora de uma demo ativa, mas não é o mesmo mecanismo e não bloqueava
nada além dele mesmo. Próxima extensão natural do `SimulatedSemsClient`, não uma pendência.

## Plano de execução

Owner: Pessoa 1 (backend/dados). Depende de M1 ter pelo menos os modelos `Charger` e
`ChargerReading` migrados — se M1 ainda não fechou, adiante só esse recorte antes de começar
aqui.

1. **Contrato e interface** — `app/schemas/charger_reading.py` (`ChargerReading`, campos
   conforme a skill) e `app/integracoes/sems_client.py` com a classe abstrata `SemsClient`
   (`async def fetch_readings(charger_serials) -> list[ChargerReading]`). `SEMS_SOURCE` no
   `.env`/`.env.example` + factory `get_sems_client()`. **Critério de aceite a proteger:**
   trocar essa variável não pode tocar nada fora de `integracoes/`.
2. **`SimulatedSemsClient` e motor de curva P(t)** — `backend/simulador/curve_engine.py` com as
   4 fases (rampa 0–2min → platô com `min(P_carregador, P_máx_OBC_veículo)` e ruído gaussiano
   ±2% → taper 80–100% linear até ~10% da nominal → fim). Catálogo simples de veículos/OBC para
   modelar o limite do lado do carro, não só do carregador.
3. **Perfis e cenários injetáveis** — dia típico por tipo de estabelecimento (shopping: pico
   noturno/fim de semana; empresa: pico às 8h); cenários de pico com fila cheia, falha de
   equipamento (consumo zerado com carro plugado) e pico anormal, expostos como parâmetro, não
   hardcoded. `--seed` em tudo que usa aleatoriedade.
4. **Serviço de polling** — `app/integracoes/polling.py`, task assíncrona no startup do
   FastAPI, `POLL_INTERVAL_SECONDS` (default 60). Tolerância a falha: try/except, contador de
   falhas consecutivas, backoff, `offline` após N falhas — sem derrubar a API.
5. **Persistência idempotente** — chave = (`charger_serial`, `timestamp` do device); upsert /
   `ON CONFLICT DO NOTHING`. Guardar toda leitura crua, sem agregar — é matéria-prima de M8.
6. **Integração de energia por trapézio** — `app/services/energy_integration.py`:
   `Δenergia = (P_anterior + P_atual)/2 × Δt_horas`. Nunca potência × intervalo cheio. Teste
   unitário dedicado — é o erro que "superfatura o cliente e alguém vai notar na demo".
7. **Histórico retroativo** — `backend/simulador/gerar_historico.py`, 60–90 dias, <1 min de
   execução, mesmos perfis/curva dos passos 2–3. Bloqueia M8 (Prophet não treina sem isso) —
   não deixar para depois.
8. **`RealSemsClient` — stub** — mesma interface, `NotImplementedError` por ora. Isolar
   autenticação/rate limit/paginação do SEMS+ real aqui quando a API existir.
9. **Testes e validação contra os critérios de aceite** — trapézio com valores conhecidos,
   idempotência (mesma leitura 2x não duplica energia), forma da curva, 10 min de simulador sem
   duplicata, `gerar_historico.py` com inspeção visual dos picos por tipo de estabelecimento.

## Critérios de aceite

- [x] Rodando o simulador contra o servidor real, `charger_readings` recebe leituras
      plausíveis e nenhuma duplicada (validado ao vivo + `test_polling.py`/`test_sems_client.py`)
- [x] A curva de uma sessão tem rampa, platô e taper visíveis — não é uma reta
      (`curve_engine.py`, já validado desde a parte batch do milestone)
- [x] O script de histórico gera 90 dias em menos de 1 min (já validado antes desta rodada)
- [x] Trocar `SEMS_SOURCE` não exige mudar nenhuma linha fora de `integracoes/` — testado via
      `get_sems_client()` despachando por `settings.sems_source`
- [ ] Os cenários de falha efetivamente disparam os alertas de M8 — a detecção de falha do
      *polling* (SEMS+ fora do ar → `offline`) está testada; a integração ponta a ponta com os
      alertas do M8 (potência zero prolongada, etc.) não foi reexercitada nesta rodada

## Armadilhas

- Dado limpo demais é pior que dado ruim: o detector de anomalias aprende um padrão irreal e
  dispara falso positivo em produção.
- Não multiplique a última potência pelo intervalo do polling. Trapézio. Esse erro superfatura
  o cliente e alguém vai notar na demo.
