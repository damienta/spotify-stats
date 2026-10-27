import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

/**
 * Adapted from Skiper UI — Skiper 40 (Link001): underline sweeps in on hover,
 * with an arrow that rises in for external links. Swapped next/link for <a>.
 * https://skiper-ui.com — free version, attribution required.
 */
export function AnimatedLink({
  children,
  href,
  className,
  external = false,
  showArrow = external,
  ariaLabel,
}: {
  children: ReactNode
  href: string
  className?: string
  external?: boolean
  showArrow?: boolean
  ariaLabel?: string
}) {
  return (
    <a
      href={href}
      aria-label={ariaLabel}
      {...(external ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
      className={cn(
        'group relative inline-flex items-center',
        "before:pointer-events-none before:absolute before:top-[1.4em] before:left-0 before:h-[0.06em] before:w-full before:bg-current before:content-['']",
        'before:origin-right before:scale-x-0 before:transition-transform before:duration-300 before:ease-[cubic-bezier(0.4,0,0.2,1)]',
        'hover:before:origin-left hover:before:scale-x-100 focus-visible:before:origin-left focus-visible:before:scale-x-100',
        'motion-reduce:before:transition-none',
        className,
      )}
    >
      {children}
      {showArrow && (
        <svg
          className="mt-0 ml-[0.3em] size-[0.55em] translate-y-1 opacity-0 transition-all duration-300 group-hover:translate-y-0 group-hover:opacity-100 motion-reduce:transition-none"
          fill="none"
          viewBox="0 0 10 10"
          aria-hidden="true"
        >
          <path
            d="M1.004 9.166 9.337.833m0 0v8.333m0-8.333H1.004"
            stroke="currentColor"
            strokeWidth="1.25"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      )}
    </a>
  )
}
