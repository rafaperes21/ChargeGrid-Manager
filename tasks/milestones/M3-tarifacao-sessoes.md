# M3 — Motor de tarifação e sessões

Status: não iniciado
Responsável: —
Depende de: M1, M2
Skill: `.claude/skills/tarifacao-e-sessoes/`

## Objetivo

O coração financeiro do produto. Tudo que envolve dinheiro passa por aqui, e erro aqui é
prejuízo real ou cliente cobrado a mais. **É o milestone que mais precisa de teste.**

## Escopo

### Tarifas
- [ ] CRUD de `tariff_rules`: faixas pico / fora de pico / madrugada por dia da semana
- [ ] Validação: faixas não se sobrepõem e cobrem 24 h; fallback documentado se houver buraco
- [ ] Faixas que cruzam a meia-noite tratadas corretamente
- [ ] Regras especiais: desconto por plano, minutos gratuitos condicionais
      (ex.: primeira meia hora grátis nos fins de semana)
- [ ] Definição em horário local (`America/Sao_Paulo`), persistência em UTC

### Sessões
- [ ] Máquina de estados `pending → active → finished | error`
- [ ] Abertura por RFID; timeout de 5 min sem potência → `error` sem cobrança
- [ ] Acúmulo de kWh a partir das leituras do polling
- [ ] Detecção de fim por potência zerada em N leituras consecutivas
- [ ] Fechamento: aplica a ordem de cálculo da skill (bruto → promoção → desconto de plano →
      franquia → valor final) e grava **snapshot** da tarifa aplicada
- [ ] Geração de recibo digital

### Planos e fila
- [ ] Assinatura, franquia em kWh, descontos de 15 % / 25 %
- [ ] Fila: ordenação por prioridade de plano, depois ordem de chegada
- [ ] Reserva de 15 min ao liberar vaga; expirou → volta ao fim do próprio tier
- [ ] Reserva antecipada de 15 min retira a vaga da oferta da fila

## Critérios de aceite

- Suite de testes unitários cobrindo, no mínimo:
  - sessão que atravessa a virada de faixa mantém a tarifa do início
  - faixa cruzando a meia-noite calcula certo
  - promoção + desconto de plano aplicados na ordem correta (não acumulados sobre o bruto)
  - franquia abatida em kWh antes da conversão em dinheiro
  - franquia excedida cobra o excedente com desconto do plano
  - fila: assinante trimestral entra depois de um avulso e é atendido antes
  - sessão em `error` não gera cobrança
- Extrato de um mês fechado permanece idêntico depois de alterar a tabela de tarifas.
- Sessão completa ponta a ponta com o simulador: abre por RFID, acumula, fecha, valor confere
  com o cálculo manual.

## Armadilhas

- Recalcular extrato antigo lendo a tarifa atual é o bug clássico deste domínio. Snapshot.
- `float` em dinheiro. `Decimal`, sempre.
