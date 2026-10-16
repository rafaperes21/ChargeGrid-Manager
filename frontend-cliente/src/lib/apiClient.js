const API_URL = import.meta.env.VITE_API_URL
const TOKEN_STORAGE_KEY = 'chargegrid_token'

export class ApiError extends Error {
  constructor(status, body) {
    super(`Erro ${status} na chamada à API`)
    this.status = status
    this.body = body
  }
}

// Conta valida, mas do outro portal (ex.: dono tentando entrar no portal do cliente). O token de
// um perfil nao serve no portal do outro: o backend responde 403 em tudo que e do perfil certo.
export class WrongPortalError extends Error {}

export function getToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY)
}

export function setToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token)
  } else {
    localStorage.removeItem(TOKEN_STORAGE_KEY)
  }
}

async function request(path, options = {}) {
  const token = getToken()
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })

  if (!response.ok) {
    throw new ApiError(response.status, await response.text().catch(() => null))
  }

  if (response.status === 204) return null
  return response.json()
}

/**
 * POST com resposta em Server-Sent Events (assistente virtual): chama `onEvent` para cada
 * `data: {json}` assim que ele chega, e devolve o ultimo evento (`done`). Mesmo token e
 * mesmo tratamento de erro HTTP do `request` acima.
 */
async function stream(path, body, onEvent) {
  const token = getToken()
  const response = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    throw new ApiError(response.status, await response.text().catch(() => null))
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let last = null
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const frames = buffer.split('\n\n')
    buffer = frames.pop()
    for (const frame of frames) {
      const line = frame.split('\n').find((l) => l.startsWith('data: '))
      if (!line) continue
      last = JSON.parse(line.slice('data: '.length))
      onEvent(last)
    }
  }
  return last
}

/**
 * Mensagem do assistente quando a conversa nem chega a ter resposta: diz a causa real em vez de
 * um "tente de novo" generico (que escondia, por exemplo, um 403 de conta do perfil errado).
 * Falha do proprio modelo (Ollama parado, modelo nao baixado) chega como resposta normal do
 * backend, ja com a causa - nao passa por aqui.
 */
export function describeChatError(error) {
  if (error instanceof ApiError) {
    if (error.status === 403) {
      return 'Esta conta não tem acesso a este assistente — saia e entre com a conta certa deste portal.'
    }
    if (error.status >= 500) {
      return `O servidor teve um erro ao processar a pergunta (HTTP ${error.status}) — veja o log do backend.`
    }
    return `O servidor recusou a pergunta (HTTP ${error.status}).`
  }
  if (error instanceof TypeError) {
    return 'Não consegui conectar ao servidor do ChargeGrid — confira se o backend está rodando.'
  }
  return 'Não consegui falar com o assistente agora — tente de novo em instantes.'
}

export const apiClient = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) }),
  put: (path, body) => request(path, { method: 'PUT', body: JSON.stringify(body) }),
  patch: (path, body) => request(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: (path) => request(path, { method: 'DELETE' }),
  stream,
}
