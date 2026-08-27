# Status atual do projeto

> Snapshot em 27/08/2026. Documento vivo — atualizar a cada rodada grande de trabalho (ver
> `tasks/milestones/` para o detalhe tarefa a tarefa; este arquivo é a visão executiva).

## 1. O que está feito

### Núcleo do produto (nunca cortado, per `tasks/README.md`)
- **M0-M1** — fundação do repositório e modelo de dados/backend core.
- **M2** — simulador de hardware + serviço de polling (uma decisão de escopo registrada, tráfego "ambiente" ainda não existe).
- **M3** — motor de tarifação, sessões, fila e catálogo fixo de planos.
- Dashboard do proprietário, sessão em andamento do cliente e motor de tarifação — as quatro peças que a própria documentação do projeto marca como "são a demo" — estão implementadas e testadas.

### Portais (M4/M5) — religados com dado real
- Sessão do cliente, fila (dois portais), relatórios financeiros, recibo digital e sugestão de precificação dinâmica na UI — tudo consumindo endpoints reais, sem placeholder de "em construção".

### Motion design, mapa e reserva (M10)
- GSAP em todas as transições de tela, contadores e estados de feedback nos dois portais.
- Mapa do cliente com geolocalização real (Haversine), tela de detalhe do estabelecimento, reserva antecipada com tolerância de no-show.
- Modo escuro nos dois portais via CSS variables.
- Prioridade 3 (carregador 3D) descartada por decisão do usuário.

### Polimento visual do cliente (Prioridade Imediata, PR #13)
- Mapa real com Leaflet (tiles OpenStreetMap) em `MapaPage`/`MapaDetalhePage`, skeleton loaders via GSAP, estados vazios ilustrados, carrossel de onboarding no primeiro login, favicon + ícones de PWA + manifest.

### Planos e pagamento (Prioridade 4)
- Catálogo fixo de planos definido pela plataforma (avulso/mensal/trimestral) — proprietário só habilita níveis, nunca define valores.
- Forma de pagamento declarativa por estabelecimento e por sessão (nunca processa cobrança de verdade).

### Peça de impacto para a GoodWe (M11, PR #14 + esta rodada)
- Painel agregado de frota multi-estabelecimento, sugestão de cross-sell solar/bateria, hero de impacto (kWh/CO₂/receita) na tela de login dos dois portais, documentação da API (tags no Swagger).
- **Tela de detalhe/telemetria por carregador** (`/carregadores/:id`, proprietário): uptime, curva de potência animada, sessões e anomalias filtradas por carregador — pedida depois de feedback do professor sobre "visão de mercado e venda".
- **Ocupação por vaga**: gráfico novo em Relatórios comparando receita/sessões por carregador.
- **FAQ estático** em 3 lugares (landing pública dos dois portais, Configurações do proprietário, Ajuda do cliente).
- **Histórico de demonstração** de 4 clientes novos no Estacionamento Central, com sessões inspiradas no padrão real de um carregador HCA G2 da FIAP.

## 2. O que ainda falta

Ordenado por urgência para a apresentação/demo, não por número de milestone.

### M9 — Deploy e demo (nada começado, é o maior risco atual)
- Backend + serviço de IA + Postgres não estão no Railway; frontends não estão na Vercel; sem `vercel.json`; sem CORS/variáveis de ambiente de produção; migrations e seed não rodados em produção; simulador não roda continuamente em nenhum ambiente de demo.
- Roteiro de demo cronometrado, dados determinísticos e plano B em vídeo — nada feito.
- Slides da apresentação — não feitos (o resto da documentação — README, arquitetura, modelo de dados, limitações — já está pronto).

### M7 — Chatbots (parcial)
- Infra e segurança básicas prontas (backend intermedia a conversa, autorização por token).
- Faltam as ferramentas reais dos dois bots (consultas de status/receita/tarifa/sessão), streaming de resposta, resposta fixa para relato de emergência. O chatbot do cliente ainda está "em construção" na UI (mitigado nesta rodada com o FAQ estático de `AjudaPage.jsx`, mas o assistente em si não tem ferramentas conectadas).

### M8 — IA/ML (parcial)
- Previsão de demanda e precificação sugerida: fechadas.
- Detecção de anomalias: só a camada de regras determinísticas; falta a camada estatística (Isolation Forest/z-score) e o botão de "falso positivo".
- Segmentação de clientes (K-Means): nada implementado — é item explicitamente cortável se o tempo apertar.
- Engenharia (versionamento de modelo, retreino agendado): não feita.

### M4/M5 — gaps pontuais (não estruturais)
- Proprietário: regras especiais de tarifa com pré-visualização de custo, histórico de consumo por cliente na tela de usuários, bloquear/desbloquear inadimplente, emitir RFID pelo painel, tempo médio de espera na fila, comparativo entre meses e exportação PDF dos relatórios.
- Cliente: login Google, cadastro de veículo/forma de pagamento no onboarding, RFID virtual, % de bateria estimado, notificação push, comparativo/contratação de planos na própria UI, link para o Google Maps, gráfico de consumo mensal, **modo empresarial inteiro** (frota/rateio/fatura consolidada — cortável).

### M6 — Onboarding/dimensionamento (gaps pontuais)
- Payback com premissas editáveis pelo usuário, texto explicando "carga sobressalente", criação automática do estabelecimento ao concluir o orçamento.

### Cortes já aprovados pelo próprio time (não são pendência real)
Ordem de corte definida em `tasks/README.md` se o tempo apertar: modo empresarial (M5) → segmentação de clientes (M8) → precificação automática (M8, hoje já é só sugestão manual, ok) → exportação PDF de relatórios (M4, manter só a tela).

## 3. O que é provisório (sinalizar antes de qualquer uso além da demo)

| Item | Onde | Por quê é provisório |
|---|---|---|
| Contato de suporte (`SUPPORT_CONTACT`) | `lib/faq.js` nos dois portais — landing, Configurações, Ajuda | E-mail/telefone fictícios, rotulados "(em breve)". Nenhum canal real existe ainda. |
| Ilustrações SVG (mapa, estados vazios, onboarding, ícones de app) | `frontend-cliente/src/assets/` | Desenhadas nesta sessão como placeholder funcional — não vieram de um designer. Documentado em `tasks/milestones/M10-motion-mapa-3d.md`. |
| Histórico de sessões de 4 clientes de demonstração | `backend/app/db/seed_demo_history.py` | Números "reais e possíveis" inspirados no padrão de horário/duração/energia de um PDF de registro de carregamento real da FIAP (HCA G2, NS 57000HPA247L0002) — **não são sessões de clientes reais**, são resample com jitter. Marcado na docstring do arquivo. |
| Leituras de potência (`ChargerReading`) backfilladas para o período das sessões de demo | mesmo arquivo acima | Perfil trapezoidal simples gerado por código, não é telemetria real do dispositivo — só alimenta o gráfico de curva de potência com histórico de semanas. |
| Pinos individuais por carregador no mini-mapa de detalhe do estabelecimento | `frontend-cliente/src/pages/MapaDetalhePage.jsx` | `Charger` não tem coordenada própria no banco (só `Establishment`); os pinos usam um offset visual (~50m em círculo) ao redor do ponto real — nunca GPS preciso. Documentado em `M10-motion-mapa-3d.md`. |
| Pagamento (`payment_method` na sessão) | `services/sessions.py`, `SessaoPage.jsx` | Declarativo por decisão de escopo do desafio GoodWe — registra a escolha, nunca processa cobrança de verdade (sem gateway, sem PCI). Não é um "falta terminar", é definitivo para este projeto. |
| Suporte por estabelecimento (`support_phone`/`support_email` do dono) | ideia registrada, não implementada | Diferente do `SUPPORT_CONTACT` acima (que é da plataforma) — esse seria por estabelecimento, ainda não tem campo no banco. |

## Como regenerar o ambiente de demo do zero

```bash
cd backend && alembic upgrade head
python -m app.db.seed              # estabelecimento, carregadores, planos, 1 owner, 1 customer
python -m app.db.seed_demo_history # 4 clientes de demo com historico "real e possivel" (provisorio)
```
