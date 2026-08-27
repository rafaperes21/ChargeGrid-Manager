# M4 — Portal do Proprietário

Status: em andamento
Responsável: —
Depende de: M1, M3
Skill: `.claude/skills/ui-dois-portais/`

## Objetivo

A tela que o jurado vai olhar primeiro. Desktop-first, densa, operacional.

## Escopo

### Dashboard (prioridade máxima)
- [x] Mapa visual das vagas: livre (verde) · carregando (azul + progresso) · problema (vermelho)
      · reservado (âmbar) · offline (cinza) — sempre com ícone e rótulo, nunca só cor
- [x] Potência total consumida agora vs. limite configurado, com o limiar marcado na barra
- [x] Receita do dia, semana e mês — `DashboardResponse.revenue_today`/`revenue_week`/
      `revenue_month` somam `amount_due` das sessões `finished` cujo `ended_at` cai no dia,
      semana (segunda-feira local) e mês corrente em horário local (America/Sao_Paulo)
      (`services/dashboard._revenue_breakdown`)
- [x] Número de sessões ativas — `DashboardResponse.active_sessions_count` conta sessões com
      `status == active` no estabelecimento (`services/dashboard.py`)
- [x] **Alerta ao atingir 90 % da carga configurada** — visível e persistente
- [x] Indicador "atualizado há X" perto de todo dado ao vivo
- [x] Refetch a cada 15–30 s (`refetchInterval: 20_000`)

### Gestão de tarifas
- [x] Editor visual das faixas horárias com validação de sobreposição/cobertura
- [ ] Criação de regras especiais (desconto de plano, minutos grátis)
- [ ] Pré-visualização: "uma sessão de 20 kWh às 19h custaria R$ X" — `services/pricing.py`
      (M3) já existe e é uma função pura, fácil de expor num endpoint de simulação; só não
      há tela nem rota específica pra isso ainda

### Gestão de usuários e planos
- [x] Lista de clientes com plano ativo (`UsuariosPlanosPage.jsx` consome a API real)
- [ ] Histórico e consumo do mês — `charging_sessions` reais já existem e são consultáveis
      via `GET /sessions?establishment_id=`; falta só a tela consumir
- [ ] Bloquear/desbloquear inadimplente — não encontrado na tela nem na API
- [ ] Liberar novo cartão RFID pelo painel — tela só exibe o RFID já cadastrado, sem ação de emitir

### Relatórios financeiros
- [ ] Extrato mensal: receita bruta, nº de sessões, kWh total, ticket médio, horários de pico —
      `RelatoriosPage.jsx` é placeholder, sem nenhuma chamada à API; o dado-fonte
      (`charging_sessions` com snapshot de tarifa) já existe via `GET /sessions`, falta agregar
      e conectar a tela
- [ ] Comparativo entre meses
- [ ] Exportação em PDF (cortável se o tempo apertar — manter a tela)

## Plano de execução

Owner: Pessoa 2 (frontend). Depende de M1 (auth/CRUD) e M3 (tarifação/sessões); pode começar
com dado mockado a partir dos wireframes de M0 antes de M1/M3 fecharem (Fase 1 do
`plano-2-pessoas.md`).

1. **Base compartilhada** — se ainda não existir de M0: pacote/diretório comum com badge de
   status (cores + ícone + rótulo, nunca só cor — skill `ui-dois-portais` §1), formatadores
   `pt-BR` (`Intl.NumberFormat('pt-BR', {style:'currency', currency:'BRL'})`), tipos gerados do
   OpenAPI.
2. **Dashboard** (prioridade máxima, fazer primeiro) — mapa de vagas com `react-query`
   `refetchInterval` de 15–30s e "atualizado há X" visível; potência atual vs. limite com o
   limiar marcado na barra; alerta persistente ao atingir 90% da carga; receita
   dia/semana/mês; sessões ativas.
3. **Gestão de tarifas** — editor visual das faixas horárias consumindo a validação de
   sobreposição/cobertura de M3 (erro do backend vira mensagem clara de qual faixa conflita);
   pré-visualização "uma sessão de 20 kWh às 19h custaria R$ X" chamando o motor de cálculo de
   M3.
4. **Gestão de usuários e planos** — lista de clientes com plano/histórico/consumo do mês,
   bloquear/desbloquear inadimplente, liberar cartão RFID.
5. **Relatórios financeiros** — extrato mensal (receita bruta, nº sessões, kWh total, ticket
   médio, horários de pico), comparativo entre meses; exportação em PDF é a primeira coisa a
   cortar se o tempo apertar (manter a tela).
6. **Estados em toda tela** — vazio, loading (skeleton, não spinner) e erro, nas 5 telas acima.
   Fazer junto com cada tela, não como passe final.

## Critérios de aceite

- Com o simulador rodando, o mapa de vagas muda de estado sozinho, sem recarregar a página.
- Forçar a demanda acima de 90 % no simulador faz o alerta aparecer.
- Salvar faixas sobrepostas é rejeitado com mensagem clara de qual conflita com qual.
- Toda tela tem estado vazio, de carregamento (skeleton) e de erro.
- Valores em `pt-BR` com R$ formatado corretamente.

## Armadilhas

- Não invente "tempo real". O dado tem 1–5 min de atraso na origem; o "atualizado há X" é o
  que faz o operador confiar na tela.
- Cor sozinha não comunica estado — o par vermelho/verde é exatamente o pior caso para
  daltonismo, e é o par central deste produto.
