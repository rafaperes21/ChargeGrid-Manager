import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
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
      <div className="flex flex-1 items-center justify-center p-8 text-sm text-muted">
        Nenhum estabelecimento encontrado para este usuário.
      </div>
    )
  }

  return (
    <div className="flex max-w-[820px] flex-1 flex-col">
      <div className="flex items-center gap-3 border-b border-hairline px-8 py-[18px]">
        <svg width="26" height="26" viewBox="0 0 24 24" className="shrink-0">
          <defs>
            <linearGradient id="cbolt" x1="4" y1="2" x2="20" y2="22" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#FF7A1A" />
              <stop offset="55%" stopColor="#E60012" />
              <stop offset="100%" stopColor="#7C3AED" />
            </linearGradient>
          </defs>
          <path d="M13 2 3 14h7l-1 8 10-12h-7l1-8Z" fill="url(#cbolt)" />
        </svg>
        <div>
          <h1 className="font-heading text-[17px] font-bold text-ink">Assistente técnico</h1>
          <p className="mt-0.5 text-xs text-muted">
            Status dos carregadores e previsão de demanda — dados só de {establishment.name}
          </p>
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-8 py-6">
        {messages.length === 0 && (
          <p className="text-sm text-muted">
            Pergunte, por exemplo: "como estão os carregadores?" ou "como está a demanda
            prevista?".
          </p>
        )}
        {messages.map((message, index) => (
          <ChatBubble key={index} message={message} />
        ))}
        {mutation.isPending && (
          <div className="flex items-center gap-2 self-start font-mono text-[11px] text-muted" aria-live="polite">
            <span className="cgm-blink inline-block h-1.5 w-1.5 rounded-full bg-brand" />
            consultando ferramentas do estabelecimento…
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="border-t border-hairline px-8 py-[22px]">
        <div className="flex items-center gap-2.5 rounded-full border-[1.5px] border-[#E7E4F0] py-2 pl-[18px] pr-2">
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
            placeholder="Pergunte sobre dimensionamento, tarifas ou status dos carregadores…"
            className="flex-1 resize-none border-none bg-transparent text-[13px] text-ink outline-none placeholder:text-muted-3"
          />
          <button
            type="submit"
            disabled={mutation.isPending || !draft.trim()}
            className="flex h-[34px] w-[34px] shrink-0 items-center justify-center rounded-full disabled:opacity-40"
            style={{ background: 'linear-gradient(135deg,#E60012,#7C3AED)' }}
            aria-label="Enviar"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
      </form>
    </div>
  )
}

function ChatBubble({ message }) {
  const isUser = message.role === 'user'
  return (
    <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} gap-1.5`}>
      <div
        className={`max-w-[76%] px-4 py-3 text-[13px] leading-relaxed ${
          isUser
            ? 'rounded-[16px_16px_4px_16px] bg-ink text-white'
            : 'rounded-[16px_16px_16px_4px] border border-hairline bg-white text-ink'
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
      </div>
      {!isUser && message.toolsUsed?.length > 0 && (
        <p className="font-mono text-[10px] text-muted-3">consultou: {message.toolsUsed.join(', ')}</p>
      )}
    </div>
  )
}
