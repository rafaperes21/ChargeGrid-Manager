# M4 — Portal do Proprietário

Status: não iniciado
Responsável: —
Depende de: M1, M3
Skill: `.claude/skills/ui-dois-portais/`

## Objetivo

A tela que o jurado vai olhar primeiro. Desktop-first, densa, operacional.

## Escopo

### Dashboard (prioridade máxima)
- [ ] Mapa visual das vagas: livre (verde) · carregando (azul + progresso) · problema (vermelho)
      · reservado (âmbar) · offline (cinza) — sempre com ícone e rótulo, nunca só cor
- [ ] Potência total consumida agora vs. limite configurado, com o limiar marcado na barra
- [ ] Receita do dia, semana e mês
- [ ] Número de sessões ativas
- [ ] **Alerta ao atingir 90 % da carga configurada** — visível e persistente
- [ ] Indicador "atualizado há X" perto de todo dado ao vivo
- [ ] Refetch a cada 15–30 s

### Gestão de tarifas
- [ ] Editor visual das faixas horárias com validação de sobreposição/cobertura
- [ ] Criação de regras especiais (desconto de plano, minutos grátis)
- [ ] Pré-visualização: "uma sessão de 20 kWh às 19h custaria R$ X"

### Gestão de usuários e planos
- [ ] Lista de clientes com plano ativo, histórico e consumo do mês
- [ ] Bloquear/desbloquear inadimplente
- [ ] Liberar novo cartão RFID pelo painel

### Relatórios financeiros
- [ ] Extrato mensal: receita bruta, nº de sessões, kWh total, ticket médio, horários de pico
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
