# M5 — Portal do Cliente

Status: não iniciado
Responsável: —
Depende de: M1, M3
Skill: `.claude/skills/ui-dois-portais/`

## Objetivo

Mobile-first. Usado em pé, no estacionamento, com pressa. Uma informação principal por tela.

## Escopo

### Cadastro e autenticação
- [ ] Login por e-mail/senha e Google
- [ ] Cadastro do modelo do veículo (alimenta estimativa de % de bateria e tempo restante)
- [ ] Cadastro de método de pagamento
- [ ] Geração do RFID virtual (QR code / número de cartão) para o proprietário cadastrar
      fisicamente no HCA G2 via SEMS+

### Sessão em andamento (prioridade máxima — tela mais vista do produto)
- [ ] kWh carregados, % estimado da bateria, tempo estimado restante, valor acumulado, tarifa vigente
- [ ] Hierarquia visual: valor e tempo restante grandes; kWh e tarifa secundários
- [ ] Sem modelo de veículo cadastrado → mostra kWh e **omite** o % de bateria
- [ ] Barra de progresso interpolada localmente; kWh e R$ só com dado confirmado
- [ ] Notificação push ao terminar

### Planos de assinatura
- [ ] Comparativo avulso / mensal (15 %, fila prioritária) / trimestral (25 %, prioridade máxima)
- [ ] Contratação e troca de plano confirmadas na interface (nunca pelo chat)

### Mapa de disponibilidade
- [ ] Vagas livres em tempo real e potência disponível de cada carregador
- [ ] Reserva com 15 min de antecedência
- [ ] Link de navegação via Google Maps

### Fila inteligente
- [ ] Entrar na fila quando tudo estiver ocupado
- [ ] Posição em tempo real, grande e acima da dobra
- [ ] Notificação quando a vaga liberar, com a janela de 15 min visível em contagem regressiva

### Histórico e sustentabilidade
- [ ] Lista de sessões: data, local, duração, energia, valor
- [ ] Recibo digital para reembolso corporativo
- [ ] Gráfico de consumo mensal
- [ ] Relatório mensal de sustentabilidade: kWh → km equivalentes → kg de CO₂ evitados,
      com comparativo do mês anterior, premissas declaradas e compartilhamento social

### Modo empresarial (cortável se o tempo apertar)
- [ ] Cadastro de frota: veículos e funcionários
- [ ] Painel corporativo com rateio por departamento ou veículo
- [ ] Fatura única mensal consolidada

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
