import { useState } from 'react'
import { ApiError, apiClient, describeChatError } from '../lib/apiClient'
import { useAuth } from '../lib/auth'

// Assistente tecnico do proprietario - resposta transmitida token a token (SSE) pelo
// backend (`POST /chatbot/message/stream`). O frontend nunca fala com o LLM direto; o escopo
// (estabelecimento) e validado pelo token no backend.
const TOOL_LABELS = {
  get_charger_status: 'status dos carregadores',
  get_active_sessions: 'sessões em andamento',
  get_revenue_summary: 'receita',
  get_current_tariff: 'tarifa vigente',
  get_energy_flow: 'fluxo de energia',
  get_demand_forecast: 'previsão de demanda',
  calculate_sizing: 'dimensionamento',
}

export function ChatPage() {
  const { establishment, logout } = useAuth()
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [pending, setPending] = useState(false)
  const [activeTool, setActiveTool] = useState(null)

  function updateLastAssistant(update) {
    setMessages((prev) => {
      const next = [...prev]
      next[next.length - 1] = { ...next[next.length - 1], ...update(next[next.length - 1]) }
      return next
    })
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const text = draft.trim()
    if (!text || pending) return

    const history = messages.map(({ role, content }) => ({ role, content }))
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: text },
      { role: 'assistant', content: '', toolsUsed: [], streaming: true },
    ])
    setDraft('')
    setPending(true)

    try {
      await apiClient.stream(
        '/chatbot/message/stream',
        { establishment_id: establishment.id, message: text, history },
        (evt) => {
          if (evt.type === 'tool') {
            setActiveTool(evt.name)
            updateLastAssistant((m) => ({ toolsUsed: [...m.toolsUsed, evt.name] }))
          } else if (evt.type === 'token') {
            setActiveTool(null)
            updateLastAssistant((m) => ({ content: m.content + evt.text }))
          } else if (evt.type === 'done') {
            updateLastAssistant(() => ({ content: evt.reply, toolsUsed: evt.tools_used, streaming: false }))
          }
        }
      )
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        logout()
        return
      }
      updateLastAssistant(() => ({ content: describeChatError(error), streaming: false }))
    } finally {
      setPending(false)
      setActiveTool(null)
    }
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
            Carregadores, sessões, receita, tarifa, energia solar/bateria e dimensionamento — dados só de {establishment.name}
          </p>
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-8 py-6">
        {messages.length === 0 && (
          <p className="text-sm text-muted">
            Pergunte, por exemplo: "quanto faturei hoje?", "quanto da energia de hoje foi solar?"
            ou "quantos GW22K cabem em 60 kW trifásico?".
          </p>
        )}
        {messages.map((message, index) => (
          <ChatBubble key={index} message={message} />
        ))}
        {pending && (
          <div className="flex items-center gap-2 self-start font-mono text-[11px] text-muted" aria-live="polite">
            <span className="cgm-blink inline-block h-1.5 w-1.5 rounded-full bg-brand" />
            {activeTool ? `consultou ${TOOL_LABELS[activeTool] ?? activeTool}…` : 'pensando…'}
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
            disabled={pending || !draft.trim()}
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
            ? 'rounded-[16px_16px_4px_16px] bg-ink-fixed text-white'
            : 'rounded-[16px_16px_16px_4px] border border-hairline bg-surface text-ink'
        }`}
      >
        <p className="whitespace-pre-wrap">
          {message.content}
          {message.streaming && <span className="cgm-blink ml-0.5 inline-block h-3 w-1.5 translate-y-0.5 bg-muted-3" />}
        </p>
      </div>
      {!isUser && message.toolsUsed?.length > 0 && (
        <p className="font-mono text-[10px] text-muted-3">
          consultou: {message.toolsUsed.map((name) => TOOL_LABELS[name] ?? name).join(', ')}
        </p>
      )}
    </div>
  )
}
