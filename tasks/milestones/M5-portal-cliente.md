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
- [ ] Cadastro do modelo do veículo pelo próprio cliente — ainda não existe UI de
      onboarding/cadastro pra isso; hoje só é populado via seed de demo. O campo
      `User.vehicle_model` já existe e já alimenta a estimativa de bateria (ver abaixo), só
      falta a tela de auto-cadastro pra um cliente real
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
- [x] **% estimado da bateria, tempo estimado restante** (28/08/2026) — resolvido reaproveitando
      `User.vehicle_model` (já existia) com uma tabela real de capacidade (kWh) dos modelos
      já cadastrados na demo (`services/vehicle_battery.py`: BYD Dolphin/Dolphin Mini, GWM
      Ora 03, Volvo EX30, Renault Kwid E-Tech — especificação pública do fabricante, não
      inventada). `GET /sessions/current` devolve `battery_pct_estimate`/
      `estimated_minutes_remaining`, sempre assumindo que a sessão começou com o veículo
      vazio (0%) — única forma de estimar sem telemetria real da bateria do carro, por isso
      a tela rotula como "estimado". Verificado ao vivo: BYD Dolphin Mini (30,008 kWh),
      0,090 kWh entregues, 3,5 kW atual → 0,3% e "~8h33 restantes", conferido na mão.
- [ ] Hierarquia visual: valor e tempo restante grandes; kWh e tarifa secundários — layout
      atual é simples (status + tempo decorrido + valor + kWh + bateria), não redesenhado ainda
- [x] Sem modelo de veículo cadastrado → mostra kWh e **omite** o % de bateria —
      `estimate_battery_status` devolve `(None, None)` pra modelo fora do catálogo, a tela
      só renderiza o bloco de bateria quando `battery_pct_estimate` existe
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

## Extra — Modo demonstração e passo a passo amigável (28/08/2026)

Pedido explícito do usuário: simular um cliente usando o produto de verdade (RFID → sessão →
carregando → tempo/preço) pra gravar demo, e deixar a jornada mais fácil de entender.

- **"Simular leitura do cartão RFID"** (`SessaoPage.jsx`, botão em `NoActiveSession`) — chama
  `POST /sessions/start` de verdade contra um carregador livre real, achado percorrendo
  `GET /establishments`/`GET /chargers`. **Não é encenação**: é a mesma sessão real que um
  RFID físico abriria, decisão consciente pra não inventar dado (alternativa descartada:
  animação puramente client-side com números fabricados).
  **Depende do worker de polling estar rodando de verdade** (`python -m
  app.integracoes.polling`, não sobe sozinho em nenhum script — mesmo gap que o
  `docs/status-atual.md` já documentava em M9, "simulador não roda continuamente") — sem
  isso a sessão fica presa em `pending` pra sempre, sem leitura de potência chegando.
  Testado ao vivo com `POLL_INTERVAL_SECONDS=10` (mais rápido que o default de 60s, só pra
  gravação): sessão real criada, `pending` → `active` em ~1 leitura, energia/valor/bateria/
  tempo restante todos avançando sozinhos com dado do backend.
- **`SessionStepper`** — indicador visual de 4 passos (Aproximar cartão → Conectando →
  Carregando → Concluído) no topo de toda a jornada de `SessaoPage.jsx` (sem sessão, pending,
  active, recibo final), mesmo espírito do carrossel de onboarding (Prioridade Imediata) mas
  persistente durante o uso real, não só no primeiro login.
- Confirmado que **"Dono do Estabelecimento" nunca aparece pro cliente por bug** — o header
  do `AppShell.jsx` mostra `user.full_name` de quem está de fato logado; só apareceria assim
  se alguém logasse com credencial de proprietário no site do cliente por engano (foi o que
  aconteceu numa sessão de teste anterior, não é um problema de código).
