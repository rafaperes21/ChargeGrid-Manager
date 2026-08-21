const API_URL = import.meta.env.VITE_API_URL

export class ApiError extends Error {
  constructor(status, body) {
    super(`Erro ${status} na chamada à API`)
    this.status = status
    this.body = body
  }
}

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })

  if (!response.ok) {
    throw new ApiError(response.status, await response.text().catch(() => null))
  }

  if (response.status === 204) return null
  return response.json()
}

export const apiClient = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) }),
  put: (path, body) => request(path, { method: 'PUT', body: JSON.stringify(body) }),
  delete: (path) => request(path, { method: 'DELETE' }),
}
