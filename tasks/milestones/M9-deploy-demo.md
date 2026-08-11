# M9 — Deploy, demo e documentação

Status: não iniciado
Responsável: —
Depende de: todos

## Objetivo

Ter tudo no ar, com um roteiro de demo ensaiado. Sistema que só roda na máquina de uma pessoa
não conta.

## Escopo

### Deploy
- [ ] Backend + serviço de IA + Postgres no Railway
- [ ] Os dois frontends na Vercel, apontando para o backend de produção
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
- [ ] `README.md` completo: problema, solução, arquitetura, como rodar
- [ ] `docs/arquitetura.md` com o diagrama do fluxo SEMS+ → polling → banco → portais
- [ ] `docs/modelo-de-dados.md` com o diagrama ER
- [ ] Seção honesta de limitações: API do HCA G2 indisponível, SEMS+ Pull-only, dados
      simulados, preços pendentes de confirmação com a GoodWe
- [ ] Slides da apresentação

## Critérios de aceite

- URLs públicas dos dois portais funcionam num celular com 4G, fora da rede local.
- O roteiro completo roda em menos de 8 min sem intervenção manual no banco.
- Alguém de fora do time consegue subir o projeto do zero seguindo só o README.
- Nenhum segredo no repositório (verificar o histórico do git, não só o estado atual).

## Armadilha

Não deixe o deploy para a véspera. Vercel e Railway têm particularidades — variável de ambiente
faltando, build de Python que quebra em versão diferente, CORS — que consomem horas na primeira
vez. Faça um deploy de teste ainda em M0, mesmo com a tela em branco.
