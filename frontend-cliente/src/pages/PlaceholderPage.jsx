export function PlaceholderPage({ title }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-2 p-8 text-center">
      <h1 className="text-lg font-semibold text-slate-900">{title}</h1>
      <p className="text-sm text-slate-400">Tela ainda não implementada — aguardando design no Figma.</p>
    </div>
  )
}
