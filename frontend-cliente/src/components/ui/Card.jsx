export function Card({ className = '', ...props }) {
  return (
    <div
      className={`rounded-2xl border border-hairline bg-white p-4 ${className}`}
      {...props}
    />
  )
}
