# M10 — Motion design, mapa com geolocalização e carregador 3D

Status: em andamento
Responsável: —
Depende de: M3, M4, M5 (religados de verdade — não vale animar placeholder)
Skill: `.claude/skills/ui-dois-portais/`, skills `gsap-*` e `motion-design` (globais, `~/.claude/skills/`)

## Objetivo

Não muda nenhuma regra de negócio, contrato de API ou dado exibido — é a camada visual que faz
o produto parecer terminado, sobre telas que já mostram dado real (M3/M4/M5 religados em
27/08/2026). Três prioridades sequenciais, cada uma só começa quando a anterior fecha.

## Escopo

### Prioridade 1 — Motion design com GSAP (concluída em 27/08/2026)

- [x] Setup: `gsap` + `@gsap/react` instalados nos dois frontends; `src/lib/motion.js` com
      `MICRO`/`TRANSITION` (personalidade "Corporate" da skill `motion-design`),
      `prefersReducedMotion()`, `animateNumber()`, `withMotionPreferences()`, `Flip` registrado
- [x] Sessão do cliente (`SessaoPage.jsx`): contagem ascensional do valor acumulado, transição
      suave no tempo decorrido, **tela de confirmação de sessão encerrada** com timeline
      sequenciada (ícone de check desenhando, depois cada linha do recibo empilhando na ordem
      real bruto→promoção→desconto→franquia→total)
- [x] Dashboard do proprietário (`DashboardPage.jsx`): barra de potência anima via `scaleX`
      (transform, não `width`), alerta de 90% pulsa continuamente enquanto ativo, cards de
      anomalia entram com slide+fade, receita hoje/semana/mês conta de forma ascendente
- [x] Sugestão de precificação (`TarifasPage.jsx`): cards de sugestão entram com slide+fade
      (mantidos aqui, não no Dashboard — é configuração de tarifa, não monitoramento)
- [x] Fila: posição do cliente (`FilaPage.jsx`) conta suavemente ao mudar; lista do
      proprietário (`FilaProprietarioPage.jsx`) reordena com GSAP Flip (FLIP: First Last
      Invert Play) em vez de só re-renderizar
- [x] Transições de rota (`AppShell.jsx` nos dois portais): fade+slide ao trocar de página;
      item de navegação ativo (`BottomNav.jsx`/`Sidebar.jsx`) transiciona suavemente em vez de
      trocar de classe instantâneo
- [x] Onboarding (`OnboardingPage.jsx`): o fluxo real é um formulário único + painel de
      resultado (não um wizard em etapas, ao contrário do que M6 descrevia) — o painel de
      resultado entra com a mesma constante `TRANSITION`

**Bugs reais encontrados e corrigidos durante esta prioridade** (não eram sobre animação, eram
sobre o dado por trás dela):
1. `gsap.to()`/`fromTo()` nunca dispara `onUpdate` quando `from === to` (comum no primeiro
   render) — contadores e barras ficavam em branco. `animateNumber()` agora escreve o estado
   inicial de forma síncrona antes do tween.
2. `GET /sessions/current` podia devolver a própria sessão com `status` já `finished`/`error`
   no exato poll em que ela fecha (vazando um status terminal numa resposta 200). Corrigido no
   backend: o endpoint agora sempre 404 depois que `sync_session` fecha a sessão — contrato
   "pending/active ou 404", nunca um terceiro estado. Ver `M3-tarifacao-sessoes.md`.

**Limitação de ferramenta anotada (não é bug do produto):** o Browser pane usado pra testar
neste ambiente nunca dispara `requestAnimationFrame`, então animações GSAP baseadas em tween
não podem ser observadas em movimento aqui — só o estado inicial (`gsap.set()`, síncrono) e o
dado final são verificáveis ao vivo. Ver memória `feedback_gsap_counter_gotcha`.

### Prioridade 2 — Mapa do cliente: eletroposto mais perto + disponibilidade + reserva (concluída em 27/08/2026)

- [x] Coordenadas e distância: `latitude`/`longitude` (`Numeric(9,6)`, opcionais) em
      `Establishment` (migration `7830e4378920`), seed com coordenada real (Av. Paulista, SP).
      `MapaPage.jsx` usa `navigator.geolocation.getCurrentPosition` + Haversine
      (`src/lib/geo.js`) pra ordenar por distância, com fallback textual claro se a permissão
      for negada ou o dispositivo não suportar geolocalização — substitui o placeholder
      "Distância e busca chegam numa próxima versão". Estabelecimentos sem coordenada cadastrada
      vão para o fim da lista, nunca quebram a ordenação.
- [x] Tela de detalhe do estabelecimento (`MapaDetalhePage.jsx`, rota `/mapa/:establishmentId`,
      fora do array `routes.js` pra não virar aba extra no `BottomNav`): carregadores
      individuais com `StatusBadge` e "atualizado há X", via `GET
      /establishments/{id}/chargers-status` — endpoint novo, aberto a qualquer usuário
      autenticado (mesmo raciocínio de `GET /chargers`: status não é dado financeiro),
      reaproveitando a leitura de `services/dashboard.get_chargers_status` (extraída de
      `get_dashboard` pra ser compartilhada sem duplicar a leitura de última leitura por
      carregador).
- [x] Reserva por horário específico: tabela `reservations` nova (`user_id`, `charger_id`,
      `scheduled_start/end`, `status` — `pending/fulfilled/cancelled/no_show`),
      `services/reservations.py` com a mesma tolerância de 15 min de no-show de
      `services/queue.py` (`NO_SHOW_TOLERANCE`). `sync_reservations` (idempotente, mesmo
      padrão de `sync_queue`/`sync_session`: sem worker, resolvido quando alguém consulta o
      estabelecimento) ocupa a vaga (`ChargerStatus.reservado`) a partir do horário agendado e
      marca `no_show` + libera se ninguém confirmar em 15 min. `services/sessions.start_session`
      passa a checar `reservations.find_active_reservation` além da reserva de fila, pro RFID
      abrir sessão numa vaga reservada antecipadamente pelo próprio cliente. Endpoints: `POST
      /reservations`, `GET /reservations/mine`, `DELETE /reservations/{id}` (cliente),
      `GET /establishments/{id}/reservations` (dono, agenda com nome do cliente e vaga).
      UI em `MapaDetalhePage.jsx`: carregador livre oferece "Entrar na fila" ou "Reservar
      horário" (form inline com `datetime-local` + duração), seção "Suas reservas aqui" com
      cancelamento. Testado ao vivo no navegador: reserva criada, cancelada, fila oferecida
      na hora por ter vaga livre.
      **Escopo em aberto, documentado aqui em vez de decidido sozinho:** sugestão de horário de
      menor movimento via `ia/app/services/forecast.py` (item "se houver tempo" do pedido
      original) não foi implementada nesta rodada — ficaria acoplando a tela de reserva a mais
      uma chamada à IA sem pedido explícito de prioridade. Retomar se o usuário pedir.
      Conflito de agenda quando a vaga reservada é ocupada por um walk-in antes do horário
      também é um limite conhecido e não resolvido automaticamente (comentado em
      `services/reservations.sync_reservations`).

### Prioridade 3 — Carregador 3D interativo (`img2threejs`)

Deliberadamente descartada por decisão do usuário em 27/08/2026 — ver memória
`project-gsap-motion-skills-global`: a skill `img2threejs` é um pipeline de 337 arquivos focado
em reconstrução de modelos 3D a partir de skins de CS2, sem relação com o domínio do projeto.
Caminho alternativo se isso for retomado: modelo estilizado do HCA G2 com primitivas do
Three.js (`@react-three/fiber`/`@react-three/drei`), sem depender de nenhuma skill de
conversão de imagem.

### Extra — Modo escuro nos dois portais (27/08/2026)

Pedido direto do usuário nesta rodada, fora da lista de prioridades original — mantendo o
template intacto (nenhuma classe Tailwind mudou nas telas, só o valor por trás dos tokens
de cor).

- `index.css` (idêntico nos dois frontends): tokens de superfície/texto que já eram
  semânticos (`--color-cream`, `--color-hairline`, `--color-muted*`, `--color-ink`,
  `--color-ink-soft`) ganharam uma redefinição sob `:root[data-theme='dark']`. Dois tokens
  novos precisaram de rename mecânico porque eram usados com dois sentidos diferentes:
  `bg-white` (~30 ocorrências) → `bg-surface` (cards/conteúdo, inverte no escuro) e `bg-ink`
  (7 ocorrências: header do cliente, sidebar do proprietário, bolha de chat do usuário,
  banners de mapa) → `bg-ink-fixed` (deliberadamente constante — já são barras escuras no
  claro, não devem mudar). `text-ink`/`text-ink-soft` (74 ocorrências) não precisaram de
  rename, só a variável por trás mudou.
- `src/lib/theme.js` (duplicado nos dois portais, mesmo padrão de `motion.js`/`format.js`):
  `bootstrapTheme()` chamado em `main.jsx` antes do primeiro render (evita flash), respeita
  `prefers-color-scheme` quando não há escolha salva em `localStorage`. `useTheme()` expõe o
  toggle, persistido em `localStorage` (`chargegrid_theme`).
  `components/ui/ThemeToggle.jsx`: ícone sol/lua sobre a barra `bg-ink-fixed` (header no
  cliente, topo da sidebar no proprietário).
- Testado ao vivo nos dois portais: tema inicial respeita preferência do sistema, alternância
  funciona e persiste, barras `bg-ink-fixed` permanecem escuras nos dois temas.
  **Armadilha encontrada:** ler `getComputedStyle` logo após disparar o toggle pode capturar
  um frame intermediário da transição CSS (`transition: background-color .2s`) — não é bug,
  é só timing de teste; reconferir numa chamada separada resolve.

## Critérios de aceite

- Nenhuma animação muda cor, layout ou componente visual existente em repouso — só timing.
- Toda animação usa `MICRO`/`TRANSITION` de `motion.js`, nunca um valor de duração inventado
  na tela.
- `prefers-reduced-motion: reduce` pula direto pro estado final em toda animação nova.
- `pytest` (backend + `ia`) e `npm run build` (os dois frontends) limpos depois de cada tarefa.

## Armadilhas

- `gsap.to()`/`fromTo()` com `from === to` não dispara `onUpdate` — sempre inicializar com
  `gsap.set()` síncrono antes do tween (ver bug #1 acima).
- Cuidado ao testar motion design neste ambiente de Browser pane: rAF não dispara, então só dá
  pra verificar dado e estado inicial, nunca a interpolação em si.
