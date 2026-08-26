# M6 — Onboarding, dimensionamento e orçamento em PDF

Status: em andamento
Responsável: —
Depende de: M4
Skill: `.claude/skills/dimensionamento-hca-g2/`

## Objetivo

O primeiro contato do proprietário com o sistema e o principal diferencial comercial:
ele entra sem saber o que comprar e sai com um orçamento para levar à GoodWe.

## Escopo

- [x] Fluxo guiado em etapas: tipo de estabelecimento → nº de vagas → carga disponível (kW) →
      fase (mono/trifásica) → tensão (`OnboardingPage.jsx`)
- [ ] Texto de ajuda explicando que a carga pedida é a **sobressalente**, não a demanda
      contratada total — é o erro de preenchimento mais comum
- [x] `services/sizing.py`: cálculo de quantos HCA G2 cabem, aplicando margem de segurança
      (80 %) e fator de simultaneidade por tipo de estabelecimento (implementado em
      `services/dimensionamento.py`)
- [x] `services/charger_catalog.py`: constantes dos modelos GW7K / GW11K / GW22K em um só lugar
- [x] Recomendação de modelo, com justificativa em texto (por que 2× GW11K em vez de 1× GW22K)
- [x] Caso `max_chargers == 0`: informar a carga mínima necessária, não devolver erro seco
- [x] Custo estimado de aquisição + instalação
- [ ] Payback com base na receita projetada por sessão — `budget` calcula com uma tarifa
      assumida fixa (`_TARIFA_ASSUMIDA_PARA_PAYBACK`), já que `preco_unitario` não veio da GoodWe
- [ ] Premissas (kWh médio, sessões/dia, custo da energia) visíveis e **editáveis** — não
      encontrado na tela; endpoint não aceita essas premissas como parâmetro
- [x] Geração do PDF do orçamento — gerado no cliente com `jspdf`
      (`OnboardingPage.jsx`, função `downloadPdf`), não no backend
- [x] Rodapé obrigatório: estimativa preliminar, não substitui projeto elétrico assinado por
      profissional habilitado (NBR 5410 / NBR 17019) — presente no PDF gerado
- [ ] Ao concluir, criar o estabelecimento e os carregadores já configurados — o endpoint
      `/onboarding/dimensionamento` apenas calcula e retorna, não persiste nada

## Plano de execução

Owner: cálculo e PDF na Pessoa 1 (backend), wizard/tela de resultado na Pessoa 2 — decisão do
`plano-2-pessoas.md` de manter a regra de dimensionamento em Python/`Decimal`, testável, com o
frontend só acionando o download. Depende de M4 (o wizard vive dentro do portal do
proprietário).

1. **`services/charger_catalog.py`** — constantes dos modelos GW7K/GW11K/GW22K num só lugar
   (potência, fase, corrente). Marcar os valores `TODO(datasheet)` da skill
   `dimensionamento-hca-g2` §2 — não hardcode número não confirmado em regra de negócio.
2. **`services/sizing.py`** — fórmulas mono (`P = V×I×FP/1000`) e trifásica
   (`P = √3×V×I×FP/1000`, FP=1,0), seleção de modelo (§3 da skill: GW22K só se
   `available_power_kw >= 2×P_GW22K`, senão GW11K; empate → GW11K com justificativa),
   `max_chargers` com margem de segurança 80% e fator de simultaneidade por tipo de
   estabelecimento (§4). Caso `max_chargers == 0` → devolver a carga mínima necessária, não
   erro seco.
3. **Fluxo guiado do onboarding** (Pessoa 2, dentro de M4) — etapas tipo de estabelecimento →
   vagas → carga disponível → fase → tensão, com texto de ajuda explícito sobre "carga
   sobressalente, não demanda contratada total" (erro de preenchimento mais comum).
4. **Custo e payback** — `capex`/`receita_mes`/`payback_meses` (skill §5) com as premissas
   padrão (kWh médio 22, sessões/dia por tipo, custo de energia, % de instalação) exibidas e
   editáveis no PDF; recalcular na hora ao mudar premissa.
5. **Geração do PDF** — reportlab/weasyprint no backend; rodapé obrigatório (estimativa
   preliminar, não substitui projeto elétrico assinado — NBR 5410/NBR 17019); "sob consulta" no
   lugar do preço enquanto `preco_unitario` não vier da GoodWe (nunca inventar).
6. **Ao concluir** — criar `establishment` e os `chargers` já configurados a partir do
   resultado.
7. **Testes unitários de `sizing.py`** — os três tipos de estabelecimento × as duas fases,
   reproduzindo as fórmulas da skill à mão para conferir.

## Critérios de aceite

- Entrada "44 kW, trifásico, shopping, 20 vagas" produz um resultado coerente, e a conta pode
  ser refeita à mão a partir das fórmulas da skill.
- Mudar uma premissa recalcula o payback na hora.
- O PDF abre, está em português, tem os números, as premissas e o rodapé legal.
- Testes unitários de `sizing.py` para os três tipos de estabelecimento e as duas fases.

## Bloqueio conhecido

**Preço unitário dos modelos não está definido.** Enquanto a GoodWe não fornecer, o PDF imprime
"sob consulta" no lugar do valor e o payback fica indisponível, com aviso explícito. Não invente
preço em documento que o proprietário vai levar para uma reunião comercial.

O mesmo vale para as potências nominais em rede brasileira 220/380 V — estão marcadas como
`TODO(datasheet)` na skill. Confirmar antes de considerar este milestone fechado.
