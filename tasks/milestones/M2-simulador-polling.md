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
