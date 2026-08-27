# M8 — Módulo de IA/ML

Status: em andamento
Responsável: —
Depende de: M2, M3
Skill: `.claude/skills/ml-previsao-e-anomalias/`

## Objetivo

Microserviço FastAPI separado em `/ia`, lendo o Postgres em **modo leitura**. Nunca escreve nas
tabelas transacionais.

Regra geral: sem dados suficientes, devolve `insufficient_data` — não um palpite. Número errado
no dashboard custa mais caro que "ainda coletando dados".

## Escopo

### Previsão de demanda
- [x] Prophet como padrão (sazonalidade diária e semanal + feriados são a estrutura do dado)
- [x] Alvo: sessões (ou kWh) por hora, próximas 24–48 h, por estabelecimento
- [ ] Regressores: hora, dia da semana, feriado nacional, tipo de estabelecimento — Prophet
      captura sazonalidade diária/semanal nativamente; não confirmado regressor explícito de
      feriado nacional/tipo de estabelecimento
- [x] Mínimo de 4 semanas de histórico; abaixo disso, `insufficient_data`
      (`has_sufficient_history`)
- [x] Endpoint consumido pelo dashboard: mapa de calor hora × dia (`build_heatmap`)
- [x] Rótulo em linguagem natural (`label_peaks`)
- [x] Backtest com **corte temporal** (nunca split aleatório), MAE e MAPE (`run_backtest`)

### Precificação dinâmica sugerida
- [x] Regra sobre a previsão: acima do p80 histórico → sugere aumento; abaixo do p20 → redução
      (`ia/app/services/pricing_suggestion.py`, endpoint
      `GET /pricing-suggestions/establishments/{id}`)
- [x] Limites `max_increase_pct` / `max_decrease_pct` configurados pelo proprietário
      (`Establishment.max_increase_pct`/`max_decrease_pct`, `PATCH /establishments/{id}`)
- [x] **Padrão é sugerir, não aplicar.** Só existe o endpoint de sugestão — nada escreve em
      `tariff_rules`; aplicação automática continua fora de escopo (nem tela nem endpoint)
- [ ] Log de auditoria de toda alteração automática, com o motivo — N/A enquanto não existir
      aplicação automática
- [x] Nunca altera tarifa de sessão já iniciada — trivialmente verdade hoje: o serviço só lê e
      devolve sugestões para horas futuras do horizonte de previsão, nunca escreve

### Detecção de anomalias
- [x] Camada de regras determinísticas, sempre ativa: potência 0 por > 30 min com veículo
      conectado · potência acima da nominal · offline por > 3 ciclos · energia acumulada
      regredindo (`ia/app/services/anomalies.py`)
- [ ] Camada estatística: Isolation Forest ou z-score em janela móvel, por carregador e horário —
      não implementada; `ia/requirements.txt` não tem scikit-learn
- [x] Alerta no dashboard com severidade **e a leitura que disparou** anexada
- [ ] Botão de "falso positivo" com o feedback persistido — é o único rótulo real disponível

### Segmentação de clientes
- [ ] K-Means com `StandardScaler`; k escolhido por cotovelo + silhouette e depois **fixado** —
      não implementado (nenhum uso de scikit-learn/KMeans no projeto)
- [ ] Features: hora média de início, desvio, sessões/mês, kWh médio, duração média,
      % em fim de semana, plano ativo
- [ ] Clusters **nomeados**: `carregador_noturno`, `usuario_de_pico`, `cliente_de_passagem`,
      `frota_corporativa` — validados contra os centroides
- [ ] Filtro por segmento no portal do proprietário, para promoção direcionada

### Engenharia
- [ ] Modelos em `/ia/models/`, fora do git — pasta existe (`ia/models/.gitkeep`), sem uso ainda
      (Prophet não é serializado/persistido)
- [ ] Retreino agendado: previsão diária, segmentação semanal. Nunca por requisição — hoje o
      treino roda sob demanda com cache em memória (`_CacheEntry`), não em agenda
- [ ] Todo endpoint devolve `model_version` e `trained_at`
- [x] Cache das previsões — o dashboard não dispara treino (`train_or_get_cached_model`)
- [x] **Fallback obrigatório:** modelo falhou → backend mostra média histórica simples e diz
      que é média histórica (`historical_average_fallback`)

## Plano de execução

Owner: Pessoa 1. Depende de M2 (os 60–90 dias de histórico) e M3 (sessões/tarifas reais).
Ordem pensada por retorno imediato: regras determinísticas de anomalia primeiro (pega a
maioria dos casos e é praticamente grátis), depois previsão, segmentação/precificação por
último — são os itens mais dispensáveis se o tempo apertar (`tasks/README.md`).

1. **Setup do microserviço** — `/ia`, FastAPI separado, conexão **somente leitura** ao mesmo
   Postgres. Nunca escreve em tabela transacional.
2. **Anomalias — camada de regras determinísticas** (implementar primeiro, sempre ligada):
   potência 0 por >30 min com veículo conectado, potência acima da nominal, `offline` por >3
   ciclos de polling, energia acumulada regredindo. Alerta com severidade **e a leitura que
   disparou** anexada — sem evidência, o operador ignora em uma semana.
3. **Anomalias — camada estatística** — Isolation Forest ou z-score em janela móvel por
   carregador/horário; botão de "falso positivo" persistindo o feedback (único rótulo real
   disponível).
4. **Previsão de demanda** — Prophet como padrão; alvo sessões/kWh por hora, 24–48h, por
   estabelecimento; regressores hora/dia da semana/feriado/tipo de estabelecimento; mínimo 4
   semanas de histórico, abaixo disso `insufficient_data`. Backtest com **corte temporal**
   (nunca split aleatório — vaza futuro), MAE/MAPE por faixa horária. Endpoint do mapa de calor
   com rótulo em linguagem natural.
5. **Precificação dinâmica sugerida** — regra sobre a previsão (acima do p80 → sugere aumento,
   abaixo do p20 → redução), limites `max_increase_pct`/`max_decrease_pct` configurados pelo
   proprietário. Padrão é sugerir, não aplicar; aplicação automática só dentro dos limites, com
   log de auditoria; nunca em sessão já iniciada (tarifa é congelada, skill
   `tarifacao-e-sessoes`).
6. **Segmentação de clientes** — K-Means + `StandardScaler`, k escolhido por
   cotovelo+silhouette e depois fixado; features de `ml-previsao-e-anomalias` §4; nomear os
   clusters validando contra os centroides (`carregador_noturno`, `usuario_de_pico`,
   `cliente_de_passagem`, `frota_corporativa`) — cluster com nome numérico não serve para o
   proprietário criar promoção.
7. **Engenharia** — modelos em `/ia/models/` fora do git; retreino agendado (previsão diária,
   segmentação semanal, nunca por requisição); todo endpoint devolve `model_version` e
   `trained_at`; cache das previsões; fallback obrigatório para média histórica simples (com
   aviso) se o modelo falhar — o portal não pode quebrar por causa disso.

## Critérios de aceite

- Com os 90 dias gerados em M2, a previsão roda e o mapa de calor aparece no dashboard.
- MAE do backtest reportado no README de `/ia` — número real, medido.
- Injetar o cenário "falha de equipamento" do simulador gera alerta em menos de um ciclo de retreino
  (a camada de regras é imediata).
- Os clusters recebem nomes que fazem sentido ao olhar os centroides.
- Derrubar o serviço de IA não quebra nenhuma tela do portal do proprietário.

## Armadilhas

- Split aleatório em série temporal vaza futuro no treino: métrica linda, previsão inútil.
- Alerta sem a evidência anexada é ignorado pelo operador em uma semana.
