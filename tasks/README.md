# Plano de execução — ChargeGrid Manager

Cada arquivo em `milestones/` define **escopo, entregáveis, critérios de aceite e dependências**.
Um milestone só começa quando as dependências dele estão marcadas como concluídas.

## Visão geral

| # | Milestone | Depende de | Frente |
|---|---|---|---|
| M0 | [Fundação do repositório](milestones/M0-fundacao.md) | — | todos |
| M1 | [Modelo de dados e backend core](milestones/M1-backend-core.md) | M0 | backend |
| M2 | [Simulador de hardware e polling](milestones/M2-simulador-polling.md) | M1 | ML/dados |
| M3 | [Motor de tarifação e sessões](milestones/M3-tarifacao-sessoes.md) | M1, M2 | backend |
| M4 | [Portal do Proprietário](milestones/M4-portal-proprietario.md) | M1, M3 | frontend 1 |
| M5 | [Portal do Cliente](milestones/M5-portal-cliente.md) | M1, M3 | frontend 2 |
| M6 | [Onboarding, dimensionamento e orçamento PDF](milestones/M6-onboarding-dimensionamento.md) | M4 | backend + frontend 1 |
| M7 | [Chatbots (Gemini + LangChain)](milestones/M7-chatbots.md) | M3, M4, M5 | integração |
| M8 | [Módulo de IA/ML](milestones/M8-modulo-ia.md) | M2, M3 | ML |
| M9 | [Deploy, demo e documentação](milestones/M9-deploy-demo.md) | todos | todos |

## Caminho crítico

```
M0 → M1 → M2 → M3 → ┬→ M4 → M6 ┐
                    ├→ M5 ──────┼→ M7 → M9
                    └→ M8 ──────┘
```

M4 e M5 são paralelos entre si. M8 pode andar em paralelo com M4/M5 assim que M2 e M3 fecharem.
**M2 é o gargalo escondido:** sem dados simulados, nem o portal nem a IA têm o que mostrar.
Não deixe para depois.

## Prioridade se o tempo apertar

Corte nesta ordem, de trás para frente:
1. Modo empresarial (M5) — impressiona, mas não é o núcleo
2. Segmentação de clientes (M8) — é o item de ML mais dispensável
3. Precificação dinâmica automática (M8) — manter só a sugestão manual
4. Relatórios financeiros em PDF (M4) — manter a tela, cortar a exportação

**Nunca corte:** dashboard do proprietário, sessão em andamento do cliente, motor de tarifação,
simulador. Esses quatro *são* a demo.

## Convenção de status

Marque no topo de cada arquivo: `Status: não iniciado | em andamento | concluído`
e o responsável. Feche o milestone só quando **todos** os critérios de aceite passarem.
