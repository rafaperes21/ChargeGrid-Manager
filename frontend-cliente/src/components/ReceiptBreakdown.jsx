import { formatCurrency } from '../lib/format'

// Ordem real do calculo (skill tarifacao-e-sessoes): bruto -> promocao -> desconto -> franquia
// -> total. So exibe as linhas com valor diferente de zero - franquia/promocao/desconto
// zerados nao aparecem, pra nao sugerir um beneficio que nao existiu nesta sessao.
const ROWS = [
  ['gross_amount', 'Bruto', false],
  ['promo_value', 'Promoção (minutos grátis)', true],
  ['discount_value', 'Desconto do plano', true],
  ['franquia_value', 'Franquia', true],
]

export function ReceiptBreakdown({ receipt }) {
  const rows = ROWS.filter(([key]) => Number(receipt[key]) !== 0)

  return (
    <div className="flex flex-col gap-1.5">
      {rows.map(([key, label, isSubtracted]) => (
        <div key={key} className="flex items-center justify-between text-xs text-muted-2">
          <span>{label}</span>
          <span>
            {isSubtracted ? '− ' : ''}
            {formatCurrency(receipt[key])}
          </span>
        </div>
      ))}
      <div className="mt-1 flex items-center justify-between border-t border-hairline pt-1.5 text-sm font-bold text-ink">
        <span>Total cobrado</span>
        <span>{formatCurrency(receipt.final_amount)}</span>
      </div>
    </div>
  )
}
