# M11 — Peça de impacto pra GoodWe (Prioridade 5)

Status: concluído em 27/08/2026
Responsável: —
Depende de: M3 (planos/pagamento), M4 (dashboard), M8 (anomalias)

## Objetivo

Público-alvo diferente das demais prioridades: quem avalia isso pensa "isso ajuda a vender
mais HCA G2?", não critério de nota. Feito só depois do resto do produto estar estável (era
a Prioridade 5, última da lista do usuário antes desta rodada).

Regra que vale pra toda tarefa aqui: **nunca inventar número**. Se a base de demonstração for
pequena, a tela mostra pequeno mesmo — ser honesto sobre a escala em vez de forjar volume.

## Escopo

- [x] **Tarefa 5.1 — Painel agregado multi-estabelecimento**: `GET /fleet/overview`
      (`services/fleet.py`, owner-only) soma estabelecimentos, carregadores, kWh gerenciado e
      receita processada (sessões `finished`) e anomalias detectadas (IA) **entre todos os
      estabelecimentos da plataforma**, não só o do proprietário logado. `FrotaPage.jsx`
      (rota `/frota`) exibe os números com a mesma contagem ascendente (`animateNumber`) já
      usada no resto do produto.
      **Decisão de escopo não pedida explicitamente, documentada aqui**: o endpoint nunca
      expõe o detalhe de nenhum estabelecimento específico por nome (só a soma) - evita
      vazar receita de um proprietário pra outro numa instância multi-tenant, mesmo sendo
      "só pra demonstração". Se o requisito real for outro, revisar aqui antes de mudar.
- [x] **Tarefa 5.2 — Cross-sell solar/bateria**: card "Oportunidade GoodWe" em
      `FrotaPage.jsx`, regra simples e real (`power_limit_kw / grid_connection_kw >= 50%`)
      sobre o **próprio estabelecimento do proprietário logado** (nunca cruza dado de outro
      dono - mesma cautela da 5.1). Explicitamente rotulado como "regra simples, não análise
      de engenharia".
- [x] **Tarefa 5.3 — Tela de abertura de impacto**: `GET /fleet/impact` (`services/fleet.py`,
      **público, sem autenticação**) expõe só os 3 números de impacto (kWh total, CO₂
      evitado, receita habilitada) - nunca contagem de sessões nem nada quebrado por
      estabelecimento. `ImpactHero` renderizado acima do formulário de login nos **dois**
      portais (`LoginPage.jsx`). CO₂ calculado em `services/sustainability.py`
      (`km_equivalentes = kWh / avg_vehicle_kwh_per_km`, `co2_kg = km * co2_emission_factor`),
      fatores em `Settings` (não hardcoded, skill `tarifacao-e-sessoes` §7).
- [x] **Tarefa 5.4 — Documentação da API**: `openapi_tags` com descrição por domínio em
      `app/main.py` (16 tags) + `description`/`summary` nos 2 endpoints novos de `fleet.py` +
      `summary` em `health.py`. Muitos endpoints já tinham docstring (o Swagger já usa como
      descrição individual automaticamente); o que faltava era o agrupamento por tag legível.

- [x] **Extra — Tela de detalhe do carregador (telemetria)**, adicionada em 27/08/2026 fora
      da lista original: pedido explícito do usuário depois de feedback do professor sobre
      "visão de mercado e venda" - mostrar telemetria granular por unidade física fala
      diretamente com quem vende hardware. `GET /chargers/{id}/detail?hours=` novo
      (`services/charger_detail.py`, owner-only, escopado ao próprio estabelecimento) reúne:
      uptime (`None`, nunca 0%, quando não há leitura na janela - o polling só acumula
      histórico desde que o ambiente subiu, sem seed de leituras antigas), curva de potência
      real ponto a ponto (`ChargerReading`, sem interpolar), sessões filtradas por
      `charger_id` (antes só dava pra filtrar por estabelecimento) e anomalias da IA
      filtradas pelo `sems_serial` daquele carregador. `ChargerDetalhePage.jsx`
      (`frontend-proprietario`, rota `/carregadores/:chargerId`) consome isso com um gráfico
      de linha animado (`PowerCurveChart.jsx` - sem lib nova, mesma técnica de
      `stroke-dasharray`/`pathLength=1` já usada na confirmação de sessão do cliente),
      crosshair+tooltip no hover e alternativa em tabela (skill `dataviz`). Cada card do
      "Mapa de vagas" do Dashboard agora é um link pra essa tela. Testado ao vivo como
      `dono@chargegrid.demo`: 112 leituras reais nas últimas 24h, uptime 100%, path SVG sem
      `NaN`, tabela e toggle funcionando.

- [x] **Extra — FAQ + histórico de demo "real e possível" + ocupação por vaga**, adicionado
      em 27/08/2026, mesmo pedido de "visão de mercado e venda":
      - **FAQ estático** em 3 lugares (`lib/faq.js` + `components/ui/FaqAccordion.jsx`,
        duplicados nos dois portais, mesmo padrão de `motion.js`): landing pública nos dois
        `LoginPage.jsx` (antes do login), `ConfiguracoesPage.jsx` novo no proprietário (rota
        `/configuracoes`, ideia que já estava registrada como pendente), e fallback abaixo do
        chatbot em `AjudaPage.jsx` do cliente. **Contato ainda não existe de verdade** -
        `SUPPORT_CONTACT` é um placeholder fixo (`contato@chargegrid-manager.com`, telefone
        fictício) rotulado "(em breve)" em toda tela onde aparece - não é um canal
        operacional, só reserva o espaço visual até existir um de verdade.
      - **Histórico de demonstração "real e possível"**: `backend/app/db/seed_demo_history.py`
        novo (rodar depois do `seed.py`), 4 clientes novos no Estacionamento Central com
        sessões dos últimos 30 dias. Os horários/durações/energias por sessão são
        *inspirados* no padrão real de um registro de carregamento do HCA G2 da FIAP (NS
        57000HPA247L0002, 29/07-27/08/2026, 158,90 kWh em 18 sessões, PDF fornecido pelo
        usuário) - resample com jitter determinístico por cliente, **não são sessões de
        clientes reais**. Cada sessão passa pelo motor de tarifação de verdade
        (`calculate_session_amount` + `_resolve_plan_context` reaproveitados de
        `services/sessions.py`, nunca um valor calculado à mão) - inclusive uma cliente
        (Marina Alves) assinante do plano Mensal, pra mostrar desconto+franquia batendo
        certo nos relatórios. Precisou criar a `TariffRule` que faltava no Estacionamento
        Central (mesma tarifa flat R$2,00/kWh já usada nos outros estabelecimentos de demo -
        sem isso as sessões fechariam como `error`). Também faz backfill de `ChargerReading`
        na janela de cada sessão (perfil trapezoidal simples, não é telemetria real) pra
        curva de potência da tela de detalhe do carregador ter semanas de histórico. Marcado
        como **PROVISÓRIO** na docstring do próprio arquivo e aqui - trocar por dado de
        produção assim que houver clientes reais.
      - **Ocupação por vaga**: `GET /establishments/{id}/chargers-occupancy` novo
        (`services/reports.py::get_charger_occupancy`) - uma linha por carregador (sessões,
        energia, receita, horas carregadas) no período, sempre a partir de sessão `finished`
        real. Gráfico de barras novo em `RelatoriosPage.jsx` (cor única da marca - é uma
        série só atravessando categorias/vagas, não identidades diferentes, skill `dataviz`),
        com rótulo direto de receita por vaga (poucas barras, sem necessidade de legenda).
      - **Seletor de janela (24h/7 dias/30 dias)** em `ChargerDetalhePage.jsx` - com o
        histórico de semanas do backfill acima, 24h fixo só mostraria uma fatia fina na
        maior parte do tempo.

## Testes

`test_fleet.py` (serviço, com IA mockada), `test_fleet_api.py` (autorização: overview é
owner-only e exige token, impact é público), `test_charger_detail.py` (uptime `None` vs
fração, janela de leituras, sessões escopadas ao carregador certo, autorização) e
`test_reports.py` (ocupação por vaga: totais corretos por carregador/período, carregador sem
sessão aparece zerado, autorização) - 179 testes backend passando no total. Verificado ao
vivo nos dois portais: hero de impacto na tela de login agora com ~292 mil kWh/R$452 de
receita (efeito colateral bom do histórico de demo novo), FAQ expandindo nos 3 lugares,
`Configurações` no menu lateral, relatório com 29 sessões/R$374 no mês e gráfico de ocupação
por vaga com valores reais, histórico do cliente Marina Alves com recibo decompondo
bruto→desconto do plano→total batendo com o cálculo real (R$13,34 → -R$2,00 → R$11,34),
seletor 7 dias trazendo 2800 leituras sem `NaN` no path do SVG.

## Armadilhas

- `test_sessao_com_curva_esgotada_some_do_cache_e_fica_ociosa` (`test_sems_client.py`) já
  existia antes desta rodada e falha esporadicamente quando rodado junto com a suíte inteira
  (passa isolado) - não é causado por nada desta Prioridade 5, não investigado a fundo aqui
  (fora de escopo), só registrado pra quem topar com ele de novo não perder tempo achando que
  quebrou algo novo.
