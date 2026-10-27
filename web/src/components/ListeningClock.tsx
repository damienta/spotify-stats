import { duration } from '@/lib/format'
import type { ClockCell } from '@/lib/types'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

/** When you listen: weekdays down, hours across, brighter green for more minutes. */
export function ListeningClock({ cells }: { cells: ClockCell[] }) {
  const max = Math.max(1, ...cells.map((c) => c.minutes))
  const peak = cells.reduce((a, b) => (b.minutes > a.minutes ? b : a), cells[0])
  const label = peak?.minutes
    ? `Listening clock: you listen most on ${DAYS[peak.weekday]} around ${peak.hour}:00.`
    : 'Listening clock: no listening yet.'
  return (
    <div className="space-y-1" role="img" aria-label={label}>
      {DAYS.map((day, weekday) => (
        <div key={day} className="flex items-center gap-1.5">
          <span className="w-7 text-[11px] text-faint">{day}</span>
          <div className="grid flex-1 grid-cols-24 gap-[3px]">
            {cells
              .filter((c) => c.weekday === weekday)
              .map((c) => (
                <div
                  key={c.hour}
                  title={`${day} ${c.hour}:00 · ${duration(c.minutes)}`}
                  className="aspect-square rounded-[3px] bg-accent"
                  style={{ opacity: c.minutes ? 0.12 + 0.88 * (c.minutes / max) : 0.05 }}
                />
              ))}
          </div>
        </div>
      ))}
      <div className="flex justify-between pl-9 text-[11px] text-faint">
        <span>00</span>
        <span>06</span>
        <span>12</span>
        <span>18</span>
        <span>23</span>
      </div>
    </div>
  )
}
