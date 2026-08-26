# Telas principais

Wireframes de baixa fidelidade das duas telas que o `tasks/README.md` marca como
"nunca corte": dashboard do proprietário e sessão em andamento do cliente. Servem para alinhar
layout e hierarquia de informação antes de começar M4/M5 — não são o design final.

- [`dashboard-proprietario.svg`](dashboard-proprietario.svg) — desktop-first, alta densidade:
  mapa de vagas, alerta de proximidade do limite (>90%), receita, sessões ativas.
- [`sessao-cliente.svg`](sessao-cliente.svg) — mobile-first, uma informação principal por bloco:
  valor acumulado e tempo restante em destaque; kWh e tarifa secundários.

## Modelo de alta fidelidade (equivalente ao Figma)

https://claude.ai/code/artifact/55d71b70-3109-4440-a607-d9eae8e6a2ca

Cobre as 10 telas prioritárias dos dois portais (a lista da skill `ui-dois-portais`) mais o
mockup dos dois assistentes de IA (`chatbots-gemini`). Identidade visual própria — paleta e
tipografia inspiradas no site da GoodWe, com a curva de potência P(t) do carregador como
elemento gráfico recorrente, não decorativo. Link privado, gerado via Claude Design; peça
acesso a quem publicou para editar ou exportar PNG/PDF.

Convenções seguidas (ver skill `ui-dois-portais`):
- Cores de status (verde/azul/vermelho/âmbar/cinza) sempre acompanhadas de ícone + rótulo em
  texto — nunca só cor.
- "Atualizado há Xs" visível perto de todo dado ao vivo — o polling do SEMS+ não é tempo real.
- Dinheiro sempre mostra o último dado confirmado, nunca extrapolado localmente.
- % de bateria só aparece se o modelo do veículo estiver cadastrado; caso contrário, mostra só
  kWh.

Ambos os SVGs abrem em qualquer navegador ou visualizador de imagem.
