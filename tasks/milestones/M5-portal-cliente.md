# M5 — Portal do Cliente

Status: em andamento
Responsável: —
Depende de: M1, M3
Skill: `.claude/skills/ui-dois-portais/`

## Objetivo

Mobile-first. Usado em pé, no estacionamento, com pressa. Uma informação principal por tela.

## Escopo

### Cadastro e autenticação
- [ ] Login por e-mail/senha e Google — só e-mail/senha implementado, sem Google no
      `frontend-cliente` (o Google OAuth existe no backend e no portal do proprietário)
- [ ] Cadastro do modelo do veículo (alimenta estimativa de % de bateria e tempo restante)
- [ ] Cadastro de método de pagamento
- [ ] Geração do RFID virtual (QR code / número de cartão) para o proprietário cadastrar
      fisicamente no HCA G2 via SEMS+

### Sessão em andamento (prioridade máxima — tela mais vista do produto)
- [x] kWh carregados e valor acumulado — `SessaoPage.jsx` consome `GET /sessions/current`.
      Tarifa vigente não é mostrada isoladamente (o valor acumulado já reflete); `amount_due`
      só existe quando a sessão fecha, então enquanto `active` o backend expõe
      `estimated_amount_due` (novo campo, `services/sessions.estimate_live_amount`) — mesma
      tarifa/plano/franquia que valeriam se a sessão fechasse agora, rotulado "(estimado)" na
      tela, nunca extrapolado no frontend
- [ ] % estimado da bateria, tempo estimado restante — sem cadastro de modelo de veículo (item
      abaixo) não há base pra estimar, então não implementado ainda
- [ ] Hierarquia visual: valor e tempo restante grandes; kWh e tarifa secundários — layout
      atual é simples (status + tempo decorrido + valor + kWh), não redesenhado ainda
- [ ] Sem modelo de veículo cadastrado → mostra kWh e **omite** o % de bateria — N/A por ora
      (bateria ainda não é estimada, ver acima)
- [ ] Barra de progresso interpolada localmente; kWh e R$ só com dado confirmado
- [ ] Notificação push ao terminar

### Planos de assinatura
- [ ] Comparativo avulso / mensal (15 %, fila prioritária) / trimestral (25 %, prioridade máxima)
      — não há tela equivalente no portal do cliente; depende também de `services/plans.py`
      (M3), deliberadamente em espera enquanto o time decide o modelo com o professor
- [ ] Contratação e troca de plano confirmadas na interface (nunca pelo chat)

### Mapa de disponibilidade
- [x] Vagas livres em tempo real e potência disponível de cada carregador (`MapaPage.jsx`
      consome a API real)
- [ ] Reserva com 15 min de antecedência
- [ ] Link de navegação via Google Maps

### Fila inteligente
- [x] Entrar na fila quando tudo estiver ocupado — `FilaPage.jsx` consome `GET /queue/mine`
      (a ação de entrar na fila em si ainda não tem botão na tela, só a leitura de posição)
- [x] Posição em tempo real, grande e acima da dobra
- [ ] Notificação quando a vaga liberar — sem push; a janela de 15 min em contagem regressiva
      está implementada (`FilaPage.jsx`), só falta a notificação em si

### Histórico e sustentabilidade
- [x] Lista de sessões: data, energia, valor — `HistoricoPage.jsx` consome `GET /sessions/mine`
      (novo endpoint). Local/duração não exibidos ainda (duração é derivável de
      `started_at`/`ended_at`, local seria o nome do estabelecimento — falta só exibir)
- [x] Recibo digital — expandir uma sessão finalizada mostra a decomposição completa
      (bruto → promoção → desconto → franquia → total) via `GET /sessions/{id}/receipt`,
      que ganhou os campos da decomposição (antes só devolvia o snapshot, sem os valores
      intermediários em R$)
- [ ] Gráfico de consumo mensal
- [ ] Relatório mensal de sustentabilidade: kWh → km equivalentes → kg de CO₂ evitados,
      com comparativo do mês anterior, premissas declaradas e compartilhamento social

### Modo empresarial (cortável se o tempo apertar)
- [ ] Cadastro de frota: veículos e funcionários
- [ ] Painel corporativo com rateio por departamento ou veículo
- [ ] Fatura única mensal consolidada

## Plano de execução

Owner: Pessoa 2 (frontend). Depende de M1 e M3, mesma lógica de adiantar com mock do M4.
Mobile-first do início — não adaptar depois de construir pensando em desktop.

1. **Cadastro e autenticação** — login e-mail/senha + Google, cadastro do modelo do veículo
   (alimenta % de bateria e tempo restante), método de pagamento, geração do RFID virtual
   (QR/número) para o proprietário cadastrar no SEMS+.
2. **Sessão em andamento** (prioridade máxima — tela mais vista do produto, fazer primeiro) —
   hierarquia visual: valor acumulado e tempo restante grandes, kWh e tarifa secundários
   (skill `ui-dois-portais` §4). Sem veículo cadastrado → mostrar kWh e **omitir** % de
   bateria, nunca estimar sem o dado. Barra de progresso interpola localmente entre fetches;
   kWh e R$ só com dado confirmado — nunca extrapolar dinheiro. Notificação push ao terminar.
3. **Mapa de disponibilidade** — vagas livres e potência disponível em tempo (quase) real,
   reserva com 15 min de antecedência, link Google Maps.
4. **Fila inteligente** — posição em tempo real acima da dobra, grande (é a única informação
   que importa para quem está na fila); notificação ao liberar, com o countdown de 15 min
   visível.
5. **Planos de assinatura** — comparativo avulso/mensal/trimestral; contratação e troca sempre
   confirmadas na interface, nunca pelo chat (isso é regra também para M7).
6. **Histórico e sustentabilidade** — lista de sessões, recibo digital (dados que um reembolso
   corporativo exige: data, local, kWh, valor, tarifa), gráfico de consumo mensal, relatório de
   sustentabilidade usando as fórmulas de `km_equivalentes`/`co2_evitado_kg` da skill
   `tarifacao-e-sessoes` §7 (premissas configuráveis, declaradas no relatório).
7. **Modo empresarial** (cortável se o tempo apertar) — cadastro de frota, painel de rateio por
   departamento/veículo, fatura única consolidada.

## Critérios de aceite

- A tela de sessão em andamento é legível de relance, numa tela de celular, sem zoom.
- Com o simulador rodando uma sessão, os números avançam sozinhos e o valor final bate com o
  cálculo do backend.
- A fila mostra a posição correta com dois clientes de planos diferentes aguardando.
- Recibo contém tudo o que um reembolso corporativo exige: data, local, kWh, valor, tarifa.

## Armadilhas

- Não estime % de bateria sem o modelo do veículo. Estimativa errada de "quanto falta" é a
  reclamação nº 1 de app de recarga.
- Extrapolar valor em R$ entre fetches faz o cliente ver um número e ser cobrado outro.
