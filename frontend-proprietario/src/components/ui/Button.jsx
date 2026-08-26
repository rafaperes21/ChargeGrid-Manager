const VARIANTS = {
  primary: 'bg-brand text-white hover:bg-brand-hover',
  secondary: 'border border-brand text-brand bg-white hover:bg-brand/5',
  ghost: 'border border-hairline text-ink-soft bg-white hover:bg-cream',
}

export function Button({ variant = 'primary', className = '', ...props }) {
  return (
    <button
      className={`rounded-full px-5 py-2.5 font-body text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${VARIANTS[variant]} ${className}`}
      {...props}
    />
  )
}
