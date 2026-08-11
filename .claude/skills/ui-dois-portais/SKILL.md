---
name: ui-dois-portais
description: Convenções de UI dos dois frontends React + Tailwind — mapa de vagas, sessão em andamento, fila, estados de tempo real, acessibilidade e diferenças de tom entre o portal do proprietário e o do cliente. Use ao construir qualquer tela de /frontend-proprietario ou /frontend-cliente.
---

# UI dos dois portais

Dois apps React + Vite + Tailwind, mesmo repositório, **públicos e usuários diferentes**.

| | Proprietário | Cliente |
|---|---|---|
| Contexto de uso | desktop, monitor de sala, sessão longa | celular, na rua, uma mão, pressa |
| Densidade | alta — muitos números por tela | baixa — uma informação principal por tela |
| Tom | operacional, técnico | amigável, direto |
| Prioridade | visão geral + alertas | "quanto falta e quanto vai custar" |

Projete o portal do cliente **mobile-first**. Ele é usado em pé, no estacionamento, com pouca
paciência. O do proprietário é desktop-first.

## 1. Cores de status — use em todo lugar, sem exceção

| Status | Cor | Uso |
|---|---|---|
| Livre | verde | vaga disponível |
| Carregando | azul + barra de progresso | sessão ativa |
| Problema | vermelho | erro/anomalia |
| Reservado | âmbar | reserva de 15 min ativa |
| Offline | cinza | sem comunicação com o SEMS+ |

**Cor nunca é o único sinal.** Todo estado precisa de ícone e rótulo em texto — daltonismo
vermelho/verde é justamente o par que este produto usa para "erro" e "livre". Contraste mínimo
AA (4.5:1) para texto.

## 2. Tempo real sem WebSocket

O dado de origem já é atrasado: o polling do SEMS+ roda a cada 1–5 min. Fingir tempo real
instantâneo é mentira de interface.

- Polling no frontend a cada 15–30 s (`react-query` com `refetchInterval` resolve).
- **Sempre exiba "atualizado há X"** perto dos dados ao vivo. É a diferença entre o operador
  confiar na tela e ele ir conferir no local.
- Barra de progresso do carregamento interpola localmente entre fetches — mas o número de kWh
  e o valor em R$ mostram o último dado confirmado. Nunca extrapole dinheiro na tela.

## 3. Telas prioritárias (fazer primeiro, nesta ordem)

**Proprietário:**
1. Dashboard — mapa de vagas, potência atual vs. limite, receita do dia/semana/mês, sessões ativas
2. Alerta de proximidade do limite (dispara em 90 % da carga configurada — visível, persistente)
3. Gestão de tarifas
4. Onboarding/dimensionamento com geração de PDF

**Cliente:**
1. Sessão em andamento — kWh, % estimado da bateria, tempo restante, valor acumulado, tarifa vigente
2. Mapa de disponibilidade
3. Histórico e recibos
4. Fila (posição em tempo real)

O resto vem depois. Essas quatro de cada lado são a demo.

## 4. Detalhes que decidem a demo

- **Sessão em andamento** é a tela mais vista do produto inteiro. Hierarquia: valor acumulado e
  tempo restante grandes; kWh e tarifa secundários. Se o modelo do veículo não estiver
  cadastrado, mostre kWh e **omita o % de bateria** — não estime sem o dado.
- **Potência vs. limite** no dashboard: barra com o limiar marcado visualmente. O operador
  precisa ver a folga sem ler número.
- **Fila:** a posição precisa estar acima da dobra, grande. É a única informação que importa
  para quem está na fila.
- **Estados vazios e de erro em toda tela.** "Nenhuma sessão ativa" é um estado de sucesso do
  sistema e precisa parecer intencional, não uma tela quebrada.
- **Skeleton, não spinner**, em listas e cards.

## 5. Organização do código

- Componentes compartilhados (botão, card, badge de status, formatadores de R$/kWh/data) em um
  pacote comum. Formatação de moeda e energia duplicada nos dois apps diverge — sempre diverge.
- `pt-BR` em toda formatação: `Intl.NumberFormat('pt-BR', {style:'currency', currency:'BRL'})`.
- Tipos da API gerados a partir do OpenAPI do FastAPI. Não escreva interfaces à mão.
- Nenhuma chamada direta a Gemini ou ao banco pelo frontend. Tudo passa pelo backend.
