import { cn } from '@/lib/utils'

/** Album art when there is some, otherwise the name's initials on a green tint. */
export function Artwork({
  src,
  name,
  round = false,
  className,
}: {
  src?: string | null
  name: string
  round?: boolean
  className?: string
}) {
  const shape = round ? 'rounded-full' : 'rounded-md'
  if (src) {
    return <img src={src} alt="" className={cn('aspect-square object-cover', shape, className)} />
  }
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join('')
  return (
    <div
      aria-hidden="true"
      className={cn(
        'flex aspect-square items-center justify-center bg-accent/15 font-bold text-accent ring-1 ring-accent/25',
        shape,
        className,
      )}
    >
      {initials}
    </div>
  )
}
