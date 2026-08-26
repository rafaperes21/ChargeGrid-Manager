# M9 — Deploy, demo e documentação

Status: em andamento
Responsável: —
Depende de: todos

## Objetivo

Ter tudo no ar, com um roteiro de demo ensaiado. Sistema que só roda na máquina de uma pessoa
não conta.

## Escopo

### Deploy
- [ ] Backend + serviço de IA + Postgres no Railway — nenhum artefato de deploy encontrado
      (sem `railway.json`/config equivalente no repo)
- [ ] Os dois frontends na Vercel, apontando para o backend de produção — sem `vercel.json`
- [ ] CORS configurado para os domínios reais
- [ ] Variáveis de ambiente de produção (nenhuma chave no código, nenhuma chave no bundle)
- [ ] Migrations rodadas em produção; seed de demo carregado
- [ ] Simulador rodando continuamente no ambiente de demo — a tela precisa estar viva quando
      o jurado abrir

### Roteiro de demo (ensaiar em voz alta, cronometrado)
1. Onboarding do proprietário → dimensionamento → orçamento em PDF
2. Dashboard com sessões acontecendo ao vivo (simulador rodando)
3. Cliente inicia sessão → tela de sessão em andamento avançando
4. Alerta de proximidade do limite disparando
5. Previsão de demanda no mapa de calor + sugestão de tarifa
6. Anomalia injetada → alerta aparecendo
7. Chatbot do proprietário respondendo pergunta de dimensionamento
8. Relatório de sustentabilidade do cliente

- [ ] Dados de demo **determinísticos** (seed fixa): a demo precisa ser idêntica em cada ensaio
- [ ] Plano B gravado em vídeo, para o caso de a internet falhar

### Documentação
- [x] `README.md` completo: problema, solução, arquitetura, como rodar
- [x] `docs/arquitetura.md` com o diagrama do fluxo SEMS+ → polling → banco → portais
- [x] `docs/modelo-de-dados.md` com o diagrama ER
- [x] Seção honesta de limitações: API do HCA G2 indisponível, SEMS+ Pull-only, dados
      simulados, preços pendentes de confirmação com a GoodWe (`README.md` §"Limitações conhecidas")
- [ ] Slides da apresentação

## Plano de execução

As duas pessoas juntas. Depende de todos os milestones — mas o deploy de teste (item 1) deve
acontecer já em M0, com telas em branco, para pegar CORS/env cedo (armadilha do milestone).

1. **Deploy de teste antecipado** (revalidar aqui, já deveria existir desde M0) — backend + `ia`
   + Postgres no Railway, os dois frontends na Vercel, apontando um para o outro.
2. **Ambiente de produção real** — variáveis de ambiente de produção (nenhuma chave no código
   ou no bundle), CORS restrito aos domínios reais, migrations rodadas em produção, seed de
   demo carregado.
3. **Simulador contínuo no ambiente de demo** — a tela precisa estar viva quando o jurado abrir,
   sem depender de alguém iniciar manualmente.
4. **Roteiro de demo** — os 8 passos já listados no escopo, ensaiados em voz alta e
   cronometrados; dados de demo com **seed fixa** (a demo precisa ser idêntica em cada ensaio).
5. **Plano B** — vídeo gravado do roteiro completo, para o caso de falha de internet/deploy no
   dia.
6. **Documentação final** — `README.md` completo (problema, solução, arquitetura, como rodar),
   `docs/arquitetura.md` com o diagrama SEMS+ → polling → banco → portais,
   `docs/modelo-de-dados.md` com o ER, seção honesta de limitações (API do HCA G2 indisponível,
   SEMS+ Pull-only, dados simulados, preços pendentes de confirmação com a GoodWe), slides.
7. **Verificação final** — histórico do git sem segredo (não só o estado atual), README
   suficiente para alguém de fora do time subir o projeto do zero.

## Critérios de aceite

- URLs públicas dos dois portais funcionam num celular com 4G, fora da rede local.
- O roteiro completo roda em menos de 8 min sem intervenção manual no banco.
- Alguém de fora do time consegue subir o projeto do zero seguindo só o README.
- Nenhum segredo no repositório (verificar o histórico do git, não só o estado atual).

## Armadilha

Não deixe o deploy para a véspera. Vercel e Railway têm particularidades — variável de ambiente
faltando, build de Python que quebra em versão diferente, CORS — que consomem horas na primeira
vez. Faça um deploy de teste ainda em M0, mesmo com a tela em branco.
