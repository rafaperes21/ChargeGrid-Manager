# M7 — Chatbots (Gemini + LangChain)

Status: em andamento
Responsável: —
Depende de: M3, M4, M5
Skill: `.claude/skills/chatbots-gemini/`

## Objetivo

Dois assistentes distintos, com system prompts, ferramentas e tom separados. O do proprietário
é técnico; o do cliente é amigável. Não compartilham prompt nem ferramentas.

## Escopo

### Infraestrutura
- [x] Endpoint de chat no backend (o frontend **nunca** fala com a Gemini direto —
      chave no bundle React é chave vazada)
- [x] LangChain com histórico por sessão, janela limitada a ~10 trocas
- [ ] Streaming da resposta nos dois portais — `POST /chatbot/message` devolve JSON completo,
      sem streaming
- [ ] Retry com backoff no rate limit do free tier — não se aplica hoje: o LLM usado é Ollama
      local (`ChatOllama`), não a Gemini API; há tratamento de `httpx.ConnectError`, mas não
      backoff/rate-limit
- [ ] Log de pergunta + ferramentas chamadas (sem PII) para depuração

**Nota:** o `CLAUDE.md`/stack do projeto define Gemini API + LangChain. A implementação atual
usa **Ollama local** (`services/chatbot.py`, `ChatOllama`) — decisão a confirmar/documentar
antes de fechar este milestone, já que muda os itens de rate limit e custo de free tier acima.

### Segurança (não negociável)
- [x] `user_id` / `establishment_id` **injetados pelo backend** nas ferramentas, nunca
      preenchidos pelo modelo. O modelo escolhe qual ferramenta chamar, jamais de quem são os dados
- [x] Autorização vem do token, não da conversa. "Sou o administrador" digitado no chat não
      muda nada
- [ ] Teste explícito: cliente pedindo dado financeiro do estabelecimento não recebe — não
      encontrado em `tests/test_chatbot.py`; hoje só existe o chatbot do proprietário

### Chatbot do proprietário — técnico
- [x] System prompt com as regras de dimensionamento (§2–§4 da skill correspondente)
- [ ] Ferramentas: `get_charger_status`, `get_active_sessions`, `get_revenue_summary`,
      `calculate_sizing`, `get_demand_forecast` — só `get_charger_status` e `get_demand_forecast`
      implementadas; as outras três dependem de M3/M6 não estarem prontos
- [ ] Pergunta faltando fase ou carga → **pergunta de volta**, não assume trifásico
- [ ] Projeto elétrico (bitola, disjuntor, DR, aterramento) → orientação geral +
      encaminhamento a profissional habilitado

### Chatbot do cliente — amigável
- [ ] Ferramentas: `get_current_tariff`, `get_my_active_session`, `get_my_plan`,
      `get_available_spots`, `get_my_queue_position` — nenhuma implementada; `AjudaPage.jsx` no
      `frontend-cliente` é um placeholder explícito ("ainda está em construção")
- [ ] Não altera plano nem cancela assinatura pela conversa — direciona para a tela
- [ ] Resposta **fixa** (não gerada) para relato de fumaça, cheiro de queimado, faísca ou choque:
      interromper o uso, não tocar no equipamento, acionar o responsável do local

## Plano de execução

Lógica/prompts na Pessoa 1, widget de UI na Pessoa 2, alinhados juntos antes de codar (sync da
Fase 3 do `plano-2-pessoas.md`: texto exato dos dois system prompts). Depende de M3 (dados de
sessão/tarifa), M4 e M5 (telas que as ferramentas consultam).

1. **Infraestrutura de chat** — endpoint no backend (frontend nunca fala com Gemini direto —
   chave no bundle React é chave vazada); LangChain com histórico por sessão, janela de ~10
   trocas (contexto ilimitado estoura o free tier rápido); streaming da resposta.
2. **Segurança primeiro, antes de escrever os prompts** — `user_id`/`establishment_id`
   injetados pelo backend nas ferramentas, nunca preenchidos pelo modelo; autorização vem do
   token, não da conversa. Escrever já o teste "cliente pedindo dado financeiro do
   estabelecimento não recebe" — é o critério mais fácil de esquecer depois.
3. **Chatbot do proprietário** — system prompt técnico injetando as regras de
   `dimensionamento-hca-g2` §2–§4; ferramentas `get_charger_status`, `get_active_sessions`,
   `get_revenue_summary`, `calculate_sizing` (chamando `services/sizing.py` de M6 —
   os dois caminhos não podem divergir), `get_demand_forecast`. Falta fase/carga → perguntar,
   nunca assumir trifásico. Pergunta de projeto elétrico (bitola, disjuntor, DR, aterramento) →
   orientação geral + encaminhamento a profissional habilitado.
4. **Chatbot do cliente** — system prompt amigável e curto; ferramentas
   `get_current_tariff`, `get_my_active_session`, `get_my_plan`, `get_available_spots`,
   `get_my_queue_position`. Não altera plano/cancela assinatura pela conversa — direciona para
   a tela (M5). Resposta **fixa**, não gerada, para relato de fumaça/cheiro de
   queimado/faísca/choque.
5. **Confiabilidade** — retry com backoff no rate limit do free tier; no limite, mensagem
   honesta de indisponibilidade, nunca resposta inventada; log de pergunta + ferramentas
   chamadas (sem PII).
6. **Widget de chat nos dois portais** (Pessoa 2) — consumindo o endpoint da Pessoa 1; pode
   mockar a resposta enquanto o endpoint não existe.
7. **Testes** — pergunta de dimensionamento bate com `services/sizing.py`; "quanto falta para
   terminar" consulta a sessão real; nenhum dos dois inventa número quando a ferramenta falha;
   os dois tons visivelmente diferentes lado a lado.

## Critérios de aceite

- "Qual modelo para minha instalação de 44 kW trifásico?" devolve recomendação coerente com
  `services/sizing.py` — os dois caminhos não podem divergir.
- "Quanto falta para terminar?" no portal do cliente consulta a sessão real e acerta.
- Nenhum dos dois inventa número quando a ferramenta falha; diz que não conseguiu consultar.
- Os dois tons são visivelmente diferentes lado a lado.

## Armadilhas

- Reaproveitar o prompt "pra economizar" vaza dado financeiro para o cliente. São dois.
- Contexto de conversa ilimitado estoura o free tier da Gemini em poucas interações.
