const currencyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
})

const energyFormatter = new Intl.NumberFormat('pt-BR', {
  minimumFractionDigits: 3,
  maximumFractionDigits: 3,
})

const powerFormatter = new Intl.NumberFormat('pt-BR', {
  minimumFractionDigits: 3,
  maximumFractionDigits: 3,
})

const dateTimeFormatter = new Intl.DateTimeFormat('pt-BR', {
  dateStyle: 'short',
  timeStyle: 'short',
  timeZone: 'America/Sao_Paulo',
})

export function formatCurrency(value) {
  return currencyFormatter.format(Number(value))
}

export function formatEnergyKwh(value) {
  return `${energyFormatter.format(Number(value))} kWh`
}

export function formatPowerKw(value) {
  return `${powerFormatter.format(Number(value))} kW`
}

export function formatDateTime(isoString) {
  return dateTimeFormatter.format(new Date(isoString))
}

export function formatUpdatedAgo(seconds) {
  if (seconds < 60) return `atualizado há ${Math.max(0, Math.floor(seconds))}s`
  return `atualizado há ${Math.floor(seconds / 60)} min`
}
