// Conteudo estatico de FAQ - Prioridade Imediata (pedido do usuario em 27/08/2026, "cara de
// site real"). PROVISORIO: os canais de contato ainda nao existem de verdade (ver
// SUPPORT_CONTACT), so o espaco reservado - trocar assim que houver canal oficial.

export const PUBLIC_FAQ = [
  {
    question: 'O que é o ChargeGrid-Manager?',
    answer:
      'Uma plataforma que conecta carregadores GoodWe HCA G2 a um app de sessão, fila e pagamento — o estabelecimento cadastra os carregadores, você aproxima o cartão RFID e acompanha tudo em tempo real.',
  },
  {
    question: 'Como funciona a cobrança?',
    answer:
      'A tarifa e a forma de pagamento escolhida ficam registradas na sessão, mas hoje o pagamento é declarativo — não processamos cobrança de verdade, é só o registro do que foi combinado.',
  },
  {
    question: 'Preciso de um cartão especial?',
    answer:
      'Sim, um cartão RFID cadastrado pelo estabelecimento — aproxime de um carregador livre pra abrir a sessão automaticamente.',
  },
  {
    question: 'Como acho um estabelecimento parceiro?',
    answer: 'Pelo mapa dentro do app, com distância até você e disponibilidade de vagas em tempo real.',
  },
]

export const HELP_FAQ = [
  {
    question: 'Por que meu valor aparece como "estimado"?',
    answer:
      'Enquanto a sessão está ativa, o valor é uma projeção com a tarifa e o plano atuais — o valor final só fecha quando o carregamento termina.',
  },
  {
    question: 'O que é a franquia do meu plano?',
    answer:
      'É a quantidade de kWh grátis por mês incluída no seu plano — abate das próximas sessões até acabar o ciclo de cobrança.',
  },
  {
    question: 'Minha reserva expirou, o que aconteceu?',
    answer:
      'Reservas (fila ou horário marcado) têm uma janela de tolerância; se ninguém chegar dentro do prazo, a vaga libera para o próximo da fila.',
  },
  {
    question: 'Posso trocar a forma de pagamento depois de iniciar a sessão?',
    answer: 'Sim, enquanto a sessão estiver em andamento — escolha entre as formas aceitas por aquele estabelecimento.',
  },
]

export const SUPPORT_CONTACT = {
  email: 'contato@chargegrid-manager.com',
  phone: '(11) 0000-0000',
  note: 'Canal oficial em configuração — em breve',
}
