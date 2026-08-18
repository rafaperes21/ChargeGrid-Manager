# M2 — Simulador de hardware e polling

Status: não iniciado
Responsável: —
Depende de: M1
Skill: `.claude/skills/integracao-sems-simulador/`

## Objetivo

Ter dados fluindo. Nada no produto — dashboard, sessão, IA, relatório — funciona ou demonstra
sem isso. **É o gargalo escondido do projeto; comece cedo.**

## Escopo

- [ ] Interface `SemsClient` + `SimulatedSemsClient` e `RealSemsClient` (stub), escolhidos
      por `SEMS_SOURCE` no `.env`
- [ ] Schema `ChargerReading` conforme a skill
- [ ] Serviço de polling assíncrono, intervalo configurável (default 60 s)
- [ ] Persistência idempotente em `charger_readings` (chave = timestamp da leitura no device)
- [ ] Integração de energia por **trapézio** entre leituras
- [ ] Tolerância a falha: SEMS+ indisponível não derruba a API; após N falhas marca `offline`
- [ ] Simulador com curva P(t): rampa → platô → taper acima de 80 % → fim, com ruído de ±2 %
- [ ] Limite pelo OBC do veículo, não só pelo carregador
- [ ] Perfis de dia típico por tipo de estabelecimento
- [ ] Geração de **60–90 dias de histórico retroativo** (sem isso M8 não tem treino)
- [ ] Cenários injetáveis: pico com fila cheia, falha de equipamento, pico anormal de consumo
- [ ] `--seed` para reprodutibilidade

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

- Rodando o simulador por 10 min, `charger_readings` recebe leituras plausíveis de todos os
  carregadores e nenhuma duplicada.
- A curva de uma sessão, plotada, tem rampa, platô e taper visíveis — não é uma reta.
- O script de histórico gera 90 dias em menos de 1 min e os dados passam numa inspeção visual
  (pico noturno em shopping, pico matinal em empresa).
- Trocar `SEMS_SOURCE` não exige mudar nenhuma linha fora de `integracoes/`.
- Os cenários de falha efetivamente disparam os alertas de M8.

## Armadilhas

- Dado limpo demais é pior que dado ruim: o detector de anomalias aprende um padrão irreal e
  dispara falso positivo em produção.
- Não multiplique a última potência pelo intervalo do polling. Trapézio. Esse erro superfatura
  o cliente e alguém vai notar na demo.
