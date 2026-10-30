import { useRef, useState } from 'react'

import { duration, minutes } from '@/lib/format'
import type { ClockCell } from '@/lib/types'
import { cn } from '@/lib/utils'

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const PARTS = [
  { name: 'Night', from: 0, to: 6 },
  { name: 'Morning', from: 6, to: 12 },
  { name: 'Afternoon', from: 12, to: 18 },
  { name: 'Evening', from: 18, to: 24 },
]
const ARROWS: Record<string, [number, number]> = {
  ArrowLeft: [0, -1],
  ArrowRight: [0, 1],
  ArrowUp: [-1, 0],
  ArrowDown: [1, 0],
}

const hour = (h: number) => `${String(h).padStart(2, '0')}:00`
const pct = (part: number, whole: number) => `${Math.round((100 * part) / Math.max(1, whole))}%`
// Minutes first, with hours in brackets once it's an hour or more.
const time = (m: number) => (m >= 60 ? `${minutes(m)} (${duration(m)})` : minutes(m))
const sum = (cells: ClockCell[]) => cells.reduce((s, c) => s + c.minutes, 0)
/** Cell brightness: square root so quiet hours still show next to busy ones. */
const shade = (m: number, max: number) => (m ? 0.15 + 0.85 * Math.sqrt(m / max) : 0.05)

function Tile({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="rounded-xl bg-white/[0.04] px-3 py-2">
      <p className="text-[11px] font-semibold tracking-wide text-faint uppercase">{label}</p>
      <p className="font-bold">{value}</p>
      <p className="text-xs text-muted">{hint}</p>
    </div>
  )
}

/** When you listen: weekdays down, hours across, brighter green for more minutes. */
export function ListeningClock({ cells }: { cells: ClockCell[] }) {
  const grid = useRef<HTMLDivElement>(null)
  const [active, setActive] = useState<ClockCell | null>(null)
  const [focused, setFocused] = useState(false)

  const at = (weekday: number, h: number) =>
    cells.find((c) => c.weekday === weekday && c.hour === h) ?? { weekday, hour: h, minutes: 0 }
  const total = sum(cells)
  const max = Math.max(1, ...cells.map((c) => c.minutes))
  const ranked = cells.filter((c) => c.minutes).sort((a, b) => b.minutes - a.minutes)
  const peak = ranked[0]
  if (!peak) return <p className="p-2 text-sm text-muted">No listening in this period yet.</p>

  const byDay = DAYS.map((_, d) => sum(cells.filter((c) => c.weekday === d)))
  const topDay = byDay.indexOf(Math.max(...byDay))
  const parts = PARTS.map((p) => ({
    ...p,
    minutes: sum(cells.filter((c) => c.hour >= p.from && c.hour < p.to)),
  }))
  const topPart = parts.reduce((a, b) => (b.minutes > a.minutes ? b : a))
  const label = `When you listen: most on ${DAYS[peak.weekday]}s around ${hour(peak.hour)}; ${DAYS[topDay]} is your biggest day.`

  // Arrow keys move the highlighted hour once the chart has focus.
  const onKey = (e: React.KeyboardEvent) => {
    const step = ARROWS[e.key]
    if (!step) return
    e.preventDefault()
    const from = active ?? peak
    setActive(at((from.weekday + step[0] + 7) % 7, (from.hour + step[1] + 24) % 24))
  }

  const shown = active ?? (focused ? peak : null)

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Tile
          label="Busiest hour"
          value={`${DAYS[peak.weekday].slice(0, 3)} ${hour(peak.hour)}`}
          hint={minutes(peak.minutes)}
        />
        <Tile label="Biggest day" value={DAYS[topDay]} hint={`${pct(byDay[topDay], total)} of your listening`} />
        <Tile label="Mostly" value={topPart.name} hint={`${pct(topPart.minutes, total)} of your listening`} />
        <Tile label="Total" value={minutes(total)} hint={duration(total)} />
      </div>

      <div
        ref={grid}
        role="img"
        aria-label={label}
        tabIndex={0}
        onKeyDown={onKey}
        onFocus={() => setFocused(true)}
        onBlur={() => {
          setFocused(false)
          setActive(null)
        }}
        onPointerLeave={() => setActive(null)}
        className="relative space-y-1 rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
      >
        {DAYS.map((day, weekday) => (
          <div key={day} className="flex items-center gap-1.5">
            <span
              className={cn(
                'w-7 text-[11px] transition-colors',
                shown?.weekday === weekday ? 'font-bold text-white' : 'text-faint',
              )}
            >
              {day.slice(0, 3)}
            </span>
            <div className="grid flex-1 grid-cols-24 gap-[3px]">
              {Array.from({ length: 24 }, (_, h) => {
                const cell = at(weekday, h)
                const on = shown?.weekday === weekday && shown.hour === h
                // Light up the hovered day and hour; dim the rest so the cross reads at a glance.
                const dim = shown && shown.weekday !== weekday && shown.hour !== h
                return (
                  <div
                    key={h}
                    data-cell={`${weekday}-${h}`}
                    onPointerEnter={() => setActive(cell)}
                    className={cn(
                      'aspect-square rounded-[3px] bg-accent transition-[opacity,transform,box-shadow] duration-75',
                      on && 'relative z-10 scale-125 shadow-[0_0_0_2px_#fff]',
                    )}
                    style={{ opacity: shade(cell.minutes, max) * (dim ? 0.45 : 1) }}
                  />
                )
              })}
            </div>
          </div>
        ))}
        <div className="flex justify-between pl-9 text-[11px] text-faint">
          {[0, 6, 12, 18, 23].map((h) => (
            <span key={h} className={cn(shown?.hour === h && 'font-bold text-white')}>
              {String(h).padStart(2, '0')}
            </span>
          ))}
        </div>

        {shown && (
          <Tooltip grid={grid.current} cell={shown}>
            <p className="text-xs font-semibold text-muted">
              {DAYS[shown.weekday]} · {hour(shown.hour)}–{hour((shown.hour + 1) % 24)}
            </p>
            <p className="text-base font-bold text-accent">{time(shown.minutes)}</p>
          </Tooltip>
        )}
      </div>

      <div className="space-y-2">
        <div className="flex h-2 gap-0.5 overflow-hidden rounded-full">
          {parts.map((p, i) => (
            <div
              key={p.name}
              className="h-full bg-accent"
              style={{ width: pct(p.minutes, total), opacity: 0.35 + 0.2 * i }}
            />
          ))}
        </div>
        <div className="flex flex-wrap justify-between gap-x-4 gap-y-1 text-xs">
          {parts.map((p, i) => (
            <span key={p.name} className="flex items-center gap-1.5 text-muted">
              <span className="size-2 rounded-full bg-accent" style={{ opacity: 0.35 + 0.2 * i }} />
              {p.name}
              <span className="font-semibold text-white tabular">{pct(p.minutes, total)}</span>
            </span>
          ))}
          <span className="flex items-center gap-1 text-faint" aria-hidden>
            Less
            {[0.05, 0.3, 0.55, 0.8, 1].map((o) => (
              <span key={o} className="size-2.5 rounded-[2px] bg-accent" style={{ opacity: o }} />
            ))}
            More
          </span>
        </div>
      </div>
    </div>
  )
}

/** Sits above the highlighted cell (below it near the top), kept inside the chart. Instant. */
function Tooltip({
  grid,
  cell,
  children,
}: {
  grid: HTMLDivElement | null
  cell: ClockCell
  children: React.ReactNode
}) {
  const target = grid?.querySelector<HTMLElement>(`[data-cell="${cell.weekday}-${cell.hour}"]`)
  if (!grid || !target) return null
  const box = grid.getBoundingClientRect()
  const rect = target.getBoundingClientRect()
  const width = Math.min(180, box.width)
  const centre = rect.left - box.left + rect.width / 2
  const left = Math.min(Math.max(centre - width / 2, 0), box.width - width)
  const below = rect.top - box.top < 70
  return (
    <div
      role="status"
      className="pointer-events-none absolute z-20 rounded-xl border border-white/10 bg-neutral-900/95 px-3 py-2 shadow-xl backdrop-blur"
      style={{
        width,
        left,
        top: below ? rect.bottom - box.top + 8 : undefined,
        bottom: below ? undefined : box.bottom - rect.top + 8,
      }}
    >
      {children}
    </div>
  )
}
