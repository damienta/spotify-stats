import type { ReactNode } from 'react'

/** A link to Spotify when there's a URL, otherwise the same content without one. */
export function MaybeLink({
  href,
  className,
  children,
}: {
  href?: string | null
  className?: string
  children: ReactNode
}) {
  if (!href) return <div className={className}>{children}</div>
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className={className}>
      {children}
    </a>
  )
}
