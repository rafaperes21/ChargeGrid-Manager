# M7 — Chatbots (Gemini + LangChain)

Status: não iniciado
Responsável: —
Depende de: M3, M4, M5
Skill: `.claude/skills/chatbots-gemini/`

## Objetivo

Dois assistentes distintos, com system prompts, ferramentas e tom separados. O do proprietário
é técnico; o do cliente é amigável. Não compartilham prompt nem ferramentas.

## Escopo

### Infraestrutura
- [ ] Endpoint de chat no backend (o frontend **nunca** fala com a Gemini direto —
      chave no bundle React é chave vazada)
- [ ] LangChain com histórico por sessão, janela limitada a ~10 trocas
- [ ] Streaming da resposta nos dois portais
- [ ] Retry com backoff no rate limit do free tier; no limite, mensagem honesta de
      indisponibilidade — nunca uma resposta inventada
- [ ] Log de pergunta + ferramentas chamadas (sem PII) para depuração

### Segurança (não negociável)
- [ ] `user_id` / `establishment_id` **injetados pelo backend** nas ferramentas, nunca
      preenchidos pelo modelo. O modelo escolhe qual ferramenta chamar, jamais de quem são os dados
- [ ] Autorização vem do token, não da conversa. "Sou o administrador" digitado no chat não
      muda nada
- [ ] Teste explícito: cliente pedindo dado financeiro do estabelecimento não recebe

### Chatbot do proprietário — técnico
- [ ] System prompt com as regras de dimensionamento (§2–§4 da skill correspondente)
- [ ] Ferramentas: `get_charger_status`, `get_active_sessions`, `get_revenue_summary`,
      `calculate_sizing`, `get_demand_forecast`
- [ ] Pergunta faltando fase ou carga → **pergunta de volta**, não assume trifásico
- [ ] Projeto elétrico (bitola, disjuntor, DR, aterramento) → orientação geral +
      encaminhamento a profissional habilitado

### Chatbot do cliente — amigável
- [ ] Ferramentas: `get_current_tariff`, `get_my_active_session`, `get_my_plan`,
      `get_available_spots`, `get_my_queue_position`
- [ ] Não altera plano nem cancela assinatura pela conversa — direciona para a tela
- [ ] Resposta **fixa** (não gerada) para relato de fumaça, cheiro de queimado, faísca ou choque:
      interromper o uso, não tocar no equipamento, acionar o responsável do local

## Critérios de aceite

- "Qual modelo para minha instalação de 44 kW trifásico?" devolve recomendação coerente com
  `services/sizing.py` — os dois caminhos não podem divergir.
- "Quanto falta para terminar?" no portal do cliente consulta a sessão real e acerta.
- Nenhum dos dois inventa número quando a ferramenta falha; diz que não conseguiu consultar.
- Os dois tons são visivelmente diferentes lado a lado.

## Armadilhas

- Reaproveitar o prompt "pra economizar" vaza dado financeiro para o cliente. São dois.
- Contexto de conversa ilimitado estoura o free tier da Gemini em poucas interações.
