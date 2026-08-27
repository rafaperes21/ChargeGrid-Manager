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

## Testes

`test_fleet.py` (serviço, com IA mockada) e `test_fleet_api.py` (autorização: overview é
owner-only e exige token, impact é público) - 169 testes backend passando no total.
Verificado ao vivo nos dois portais: hero de impacto na tela de login com dado real da base
de demo (4 estabelecimentos, ~16.500 kWh, R$ 33 de receita), painel de frota com os 6 cards e
a sugestão de cross-sell calculada certa (53% = 40kW/75kW do Estacionamento Central).

## Armadilhas

- `test_sessao_com_curva_esgotada_some_do_cache_e_fica_ociosa` (`test_sems_client.py`) já
  existia antes desta rodada e falha esporadicamente quando rodado junto com a suíte inteira
  (passa isolado) - não é causado por nada desta Prioridade 5, não investigado a fundo aqui
  (fora de escopo), só registrado pra quem topar com ele de novo não perder tempo achando que
  quebrou algo novo.
