import { duration, minutes } from '@/lib/format'
import { cn } from '@/lib/utils'

/** Time listened: minutes first, with the same time in hours in brackets after it. */
export function Minutes({
  value,
  hours = true,
  className,
}: {
  value: number
  hours?: boolean
  className?: string
}) {
  return (
    <span className={cn('tabular', className)}>
      {minutes(value)}
      {hours && value >= 60 && (
        <span className="ml-1 font-normal text-muted">({duration(value)})</span>
      )}
    </span>
  )
}
