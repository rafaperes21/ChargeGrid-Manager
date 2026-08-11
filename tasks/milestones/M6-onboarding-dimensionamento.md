# M6 — Onboarding, dimensionamento e orçamento em PDF

Status: não iniciado
Responsável: —
Depende de: M4
Skill: `.claude/skills/dimensionamento-hca-g2/`

## Objetivo

O primeiro contato do proprietário com o sistema e o principal diferencial comercial:
ele entra sem saber o que comprar e sai com um orçamento para levar à GoodWe.

## Escopo

- [ ] Fluxo guiado em etapas: tipo de estabelecimento → nº de vagas → carga disponível (kW) →
      fase (mono/trifásica) → tensão
- [ ] Texto de ajuda explicando que a carga pedida é a **sobressalente**, não a demanda
      contratada total — é o erro de preenchimento mais comum
- [ ] `services/sizing.py`: cálculo de quantos HCA G2 cabem, aplicando margem de segurança
      (80 %) e fator de simultaneidade por tipo de estabelecimento
- [ ] `services/charger_catalog.py`: constantes dos modelos GW7K / GW11K / GW22K em um só lugar
- [ ] Recomendação de modelo, com justificativa em texto (por que 2× GW11K em vez de 1× GW22K)
- [ ] Caso `max_chargers == 0`: informar a carga mínima necessária, não devolver erro seco
- [ ] Custo estimado de aquisição + instalação
- [ ] Payback com base na receita projetada por sessão
- [ ] Premissas (kWh médio, sessões/dia, custo da energia) visíveis e **editáveis**
- [ ] Geração do PDF do orçamento
- [ ] Rodapé obrigatório: estimativa preliminar, não substitui projeto elétrico assinado por
      profissional habilitado (NBR 5410 / NBR 17019)
- [ ] Ao concluir, criar o estabelecimento e os carregadores já configurados

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
