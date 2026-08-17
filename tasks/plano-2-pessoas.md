# Plano de execução — divisão em 2 pessoas

Este documento substitui a divisão em 5 frentes sugerida em `CLAUDE.md`/no enunciado do
desafio. Os milestones em `milestones/M0-*.md` a `M9-*.md` continuam valendo como fonte de
escopo, critérios de aceite e armadilhas — este arquivo só redefine **quem faz o quê e em que
ordem**, para duas pessoas.

## A fronteira: backend vs. frontend

A divisão segue o contrato de API (`/docs` do FastAPI), não as camadas do enunciado original.
IA/ML e os dois chatbots ficam do lado do backend — não porque sejam "menos importantes", mas
porque dependem do mesmo banco, do mesmo Python e das mesmas regras de negócio que a pessoa de
backend já está com a cabeça dentro. Separar isso para a pessoa de frontend significaria ela
aprender o domínio duas vezes, em duas linguagens.

O mesmo raciocínio vale para o PDF de orçamento (M6): o cálculo de dimensionamento é
`Decimal` e testável em Python — gerar o PDF no backend (reportlab/weasyprint) evita duplicar
a regra de negócio em JS. O frontend só aciona o download.

## Pessoa 1 — Backend, dados, integrações e IA

Dona de: **M1, M2, M3, M6 (lógica), M7 (lógica/prompts), M8, metade de M9**

- Modelo de dados completo + migrations Alembic (M1)
- Auth (JWT + Google OAuth), isolamento `owner` vs. `customer` (M1)
- Simulador do HCA G2 + serviço de polling + interface `SemsClient` (M2)
- Motor de tarifação, ciclo de vida de sessão, fila (M3) — é a parte com mais teste unitário
  exigido; ver skill `tarifacao-e-sessoes`
- `services/sizing.py` + `services/charger_catalog.py` + geração do PDF de orçamento (M6)
- Chatbot: endpoint de chat, LangChain, ferramentas, os dois system prompts (M7) —
  ver skill `chatbots-gemini`
- Microserviço de IA: previsão de demanda, detecção de anomalias, segmentação (M8)
- Deploy do backend + IA + Postgres no Railway (metade de M9)

## Pessoa 2 — Frontend, produto e experiência

Dona de: **M4, M5, M6 (UI), M7 (UI), metade de M9**

- Portal do Proprietário: dashboard, gestão de tarifas, usuários/planos, relatórios (M4)
- Portal do Cliente: sessão em andamento, mapa, fila, histórico, sustentabilidade,
  modo empresarial (M5)
- Onboarding wizard (formulário guiado + tela de resultado do dimensionamento) (M6, UI)
- Widget de chat nos dois portais, consumindo o endpoint que a Pessoa 1 expõe (M7, UI)
- Componentes compartilhados, formatação `pt-BR`, estados vazios/erro/skeleton —
  ver skill `ui-dois-portais`
- Deploy dos dois frontends na Vercel (metade de M9)

## Cronograma em fases

Sem datas fixas — ajuste a duração de cada fase ao prazo real do desafio. A regra é: **uma
pessoa nunca fica travada esperando a outra terminar**.

### Fase 0 — Fundação (as duas pessoas juntas)
`M0` inteiro. Inclui os wireframes do dashboard e da sessão em andamento — sem isso a Pessoa 2
não tem o que construir na Fase 1.

### Fase 1 — Contrato de dados
- **Pessoa 1:** `M1` — modelos, auth, CRUD básico, OpenAPI publicado.
- **Pessoa 2:** telas estáticas dos dois portais com dado mockado (formato copiado dos schemas
  Pydantic do `/docs`), a partir dos wireframes do M0. Não espera o backend existir.
- **Sync:** OpenAPI fechado → Pessoa 2 gera tipos e troca mock por `fetch` real nas telas que
  já não dependem de M2/M3.

### Fase 2 — Dados vivos
- **Pessoa 1:** `M2` (simulador + polling) e `M3` (tarifação/sessões).
- **Pessoa 2:** fecha dashboard e sessão em andamento contra a API real assim que `M1` permitir
  autenticação e CRUD; usa o seed de M1 enquanto M2/M3 não fecham.
- **Sync:** `charger_readings` fluindo → o mapa de vagas do dashboard passa a mostrar dado real,
  não seed estático.

### Fase 3 — Produto completo
- **Pessoa 1:** `M6` (dimensionamento + PDF) primeiro — é bloqueio direto do onboarding da
  Pessoa 2. Só depois começa `M7` (chatbot backend).
- **Pessoa 2:** completa `M4`/`M5` (tarifas, planos, fila, histórico, sustentabilidade),
  onboarding wizard (`M6` UI) e o widget de chat (`M7` UI) — pode mockar a resposta do chat
  enquanto o endpoint da Pessoa 1 não existe.
- **Sync:** antes de codar `M7`, alinhar juntas o texto exato dos dois system prompts
  (skill `chatbots-gemini`) — muda o layout do widget de chat.

### Fase 4 — IA e polish
- **Pessoa 1:** `M8` — regra determinística de anomalia primeiro (é imediata e já gera alerta),
  depois previsão de demanda com Prophet. Segmentação e precificação automática só se sobrar
  tempo (ver cortes abaixo).
- **Pessoa 2:** consome previsão/anomalias no dashboard, resolve acessibilidade
  (contraste, ícone + texto em todo estado), estados vazios e de erro em toda tela.

### Fase 5 — Deploy e ensaio
`M9` inteiro, as duas pessoas juntas. Não deixar para a véspera — fazer um deploy de teste
ainda na Fase 0, com as telas em branco, para pegar os problemas de CORS/env cedo.

## Cortes, em ordem, se o tempo apertar

Com duas pessoas cobrindo o escopo original de cinco, estes cortes do `tasks/README.md` deixam
de ser "se sobrar tempo" e passam a ser prováveis:

1. Modo empresarial (Pessoa 2, M5)
2. Segmentação de clientes (Pessoa 1, M8)
3. Precificação dinâmica automática — manter só a sugestão manual (Pessoa 1, M8)
4. Exportação de relatório financeiro em PDF — manter a tela (Pessoa 2, M4)
5. `RealSemsClient` — deixar como stub sem implementação real; não é necessário para a demo
6. LSTM como alternativa ao Prophet — nunca foi necessário, nem cogitar

**Nunca cortar:** dashboard do proprietário, sessão em andamento do cliente, motor de
tarifação, simulador. São os quatro itens que carregam a demo inteira.

## Pontos de sincronização obrigatórios

- Fim de `M1`: OpenAPI publicado — Pessoa 2 regenera tipos.
- Fim de `M2`: dado real fluindo — Pessoa 2 troca mock por fetch nas telas que dependiam disso.
- Antes de `M7`: texto dos dois system prompts alinhado entre as duas.
- Antes de `M9`: ensaio da demo, as duas pessoas, roteiro do `M9-deploy-demo.md` cronometrado.
