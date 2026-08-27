// Conteudo estatico de FAQ - Prioridade Imediata (pedido do usuario em 27/08/2026, "cara de
// site real"). PROVISORIO: os canais de contato ainda nao existem de verdade (ver
// SUPPORT_CONTACT), so o espaco reservado - trocar assim que houver canal oficial.

export const PUBLIC_FAQ = [
  {
    question: 'O que é o ChargeGrid-Manager?',
    answer:
      'Uma plataforma de gestão pros carregadores GoodWe HCA G2 do seu estabelecimento — sessão, fila, tarifação e relatórios em um só painel.',
  },
  {
    question: 'Preciso de alguma integração técnica com o SEMS+?',
    answer: 'Não diretamente — o polling de leituras roda por trás disso, você só usa o painel.',
  },
  {
    question: 'Eu defino o preço da tarifa e dos planos?',
    answer:
      'A tarifa por horário é sua. Os planos (avulso/mensal/trimestral) seguem um catálogo fixo definido pela plataforma — você só escolhe quais níveis oferece.',
  },
  {
    question: 'Como entro em contato pra ser um estabelecimento parceiro?',
    answer: 'Em breve — os canais de contato desta seção ainda estão sendo configurados.',
  },
]

export const SETTINGS_FAQ = [
  {
    question: 'Como funciona a precificação sugerida?',
    answer:
      'A IA compara a demanda prevista com o histórico e sugere aumento (acima do p80) ou redução (abaixo do p20) — nunca aplica sozinha, a decisão final é sempre sua.',
  },
  {
    question: 'Por que uma sessão fechou sem cobrança?',
    answer: 'Não existe regra de tarifa configurada pra aquele horário — configure uma faixa cobrindo o dia inteiro pra evitar isso.',
  },
  {
    question: 'O que muda entre os níveis do catálogo de planos?',
    answer:
      'Cada nível tem desconto percentual e franquia de kWh fixados pela plataforma — você só habilita quais níveis aceita oferecer, nunca os valores.',
  },
  {
    question: 'Como funciona a franquia do plano mensal/trimestral?',
    answer:
      'É consumida na ordem cronológica das sessões dentro do ciclo de cobrança — depois de esgotada, o cliente passa a pagar a tarifa normal já com o desconto do plano.',
  },
]

export const SUPPORT_CONTACT = {
  email: 'contato@chargegrid-manager.com',
  phone: '(11) 0000-0000',
  note: 'Canal oficial em configuração — em breve',
}
