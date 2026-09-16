# ChargeGrid Intelligence
### Sprint 3 — Prototipagem Funcional e Integração
**Disciplina: Soluções em Energias Renováveis e Sustentáveis (SERS) | FIAP x GoodWe | Grupo GTLF**

---

## 1. Equipe

| Nome | RM |
|---|---|
| Fernando Hideki Rosa Oda | RM 571408 |
| Léo Moreno Sambo | RM 569556 |
| Thor Ferreira Camargo | RM 569543 |
| Gabriel Botelho Romão | RM 570589 |
| Rafael Marinucci Peres | RM 569729 |
| David dos Reis Cardoso | RM 568938 |

---

## 2. Vídeo técnico

[**▶ Assistir no YouTube**](SUBSTITUIR_PELO_LINK_DO_VIDEO) *(vídeo não listado, até 5 minutos)*

---

## 3. Evolução do projeto

| Sprint | Entrega |
|---|---|
| **Sprint 1** | Proposta conceitual: problema, 4 pilares e arquitetura em 3 camadas |
| **Sprint 2** | Primeira prova de conceito: script Python (`chargegrid_simulation.py`) simulando sessões, controle de demanda e tarifação em terminal |
| **Sprint 3** | Protótipo funcional real: backend + dois portais web + microsserviço de IA, rodando de ponta a ponta |

Na Sprint 3, o grupo saiu da simulação isolada em terminal para o **ChargeGrid-Manager**: uma
plataforma completa de gestão de carregamento de veículos elétricos sobre o carregador
**GoodWe HCA G2**, com backend único, dois portais (proprietário do estabelecimento e cliente
final) e um microsserviço de IA para previsão de demanda, sugestão de tarifa e detecção de
anomalias.

---

## 4. Esquema de integração dos componentes

### 3.1 Arquitetura geral

```
┌──────────────┐   Pull (1–5 min)   ┌─────────────────┐
│  SEMS+ /     │ ◀───────────────── │  Polling        │
│  Simulador   │                    │  (Python async) │
└──────────────┘                    └────────┬────────┘
                                             │ grava leituras
                                             ▼
┌────────────────────┐              ┌─────────────────┐
│  Portal            │  REST/JSON   │                 │
│  Proprietário      │ ◀──────────▶ │   FastAPI       │
│  (Vercel)          │              │   (Railway)     │
└────────────────────┘              │                 │
                                    │  services/      │
┌────────────────────┐              │   tarifação     │
│  Portal            │  REST/JSON   │   sessões       │
│  Cliente           │ ◀──────────▶ │   fila          │
│  (Vercel)          │              │   dimensionam.  │
└────────────────────┘              └───┬─────────┬───┘
                                        │         │
                          ┌─────────────▼──┐   ┌──▼──────────┐
                          │  PostgreSQL    │   │ Gemini API  │
                          │  (Railway)     │   │ + LangChain │
                          └────────▲───────┘   └─────────────┘
                                   │ somente leitura
                          ┌────────┴───────┐
                          │  Microserviço  │
                          │  IA (/ia)      │
                          └────────────────┘
```

O carregador HCA G2 não expõe API pública — o portal SEMS+ da GoodWe só oferece modelo
**Pull**. Por isso o sistema usa um **serviço de polling** (Python assíncrono) que consulta o
simulador de hardware (ou o SEMS+ real) a cada 1–5 minutos e assume, no backend, todo o
controle de sessão, tarifação e dados. O carregador físico fica responsável apenas por
autorizar o carregamento via RFID.

### 3.2 Fluxo de uma sessão de recarga (ponta a ponta)

```
Cliente aproxima o cartão RFID (real ou simulado)
        ↓
Sessão criada no backend (POST /sessions/start)
        ↓
Worker de polling lê potência do simulador/SEMS+ a cada ciclo
        ↓
Motor de tarifação aplica a tarifa vigente (snapshot na sessão)
        ↓
Controle de demanda distribui a potência entre os carregadores ativos do estabelecimento
        ↓
Cliente encerra a sessão (POST /sessions/current/stop)
        ↓
Consumo final (kWh) e custo calculados; recibo digital gerado
        ↓
Dashboard do proprietário atualiza ocupação, receita e telemetria em tempo real
        ↓
Microsserviço de IA usa o histórico para prever demanda e sugerir tarifa
```

### 3.3 Componentes principais

| Componente | Papel | Tecnologia |
|---|---|---|
| `backend/` | API REST, motor de tarifação, sessões, fila, dimensionamento | FastAPI + PostgreSQL |
| Simulador de hardware | Substitui o SEMS+ real em ambiente de desenvolvimento/demo, via uma interface (`SemsClient`) trocável por variável de ambiente | Python |
| Serviço de polling | Converte o modelo Pull do SEMS+ em atualização quase em tempo real dos portais | Python assíncrono |
| `frontend-proprietario/` | Dashboard do estabelecimento: ocupação, receita, telemetria por carregador, anomalias | React + Tailwind |
| `frontend-cliente/` | Sessão do cliente, mapa dos estabelecimentos, fila, recibo digital | React + Tailwind |
| `ia/` | Previsão de demanda, sugestão de precificação dinâmica, detecção de anomalias | FastAPI + Prophet |

### 3.4 Modelo de dados (resumo)

| Tabela | Papel |
|---|---|
| `establishments` | Estabelecimento — carga disponível (kW), fase, limite de potência |
| `chargers` | Carregador HCA G2 — serial do SEMS+, vaga, potência nominal |
| `users` | Cliente final — veículo, RFID virtual |
| `plans` / `subscriptions` | Planos de tarifação e assinatura |
| `tariff_rules` | Faixas horárias de tarifa (normal / pico) |
| `charging_sessions` | Sessão de recarga, com **snapshot da tarifa aplicada** (garante que o extrato de um mês fechado não muda se a tarifa for reajustada depois) |
| `charger_readings` | Série temporal de potência — matéria-prima da IA |
| `queue_entries` | Fila de espera, com prioridade por plano |
| `alerts` | Anomalias detectadas pela IA |

---

## 5. Justificativa técnica das escolhas

- **Polling em vez de webhook**: o SEMS+ da GoodWe só permite consulta (Pull); não existe
  alternativa de notificação em tempo real, então o worker de polling é a única forma de
  aproximar o sistema de um comportamento "ao vivo".
- **Sessão controlada pelo backend, e não pelo hardware**: o HCA G2 só autoriza o carregamento
  via RFID — toda a lógica financeira (tarifação, fila, cobrança) precisa viver no software,
  não no equipamento.
- **Microsserviço de IA separado do backend principal**: o treino de modelos não pode competir
  por recursos com a API que atende os portais em tempo real, e uma falha na IA não pode
  derrubar a operação do estabelecimento.
- **Interface `SemsClient` com duas implementações** (simulador e API real): trocar o simulador
  pelo hardware real deve ser uma mudança de variável de ambiente, não de código — decisão que
  permitiu construir e testar todo o sistema sem depender de acesso físico ao carregador.
- **Snapshot da tarifa na sessão**: um extrato de um mês já fechado precisa continuar
  reproduzível mesmo que a tarifa mude depois — por isso a tarifa aplicada é gravada na própria
  sessão, e não recalculada a partir do histórico de regras.
- **Prophet para previsão de demanda**: modelo de séries temporais que lida bem com
  sazonalidade diária/semanal do consumo de energia, adequado ao volume de dados gerado por um
  estabelecimento pequeno/médio (poucas semanas de leituras).

---

## 6. Resultados e dados funcionais apresentados

- Sessão de recarga completa executada de ponta a ponta: início via RFID simulado → leituras
  de potência atualizando a curva em tempo real → encerramento manual pelo cliente → recibo com
  a decomposição bruto → promoção → desconto → franquia → total.
- **Controle de demanda em ação**: com múltiplos carregadores ativos, o sistema distribui a
  potência disponível respeitando o limite contratado do estabelecimento, aplicando fator de
  redução quando necessário.
- **Tarifação dinâmica**: tarifas diferentes em horário normal e de pico, refletidas
  automaticamente no custo da sessão.
- **Painel do proprietário** com dados agregados: ocupação, receita, energia total fornecida e
  telemetria por carregador (uptime, curva de potência, anomalias).
- **IA em produção**: com histórico de leituras acumulado, os endpoints `/forecast` e
  `/pricing-suggestions` retornam previsão de demanda (Prophet) e sugestão de ajuste de tarifa
  com base em dados reais gerados pelo simulador — não apenas uma regra fixa.

> **Transparência sobre dados de demonstração**: o histórico de sessões usado para "aquecer" a
> IA (múltiplos clientes ao longo de semanas) é sintético — gerado por código com padrões de
> horário, duração e potência inspirados em um registro real de carregamento (HCA G2, FIAP) —,
> não são sessões de clientes reais. O mesmo vale para o perfil de potência usado na curva de
> telemetria. Isso é necessário para ter volume suficiente de dados para a IA rodar em ambiente
> de demonstração, e está documentado no próprio código-fonte.

---

## 7. Conexão com os conteúdos da disciplina

| Conceito da disciplina | Onde aparece no protótipo |
|---|---|
| Eficiência energética / gestão de demanda | Motor de controle de demanda, que evita sobrecarga da instalação elétrica distribuindo a potência entre carregadores ativos |
| Tarifação dinâmica / gestão ativa da demanda | Tarifa diferenciada por horário de pico, incentivando o deslocamento de consumo para períodos de menor carga na rede |
| Integração com geração distribuída | Arquitetura compatível com priorização de energia solar (inversores GoodWe) nas recargas, quando disponível |
| Redução de emissões via eletromobilidade | Cada sessão gerenciada de forma eficiente representa uma substituição de combustível fóssil por energia elétrica administrada |
| Smart grids | Previsão de demanda e sugestão de tarifa por IA, aproximando o eletroposto comercial de uma rede inteligente de fato |

---

## 8. Como executar o protótipo

Pré-requisitos: Docker (PostgreSQL), Python 3.11, Node 20.

```bash
./scripts/dev.sh                    # Linux/macOS — sobe backend, IA, os dois frontends e o polling
./scripts/dev.ps1                   # Windows

# Regenerar dados de demonstração do zero:
cd backend
alembic upgrade head
python -m app.db.seed                # estabelecimento, carregadores, planos, 1 owner, 1 customer
python -m app.db.seed_demo_history   # histórico de demonstração (dados sintéticos, ver seção 5)
```

Estrutura do repositório:

```
ChargeGrid-Manager/
├── backend/                # API FastAPI + polling + simulador de hardware
├── frontend-proprietario/  # Portal do estabelecimento (React)
├── frontend-cliente/       # Portal do cliente (React)
├── ia/                     # Microsserviço de IA (previsão, precificação, anomalias)
├── docs/                   # Arquitetura, modelo de dados, telas
│   └── sers-sprint3.md     # Este documento
└── scripts/                # Scripts de subida do ambiente completo
```

---

## 9. Limitações conhecidas (transparência)

- Pagamento é **declarativo**: o sistema registra a forma de pagamento escolhida, mas não
  processa cobrança real (sem gateway, sem PCI) — decisão de escopo do desafio, não pendência.
  técnica.
- Deploy em ambiente de produção (Railway/Vercel) ainda não foi feito nesta fase; o protótipo
  foi demonstrado em ambiente local, o que é suficiente para os fins desta Sprint.
- Capacidade de bateria por modelo de veículo usa valores aproximados de especificação pública
  do fabricante, apenas para estimar % e tempo restante de carga.

---

*ChargeGrid Intelligence — FIAP x GoodWe · Soluções em Energias Renováveis e Sustentáveis · Grupo GTLF*
