import { ApiError } from './apiClient'

// Mapeamento compartilhado de erros de POST /sessions/start - usado tanto pelo atalho de
// "simular RFID em qualquer carregador livre" (SessaoPage) quanto pela simulacao num
// carregador especifico escolhido no mapa (MapaDetalhePage).
export function startSessionErrorMessage(error) {
  if (error instanceof ApiError && error.status === 400) {
    return 'Sua conta ainda não tem um cartão RFID cadastrado.'
  }
  if (error instanceof ApiError && error.status === 409) {
    return 'Não foi possível iniciar a sessão — carregador ocupado ou você já tem uma sessão em andamento.'
  }
  return 'Não foi possível simular o cartão agora.'
}
