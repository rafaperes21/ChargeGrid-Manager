export function Card({ className = '', ...props }) {
  return (
    <div
      className={`rounded-[18px] border border-hairline bg-white p-5 shadow-[0_2px_14px_rgba(14,10,26,0.05)] ${className}`}
      {...props}
    />
  )
}
