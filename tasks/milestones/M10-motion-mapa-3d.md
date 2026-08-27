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

### Prioridade 2 — Mapa do cliente: eletroposto mais perto + disponibilidade + reserva

- [ ] Coordenadas e distância: `latitude`/`longitude` em `Establishment` (migration + seed),
      `MapaPage.jsx` usa `navigator.geolocation` + Haversine pra ordenar por distância,
      substituindo o placeholder "Distância e busca chegam numa próxima versão"
- [ ] Tela de detalhe do estabelecimento (`/mapa/:establishmentId`): carregadores individuais
      com status, somente leitura, reaproveitando a lógica do dashboard do proprietário
- [ ] Reserva por horário específico: lacuna já documentada em M3 ("reserva antecipada... não
      modelada") — tabela `reservations` nova, endpoints `POST/GET/DELETE /reservations`,
      opcionalmente pré-selecionando horário de menor movimento via `ia/app/services/forecast.py`
      (mesma tese "IA sugere, nunca decide sozinha" da precificação dinâmica)

### Prioridade 3 — Carregador 3D interativo (`img2threejs`)

Deliberadamente descartada por decisão do usuário em 27/08/2026 — ver memória
`project-gsap-motion-skills-global`: a skill `img2threejs` é um pipeline de 337 arquivos focado
em reconstrução de modelos 3D a partir de skins de CS2, sem relação com o domínio do projeto.
Caminho alternativo se isso for retomado: modelo estilizado do HCA G2 com primitivas do
Three.js (`@react-three/fiber`/`@react-three/drei`), sem depender de nenhuma skill de
conversão de imagem.

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
