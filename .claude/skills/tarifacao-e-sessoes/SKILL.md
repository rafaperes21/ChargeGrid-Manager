---
name: tarifacao-e-sessoes
description: Regras de cálculo de tarifa dinâmica, planos de assinatura, fila prioritária e fechamento financeiro de sessão de carregamento. Use ao implementar o motor de tarifação, o CRUD de tarifas do proprietário, a tela de sessão em andamento, os relatórios financeiros ou a fatura corporativa.
---

# Tarifação, sessões e planos

## 1. Princípio inegociável

**A tarifa é congelada no início da sessão.** O horário de início determina a faixa aplicada e
ela não muda mesmo que a sessão atravesse a virada para outra faixa. Isso evita disputa com o
cliente e simplifica auditoria.

Grave em `charging_sessions` um **snapshot** dos valores aplicados: `tariff_rate_applied`,
`plan_discount_pct`, `free_minutes_applied`, `tariff_rule_id`. Nunca recalcule um extrato
antigo lendo a tabela de tarifas atual — ela muda, e o histórico tem que ser reproduzível.

## 2. Faixas de horário

```
peak        pico          — R$/kWh mais caro
off_peak    fora de pico
overnight   madrugada     — mais barato
```

Definidas pelo proprietário como `(dias_da_semana, hora_inicio, hora_fim, preco_kwh)` em
**horário local (America/Sao_Paulo)**, persistidas em UTC. Faixas podem cruzar a meia-noite
(ex.: 23h → 06h) — trate como dois intervalos ou compare com lógica circular; é onde o bug
aparece.

Validação obrigatória no CRUD: as faixas de um mesmo dia **não podem se sobrepor** e devem
cobrir 24 h. Se houver buraco, aplique a tarifa `off_peak` como fallback e registre no log.

## 3. Ordem de aplicação (não inverta)

```
1. energia_kwh × tarifa_da_faixa            → bruto
2. − minutos gratuitos convertidos em kWh   → regra promocional (ex.: 1ª meia hora grátis fim de semana)
3. − desconto do plano (%)                  → 15 % mensal, 25 % trimestral
4. − consumo abatido da franquia            → franquia é abatida em kWh, antes de virar dinheiro
5. = valor_final
```

O desconto do plano incide sobre o valor **já descontado da promoção**, nunca acumulado sobre
o bruto. Se as duas regras se aplicarem, aplique as duas nessa ordem — está definido, não é
ambíguo.

## 4. Planos

| Plano | Mensalidade | Franquia | Desconto | Fila |
|---|---|---|---|---|
| `avulso` | — | — | 0 % | prioridade 0 |
| `mensal` | sim | kWh incluídos | 15 % | prioridade 1 |
| `trimestral` | sim | franquia maior | 25 % | prioridade 2 |

Franquia **não acumula** entre ciclos (padrão de mercado; se o time decidir diferente,
documentar aqui). Consumo acima da franquia é cobrado à tarifa da faixa com o desconto do plano.

O trimestral inclui relatório de sustentabilidade personalizado (ver §7).

## 5. Fila inteligente

Ordenação: `prioridade_do_plano DESC`, depois `entrou_na_fila_em ASC`.
Nunca desempate por outro critério — o cliente vê a posição em tempo real e qualquer
reordenação inexplicada vira reclamação.

Regras:
- Vaga liberou → notifica o primeiro da fila e **reserva por 15 min**. Não respondeu, cai
  para o fim da fila do seu tier e chama o próximo.
- Reserva antecipada (15 min) ocupa a vaga logicamente — ela não entra na oferta da fila.
- Um cliente tem no máximo uma posição ativa na fila.

## 6. Ciclo de vida da sessão

```
pending → active → finished
                 ↘ error
```

- `pending`: RFID aproximado, aguardando o carregador reportar potência > 0.
  Timeout de 5 min sem potência → `error`, sem cobrança.
- `active`: acumula `energy_kwh` a cada leitura do polling. Como o polling é a cada 1–5 min,
  integre a potência por trapézio entre leituras — não multiplique a última leitura pelo
  intervalo inteiro.
- `finished`: desconexão detectada (potência 0 por N leituras consecutivas) ou encerramento
  manual. Calcula o valor conforme §3 e gera recibo.
- `error`: sessão sem cobrança + alerta no dashboard do proprietário.

Idempotência: o polling pode repetir leituras. Use o timestamp da leitura do SEMS+ como chave,
não o momento em que o backend processou.

## 7. Cálculo de sustentabilidade

```
km_equivalentes = energia_kwh / consumo_medio_veiculo_kwh_por_km   # default 0,16 kWh/km
co2_evitado_kg  = km_equivalentes × fator_emissao_combustao        # default 0,12 kg CO₂/km
```

Ambos os fatores ficam em config, não hardcoded — a matriz elétrica brasileira muda e o número
precisa ser defensável. O relatório deve dizer qual premissa usou.

## 8. Modo empresarial

Faturas consolidadas agregam sessões por `company_id` no ciclo, com rateio por
`department` ou `vehicle`. A fatura é um documento **imutável**: gerada uma vez, guarda os
próprios totais. Correção se faz por nota de ajuste, não editando a fatura.
