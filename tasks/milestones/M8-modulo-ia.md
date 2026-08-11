# M8 — Módulo de IA/ML

Status: não iniciado
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
- [ ] Prophet como padrão (sazonalidade diária e semanal + feriados são a estrutura do dado)
- [ ] Alvo: sessões (ou kWh) por hora, próximas 24–48 h, por estabelecimento
- [ ] Regressores: hora, dia da semana, feriado nacional, tipo de estabelecimento
- [ ] Mínimo de 4 semanas de histórico; abaixo disso, `insufficient_data`
- [ ] Endpoint consumido pelo dashboard: mapa de calor hora × dia com intervalo de confiança
- [ ] Rótulo em linguagem natural: "amanhã das 18h às 20h: alta demanda esperada"
- [ ] Backtest com **corte temporal** (nunca split aleatório), MAE e MAPE por faixa horária

### Precificação dinâmica sugerida
- [ ] Regra sobre a previsão: acima do p80 histórico → sugere aumento; abaixo do p20 → redução
- [ ] Limites `max_increase_pct` / `max_decrease_pct` configurados pelo proprietário
- [ ] **Padrão é sugerir, não aplicar.** Aplicação automática só dentro dos limites configurados
- [ ] Log de auditoria de toda alteração automática, com o motivo
- [ ] Nunca altera tarifa de sessão já iniciada

### Detecção de anomalias
- [ ] Camada de regras determinísticas, sempre ativa (implementar primeiro — pega a maioria):
      potência 0 por > 30 min com veículo conectado · potência acima da nominal ·
      offline por > 3 ciclos · energia acumulada regredindo
- [ ] Camada estatística: Isolation Forest ou z-score em janela móvel, por carregador e horário
- [ ] Alerta no dashboard com severidade **e a leitura que disparou** anexada
- [ ] Botão de "falso positivo" com o feedback persistido — é o único rótulo real disponível

### Segmentação de clientes
- [ ] K-Means com `StandardScaler`; k escolhido por cotovelo + silhouette e depois **fixado**
- [ ] Features: hora média de início, desvio, sessões/mês, kWh médio, duração média,
      % em fim de semana, plano ativo
- [ ] Clusters **nomeados**: `carregador_noturno`, `usuario_de_pico`, `cliente_de_passagem`,
      `frota_corporativa` — validados contra os centroides
- [ ] Filtro por segmento no portal do proprietário, para promoção direcionada

### Engenharia
- [ ] Modelos em `/ia/models/`, fora do git
- [ ] Retreino agendado: previsão diária, segmentação semanal. Nunca por requisição
- [ ] Todo endpoint devolve `model_version` e `trained_at`
- [ ] Cache das previsões — o dashboard não dispara treino
- [ ] **Fallback obrigatório:** modelo falhou → backend mostra média histórica simples e diz
      que é média histórica. O portal não quebra porque o Prophet não convergiu

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
