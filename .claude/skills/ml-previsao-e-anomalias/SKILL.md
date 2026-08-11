---
name: ml-previsao-e-anomalias
description: Modelos do microserviço de IA — previsão de demanda (Prophet/LSTM), precificação dinâmica sugerida, detecção de anomalias em carregadores e segmentação de perfil de clientes. Use ao implementar, treinar ou avaliar qualquer modelo em /ia, ou ao expor essas previsões no dashboard do proprietário.
---

# Módulo de IA

Microserviço FastAPI separado (`/ia`). Lê o mesmo Postgres em modo leitura, expõe endpoints que
o backend principal consome. **Nunca escreve nas tabelas transacionais.**

Regra geral: se o modelo não tem dados suficientes, ele devolve `insufficient_data`, não um
palpite. Um número errado no dashboard do proprietário custa mais caro que um "ainda coletando
dados".

## 1. Previsão de demanda

**Alvo:** número de sessões (ou kWh) por hora, para as próximas 24–48 h, por estabelecimento.

**Modelo:** Prophet como padrão. Ele lida nativamente com sazonalidade semanal e diária e com
feriados, que é exatamente a estrutura desses dados. LSTM só se sobrar tempo e houver ganho
mensurável — quase nunca há, neste volume.

**Features/regressores:** hora do dia, dia da semana, feriado nacional, e (se disponível) o
tipo de estabelecimento. Fim de semana em shopping tem comportamento oposto ao de empresa.

**Dados mínimos:** 4 semanas de histórico. Abaixo disso, devolva `insufficient_data`. Por isso
o simulador precisa gerar 60–90 dias retroativos (ver skill `integracao-sems-simulador`).

**Saída para o dashboard:** mapa de calor hora × dia, com intervalo de confiança. Rotule os
picos em linguagem natural: "amanhã das 18h às 20h: alta demanda esperada".

**Validação:** backtest com corte temporal (`cutoff` móvel), MAE e MAPE por faixa horária.
Nunca faça split aleatório em série temporal — vaza futuro no treino e o resultado fica lindo
e falso.

## 2. Precificação dinâmica sugerida

Não é um modelo próprio — é uma **regra sobre a previsão**:

```
se demanda_prevista > p80(demanda_histórica_daquela_hora):
    sugerir tarifa × (1 + ajuste), limitado a max_increase_pct
se demanda_prevista < p20(...):
    sugerir tarifa × (1 − ajuste), limitado a max_decrease_pct
```

Limites (`max_increase_pct`, `max_decrease_pct`) são configurados pelo proprietário.
**Modo padrão é sugerir, não aplicar.** Aplicação automática só dentro dos limites que ele
configurou explicitamente, e toda alteração automática vai para log de auditoria com o motivo.

Nunca aplique ajuste a uma sessão já iniciada — a tarifa é congelada no início (ver skill
`tarifacao-e-sessoes`).

## 3. Detecção de anomalias

**Escopo:** por carregador, sobre a série de `charger_readings`.

Duas camadas, e a primeira pega a maioria dos casos:

*Regras determinísticas* (implementar primeiro, sempre ligadas):
- potência 0 por > 30 min com veículo conectado → possível falha
- potência acima da nominal do modelo → erro de medição ou defeito
- carregador `offline` por > 3 ciclos de polling
- energia acumulada do dispositivo regredindo → reset ou corrupção de dado

*Modelo estatístico* (complementa): Isolation Forest ou z-score sobre janela móvel do perfil
de consumo daquele carregador naquele horário. Aprende o que é normal para *aquele* ponto.

Anomalia gera alerta no dashboard com severidade e a leitura que disparou. Alerta sem
evidência anexada é ignorado pelo operador em uma semana. Inclua um botão de "falso positivo"
e guarde esse feedback — é o único rótulo real que vocês vão ter.

## 4. Segmentação de clientes

**Método:** K-Means sobre features agregadas por cliente. Padronize antes (`StandardScaler`),
escolha k pelo método do cotovelo + silhouette — e depois **fixe k** e nomeie os clusters.
Cluster com nome numérico não serve para o proprietário criar promoção.

Features: hora média de início, desvio da hora de início, sessões/mês, kWh médio por sessão,
duração média, % de sessões em fim de semana, plano ativo.

Rótulos esperados (validar contra os centroides antes de usar):
`carregador_noturno`, `usuario_de_pico`, `cliente_de_passagem`, `frota_corporativa`.

Uso: o proprietário filtra por segmento para criar promoção direcionada — tipicamente desconto
para migrar `usuario_de_pico` para fora de pico, o que também alivia a instalação.

## 5. Engenharia

- Modelos treinados em `/ia/models/` — **fora do git** (ver `.gitignore`).
- Retreino agendado (diário para previsão, semanal para segmentação), não a cada requisição.
- Todo endpoint devolve `model_version` e `trained_at`. Sem isso é impossível depurar uma
  previsão estranha.
- Cache das previsões: o dashboard não pode disparar treino.
- Fallback obrigatório: se o modelo falhar, o backend mostra média histórica simples e diz
  que é média histórica. O portal não pode quebrar porque o Prophet não convergiu.
