import { useEffect, useRef, useState } from 'react'
import { FaqAccordion } from '../components/ui/FaqAccordion'
import { ApiError, apiClient, describeChatError } from '../lib/apiClient'
import { useAuth } from '../lib/auth'
import { HELP_FAQ, SUPPORT_CONTACT } from '../lib/faq'

// Assistente do cliente (Sprint 4): conversa com o backend em streaming
// (`POST /chatbot/customer/message/stream`). So enxerga os dados de quem esta logado -
// sessao, recibo, plano, fila - e a tarifa publica; nunca dado financeiro do estabelecimento.
const SUGGESTIONS = ['Quanto falta pra terminar?', 'Qual a tarifa agora?', 'Quanto deu minha última recarga?']

export function AjudaPage() {
  const { logout } = useAuth()
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [pending, setPending] = useState(false)
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' })
  }, [messages])

  function updateLast(update) {
    setMessages((prev) => {
      const next = [...prev]
      next[next.length - 1] = { ...next[next.length - 1], ...update(next[next.length - 1]) }
      return next
    })
  }

  async function send(text) {
    const message = text.trim()
    if (!message || pending) return
    const history = messages.map(({ role, content }) => ({ role, content }))
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: message },
      { role: 'assistant', content: '', streaming: true },
    ])
    setDraft('')
    setPending(true)
    try {
      await apiClient.stream('/chatbot/customer/message/stream', { message, history }, (evt) => {
        if (evt.type === 'token') updateLast((m) => ({ content: m.content + evt.text }))
        if (evt.type === 'done') updateLast(() => ({ content: evt.reply, streaming: false }))
      })
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        logout()
        return
      }
      updateLast(() => ({ content: describeChatError(error), streaming: false }))
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="flex flex-1 flex-col">
      <div className="flex items-center gap-2.5 bg-ink-fixed px-5 py-4 text-white">
        <svg width="22" height="22" viewBox="0 0 24 24" className="shrink-0">
          <defs>
            <linearGradient id="cbolt3" x1="4" y1="2" x2="20" y2="22" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#FF7A1A" />
              <stop offset="55%" stopColor="#E60012" />
              <stop offset="100%" stopColor="#7C3AED" />
            </linearGradient>
          </defs>
          <path d="M13 2 3 14h7l-1 8 10-12h-7l1-8Z" fill="url(#cbolt3)" />
        </svg>
        <div>
          <p className="font-heading text-sm font-semibold">Ajuda</p>
          <p className="mt-0.5 text-[10.5px] text-white/55">pergunte sobre sua sessão, tarifa ou plano</p>
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-3 overflow-y-auto p-5" aria-live="polite">
        <div className="max-w-[85%] self-start rounded-[16px_16px_16px_4px] border border-hairline bg-surface px-[15px] py-[11px]">
          <p className="text-[13px] leading-relaxed text-ink">
            Oi! Posso te ajudar com sua recarga, a tarifa, seus recibos, seu plano e a fila.
          </p>
        </div>

        {messages.length === 0 && (
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                onClick={() => send(suggestion)}
                className="rounded-full border border-hairline bg-surface px-3 py-1.5 text-[12px] text-ink-soft"
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}

        {messages.map((message, index) => (
          <div
            key={index}
            className={`max-w-[85%] px-[15px] py-[11px] text-[13px] leading-relaxed ${
              message.role === 'user'
                ? 'self-end rounded-[16px_16px_4px_16px] bg-ink-fixed text-white'
                : 'self-start rounded-[16px_16px_16px_4px] border border-hairline bg-surface text-ink'
            }`}
          >
            <p className="whitespace-pre-wrap">
              {message.content || (message.streaming ? 'consultando…' : '')}
            </p>
          </div>
        ))}
        <div ref={endRef} />

        {messages.length === 0 && (
          <div className="mt-2">
            <h2 className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">
              Perguntas frequentes
            </h2>
            <FaqAccordion items={HELP_FAQ} />
            <p className="mt-3 text-[11px] text-muted-2">
              Não resolveu? Fale com o estabelecimento onde você carrega — {SUPPORT_CONTACT.email}
              <br />
              <span className="text-muted-3">({SUPPORT_CONTACT.note})</span>
            </p>
          </div>
        )}
      </div>

      <form
        onSubmit={(event) => {
          event.preventDefault()
          send(draft)
        }}
        className="border-t border-hairline px-5 py-3"
      >
        <div className="flex items-center gap-2 rounded-full border-[1.5px] border-hairline py-2 pl-4 pr-2">
          <input
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Escreva sua pergunta…"
            aria-label="Sua pergunta"
            className="flex-1 border-none bg-transparent text-[13px] text-ink outline-none placeholder:text-muted-3"
          />
          <button
            type="submit"
            disabled={pending || !draft.trim()}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand disabled:opacity-40"
            aria-label="Enviar"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
      </form>
    </div>
  )
}
