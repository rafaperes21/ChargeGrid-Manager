# Telas principais

Wireframes de baixa fidelidade das duas telas que o `tasks/README.md` marca como
"nunca corte": dashboard do proprietário e sessão em andamento do cliente. Servem para alinhar
layout e hierarquia de informação antes de começar M4/M5 — não são o design final.

- [`dashboard-proprietario.svg`](dashboard-proprietario.svg) — desktop-first, alta densidade:
  mapa de vagas, alerta de proximidade do limite (>90%), receita, sessões ativas.
- [`sessao-cliente.svg`](sessao-cliente.svg) — mobile-first, uma informação principal por bloco:
  valor acumulado e tempo restante em destaque; kWh e tarifa secundários.

Convenções seguidas (ver skill `ui-dois-portais`):
- Cores de status (verde/azul/vermelho/âmbar/cinza) sempre acompanhadas de ícone + rótulo em
  texto — nunca só cor.
- "Atualizado há Xs" visível perto de todo dado ao vivo — o polling do SEMS+ não é tempo real.
- Dinheiro sempre mostra o último dado confirmado, nunca extrapolado localmente.
- % de bateria só aparece se o modelo do veículo estiver cadastrado; caso contrário, mostra só
  kWh.

Ambos os SVGs abrem em qualquer navegador ou visualizador de imagem.
