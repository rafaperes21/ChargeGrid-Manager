import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { Button } from '../components/ui/Button'
import { ApiError, apiClient } from '../lib/apiClient'
import { useAuth } from '../lib/auth'

export function ChatPage() {
  const { establishment, logout } = useAuth()
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')

  const mutation = useMutation({
    mutationFn: (message) =>
      apiClient.post('/chatbot/message', {
        establishment_id: establishment.id,
        message,
        history: messages.map(({ role, content }) => ({ role, content })),
      }),
  })

  function handleSubmit(event) {
    event.preventDefault()
    const text = draft.trim()
    if (!text || mutation.isPending) return

    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setDraft('')

    mutation.mutate(text, {
      onSuccess: (data) => {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: data.reply, toolsUsed: data.tools_used },
        ])
      },
      onError: (error) => {
        if (error instanceof ApiError && error.status === 401) {
          logout()
          return
        }
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: 'Não consegui falar com o assistente agora — tente de novo em instantes.',
            toolsUsed: [],
          },
        ])
      },
    })
  }

  if (!establishment) {
    return (
      <div className="flex flex-1 items-center justify-center p-8 text-sm text-slate-400">
        Nenhum estabelecimento encontrado para este usuário.
      </div>
    )
  }

  return (
    <div className="flex flex-1 flex-col p-6">
      <div className="mb-4">
        <h1 className="text-lg font-semibold text-slate-900">Assistente</h1>
        <p className="text-sm text-slate-500">
          Tira dúvidas sobre o status dos carregadores e a previsão de demanda de{' '}
          {establishment.name}. Não inventa dado — se não souber, diz que não sabe.
        </p>
      </div>

      <div className="flex flex-1 flex-col gap-3 overflow-y-auto rounded-lg border border-slate-200 bg-white p-4">
        {messages.length === 0 && (
          <p className="text-sm text-slate-400">
            Pergunte, por exemplo: "como estão os carregadores?" ou "como está a demanda
            prevista?".
          </p>
        )}
        {messages.map((message, index) => (
          <ChatBubble key={index} message={message} />
        ))}
        {mutation.isPending && (
          <p className="text-sm text-slate-400" aria-live="polite">
            Consultando…
          </p>
        )}
      </div>

      <form onSubmit={handleSubmit} className="mt-4 flex gap-2">
        <textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              handleSubmit(event)
            }
          }}
          rows={1}
          placeholder="Digite sua pergunta…"
          className="flex-1 resize-none rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
        />
        <Button type="submit" disabled={mutation.isPending || !draft.trim()}>
          Enviar
        </Button>
      </form>
    </div>
  )
}

function ChatBubble({ message }) {
  const isUser = message.role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[75%] rounded-lg px-3 py-2 text-sm ${
          isUser ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-900'
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {message.toolsUsed?.length > 0 && (
          <p className="mt-1 text-xs text-slate-400">consultou: {message.toolsUsed.join(', ')}</p>
        )}
      </div>
    </div>
  )
}
