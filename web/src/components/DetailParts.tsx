// The parts artist and album pages share: rank tiles, stat tiles, the month-by-month chart
// and the top songs list.

import type { ReactNode } from 'react'

import { Artwork } from '@/components/Artwork'
import { MaybeLink } from '@/components/MaybeLink'
import { Minutes } from '@/components/Minutes'
import { type ChartPoint, MinutesChart } from '@/components/MinutesChart'
import { Section } from '@/components/Section'
import SpotlightCard from '@/components/SpotlightCard'
import { ago, count, listened } from '@/lib/format'
import type { Period, RankWindow, TopRow } from '@/lib/types'
import { cn } from '@/lib/utils'

/** What the history card needs from an artist or album page. */
interface Played {
  first_played: string
  first_track: string
  last_played: string
  minutes_by_month: Period[]
}

export const RANGES: { key: RankWindow; label: string }[] = [
  { key: '4_weeks', label: '4 weeks' },
  { key: '6_months', label: '6 months' },
  { key: '12_months', label: '12 months' },
  { key: 'all_time', label: 'all time' },
]

const pad = (n: number) => String(n).padStart(2, '0')

/** Every month from their first play to now, so gaps show as empty bars. */
export function months(data: Period[], now = new Date()): ChartPoint[] {
  const played = data.find((p) => p.minutes > 0)
  if (!played) return []
  const byMonth = new Map(data.map((p) => [p.start.slice(0, 7), p.minutes]))
  const first = new Date(`${played.start.slice(0, 7)}-01T12:00:00`)
  const points: ChartPoint[] = []
  const busiest = Math.max(...data.map((p) => p.minutes))
  for (let d = first; d <= now; d = new Date(d.getFullYear(), d.getMonth() + 1, 1, 12)) {
    const value = byMonth.get(`${d.getFullYear()}-${pad(d.getMonth() + 1)}`) ?? 0
    points.push({
      label: d.toLocaleDateString('en-GB', { month: 'short', year: '2-digit' }),
      minutes: value,
      highlight: value === busiest,
    })
  }
  return points
}

export const longDate = (iso: string) =>
  new Date(iso.replace(' ', 'T')).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })

export function Tile({ label, children }: { label: string; children: ReactNode }) {
  return (
    <SpotlightCard>
      <p className="text-xs text-muted">{label}</p>
      <p className="text-2xl font-extrabold tabular">{children}</p>
    </SpotlightCard>
  )
}

/**
 * Your rank for this artist in each range, as four tiles: the number big, the range small
 * underneath, so "#4" and "4 weeks" can't run together. Your best rank is filled green; on a
 * tie, the most recent range, since that's the one that says how much you play them now.
 */
export function Ranks({ ranks, label }: { ranks: Record<RankWindow, number | null>; label: string }) {
  const ranked = RANGES.map((r) => ranks[r.key]).filter((n): n is number => n != null)
  if (!ranked.length) return null
  const best = RANGES.find((r) => ranks[r.key] === Math.min(...ranked))?.key
  return (
    <ul className="mx-auto grid max-w-md grid-cols-4 gap-2 sm:mx-0" aria-label={label}>
      {RANGES.map((r) => {
        const rank = ranks[r.key]
        const top = r.key === best
        return (
          <li
            key={r.key}
            className={cn(
              'rounded-2xl px-2 py-2.5 text-center',
              top ? 'bg-accent text-black' : 'glass',
            )}
          >
            <p aria-hidden="true" className={cn('text-2xl font-extrabold tabular sm:text-3xl', rank == null && 'text-faint')}>
              {rank == null ? '–' : `#${rank}`}
            </p>
            <p aria-hidden="true" className={cn('text-xs', top ? 'font-semibold' : 'text-muted')}>
              {r.label}
            </p>
            {/* Screen readers hear "number 4 over 4 weeks", not "hash 4 4 weeks". */}
            <span className="sr-only">
              {rank == null ? `Not in your top 100 over ${r.label}` : `Number ${rank} over ${r.label}`}
            </span>
          </li>
        )
      })}
    </ul>
  )
}


export function History({ page }: { page: Played }) {
  const points = months(page.minutes_by_month)
  const busiest = points.find((p) => p.highlight)
  return (
    <Section title="Minutes by month">
      <SpotlightCard className="space-y-3">
        <p className="text-sm text-muted">
          First played on <span className="font-semibold text-white">{longDate(page.first_played)}</span>
          {page.first_track && (
            <>
              {' '}
              with <span className="font-semibold text-white">{page.first_track}</span>
            </>
          )}
          . Last played {ago(page.last_played.replace(' ', 'T'))} ago.
        </p>
        <MinutesChart points={points} height={160} />
        {busiest && (
          <p className="text-xs text-faint">
            Busiest month: {busiest.label}, {listened(busiest.minutes)}
          </p>
        )}
      </SpotlightCard>
    </Section>
  )
}

export function Tracks({ title, tracks }: { title: string; tracks: TopRow[] }) {
  return (
    <Section title={title}>
      <SpotlightCard className="p-2">
        <ol>
          {tracks.map((t, i) => (
            <li key={t.name}>
              <MaybeLink
                href={t.url}
                className="group flex items-center gap-3 rounded-xl p-2 transition-colors hover:bg-white/5"
              >
                <span className="w-6 text-right text-sm font-semibold text-faint tabular">{i + 1}</span>
                <Artwork src={t.image} name={t.name} className="size-11 text-xs" />
                <p className="min-w-0 flex-1 truncate text-sm font-semibold underline-offset-4 group-hover:underline">
                  {t.name}
                </p>
                <div className="text-right text-xs">
                  <p className="font-semibold">
                    <Minutes value={t.hours * 60} hours={false} />
                  </p>
                  <p className="text-faint tabular">{count(t.streams)} streams</p>
                </div>
              </MaybeLink>
            </li>
          ))}
        </ol>
      </SpotlightCard>
    </Section>
  )
}
