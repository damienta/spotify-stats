import { motion } from 'framer-motion'
import { useId } from 'react'

import { cn } from '@/lib/utils'

/** A pill switcher (Day / Week / ...); the green pill slides between options. */
export function Segmented<T extends string>({
  options,
  value,
  onChange,
  className,
}: {
  options: { value: T; label: string }[]
  value: T
  onChange: (value: T) => void
  className?: string
}) {
  const id = useId()
  return (
    <div role="tablist" className={cn('glass flex rounded-full p-1', className)}>
      {options.map((o) => (
        <button
          key={o.value}
          role="tab"
          aria-selected={o.value === value}
          onClick={() => onChange(o.value)}
          className={cn(
            'relative flex-1 rounded-full px-3 py-1.5 text-xs font-semibold transition-colors sm:text-sm',
            o.value === value ? 'text-black' : 'text-muted hover:text-white',
          )}
        >
          {o.value === value && (
            <motion.span
              layoutId={id}
              className="absolute inset-0 rounded-full bg-accent"
              transition={{ type: 'spring', stiffness: 500, damping: 38 }}
            />
          )}
          <span className="relative">{o.label}</span>
        </button>
      ))}
    </div>
  )
}
