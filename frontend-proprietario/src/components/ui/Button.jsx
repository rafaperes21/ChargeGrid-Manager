const VARIANTS = {
  primary: 'bg-slate-900 text-white hover:bg-slate-800',
  secondary: 'border border-slate-300 text-slate-700 hover:bg-slate-50',
}

export function Button({ variant = 'primary', className = '', ...props }) {
  return (
    <button
      className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${VARIANTS[variant]} ${className}`}
      {...props}
    />
  )
}
