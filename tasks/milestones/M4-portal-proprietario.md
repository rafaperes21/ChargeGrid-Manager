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
