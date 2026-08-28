// Rotulos das formas de pagamento (`PaymentMethod` no backend) - unico lugar que mapeia o
// enum pra texto em pt-BR, reaproveitado em toda tela que mostra ou seleciona a forma de
// pagamento (sessao ativa, resumo pos-parada, recibo do historico).
export const PAYMENT_METHOD_LABELS = {
  pix: 'Pix',
  cartao_credito: 'Crédito',
  cartao_debito: 'Débito',
  carteira_do_app: 'Carteira do app',
}
