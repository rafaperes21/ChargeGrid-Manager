---
name: dimensionamento-hca-g2
description: Regras de dimensionamento elétrico e seleção de modelo do carregador GoodWe HCA G2 (GW7K / GW11K / GW22K). Use ao implementar a calculadora de onboarding do proprietário, o gerador de orçamento em PDF, o cálculo de payback, ou o system prompt do chatbot técnico. Contém as fórmulas de potência mono/trifásica, o fator de simultaneidade e os limites de carga.
---

# Dimensionamento do HCA G2

## 1. Dados de entrada do onboarding

| Campo | Tipo | Observação |
|---|---|---|
| `establishment_type` | enum: `shopping`, `parking`, `company` | afeta o perfil de simultaneidade |
| `parking_spots` | int > 0 | teto físico de carregadores |
| `available_power_kw` | Decimal | carga elétrica **disponível para EV**, não a demanda contratada total |
| `phase` | enum: `single_phase`, `three_phase` | trava quais modelos são elegíveis |
| `voltage` | Decimal | padrão BR: 220 V (F-N) mono, 380 V (F-F) tri |

Erro comum: o proprietário informa a demanda contratada total do prédio. Pergunte
explicitamente pela **carga sobressalente**, e aplique margem de segurança (§4).

## 2. Fórmulas

Monofásico:
```
P(kW) = V × I × FP / 1000
```

Trifásico:
```
P(kW) = √3 × V × I × FP / 1000
```

Para carregamento AC de VE assume-se **FP = 1,0** (o OBC do veículo é corrigido).
Não introduza FP < 1 nas contas sem justificar.

Referência rápida (arredondada):

| Modelo | Fase | Corrente | Potência nominal |
|---|---|---|---|
| GW7K | Monofásico | 32 A | ~7,4 kW |
| GW11K | Trifásico | 16 A | ~11 kW |
| GW22K | Trifásico | 32 A | ~22 kW |

> `TODO(datasheet)` — os valores acima são as classes comerciais padrão (base 230/400 V).
> Em rede brasileira 220/380 V a potência real cai proporcionalmente
> (ex.: √3 × 380 × 32 ≈ 21,1 kW, não 22 kW). **Confirmar no datasheet oficial da GoodWe
> antes de imprimir qualquer número em orçamento entregue ao proprietário.**
> O código deve ler essas constantes de `backend/app/services/charger_catalog.py`,
> nunca hardcoded em regra de negócio.

## 3. Seleção de modelo

```
se phase == single_phase:
    único elegível → GW7K
se phase == three_phase:
    GW22K se available_power_kw >= 2 × P_GW22K   (permite ao menos 2 pontos)
    senão GW11K
```

Regra prática: um único carregador de 22 kW numa entrada apertada é pior negócio que dois de
11 kW — dobra a ocupação de vagas e a receita, e quase nenhum VE do mercado brasileiro aceita
mais de 11 kW em AC. **Ao empatar, recomende o GW11K e explique isso.**

## 4. Quantidade máxima de carregadores

```
usable_kw     = available_power_kw × SAFETY_MARGIN      # SAFETY_MARGIN = 0.80
max_by_power  = floor(usable_kw / (P_modelo × DIVERSITY_FACTOR))
max_chargers  = min(max_by_power, parking_spots)
```

`DIVERSITY_FACTOR` (fator de simultaneidade) por tipo de estabelecimento:

| Tipo | Fator | Razão |
|---|---|---|
| `shopping` | 0,60 | rotatividade alta, permanência curta, picos concentrados |
| `parking` | 0,70 | permanência média |
| `company` | 0,85 | todos chegam e plugam no mesmo horário — pouca diversidade |

O HCA G2 faz **controle dinâmico de carga** internamente, então o somatório nominal pode
exceder a entrada com segurança — é isso que o fator de simultaneidade representa. Mas o
dashboard deve alertar **antes** do fusível atuar (limiar em 90 % do `available_power_kw`).

Se `max_chargers == 0`, não devolva erro seco: informe qual é a carga mínima necessária para
um único ponto do menor modelo elegível.

## 5. Custo e payback

```
capex        = (preco_unitario × qtd) + custo_instalacao_estimado
receita_mes  = sessoes_dia_estimadas × qtd × kwh_medio_sessao × (tarifa - custo_energia) × 30
payback_meses = capex / receita_mes
```

Premissas padrão, todas **exibidas no PDF** e editáveis pelo proprietário:

| Premissa | Default |
|---|---|
| `kwh_medio_sessao` | 22 kWh |
| `sessoes_dia_estimadas` por ponto | shopping 3,5 · parking 2,5 · company 1,5 |
| `custo_energia` (tarifa da concessionária) | R$ 0,85/kWh |
| `custo_instalacao_estimado` | 35 % do capex de equipamento |

> `TODO(datasheet)` — `preco_unitario` por modelo precisa vir da GoodWe. Até lá, o PDF deve
> imprimir "sob consulta" em vez de um número inventado. **Nunca chute preço em documento
> que o proprietário vai levar para uma reunião comercial.**

O orçamento deve declarar em rodapé que é uma estimativa preliminar e não substitui projeto
elétrico assinado por profissional habilitado (ART/NBR 5410 e NBR 17019).

## 6. Ao usar isto no chatbot do proprietário

Injete §2, §3 e §4 no system prompt. Duas regras de comportamento:
- Se faltar fase ou carga disponível, **pergunte** — não assuma trifásico.
- Diante de pergunta que exige projeto elétrico (bitola de cabo, disjuntor, aterramento,
  proteção DR), dê a orientação geral e encaminhe para engenheiro habilitado.
