import { useState } from 'react'

// Acordeao de FAQ reutilizavel - expande em altura via CSS grid-template-rows (sem medir
// scrollHeight em JS). Espelha frontend-cliente/src/components/ui/FaqAccordion.jsx.
export function FaqAccordion({ items }) {
  const [openIndex, setOpenIndex] = useState(null)

  return (
    <div className="flex flex-col gap-2">
      {items.map((item, index) => {
        const isOpen = openIndex === index
        return (
          <div key={item.question} className="overflow-hidden rounded-xl border border-hairline bg-surface">
            <button
              type="button"
              onClick={() => setOpenIndex(isOpen ? null : index)}
              className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left text-sm font-semibold text-ink"
              aria-expanded={isOpen}
            >
              {item.question}
              <span className="shrink-0 text-muted-2">{isOpen ? '−' : '+'}</span>
            </button>
            <div
              className={`grid transition-[grid-template-rows] duration-300 ease-out ${
                isOpen ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'
              }`}
            >
              <div className="overflow-hidden">
                <p className="px-4 pb-3.5 text-xs leading-relaxed text-muted-2">{item.answer}</p>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
