import { listened, listenedOther } from '@/lib/format'
import { useSettings } from '@/lib/settings'
import { cn } from '@/lib/utils'

/** Time listened in the unit chosen in Settings, with the other unit in brackets after it. */
export function Minutes({
  value,
  hours = true,
  className,
}: {
  value: number
  hours?: boolean
  className?: string
}) {
  useSettings() // redraw when the unit changes
  const other = hours ? listenedOther(value) : null
  return (
    <span className={cn('tabular', className)}>
      {listened(value)}
      {other && <span className="ml-1 font-normal text-muted">({other})</span>}
    </span>
  )
}
