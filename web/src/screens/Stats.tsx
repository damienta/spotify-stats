import { Flame, RefreshCw, Trophy } from 'lucide-react'
import { useState } from 'react'

import { Artwork } from '@/components/Artwork'
import BlurText from '@/components/BlurText'
import { ListeningClock } from '@/components/ListeningClock'
import { MinutesChart } from '@/components/MinutesChart'
import { Section } from '@/components/Section'
import { Segmented } from '@/components/Segmented'
import SpotlightCard from '@/components/SpotlightCard'
import { Button } from '@/components/ui/button'
import { Problem, Skeleton } from '@/components/States'
import { MaybeLink } from '@/components/MaybeLink'
import { Minutes } from '@/components/Minutes'
import { ago, count, duration, minutes, percent } from '@/lib/format'
import { fillPeriod, GRAIN_STAT, type PeriodName } from '@/lib/periods'
import { useRefreshStats, useStat, useStatBuiltAt } from '@/lib/queries'
import type {
  ClockCell,
  Discovery,
  Period,
  Repeat,
  Skips,
  Streaks,
  TopRow,
  Totals,
} from '@/lib/types'

const PERIODS: { value: PeriodName; label: string; long: string }[] = [
  { value: 'today', label: 'Day', long: 'today' },
  { value: 'this_week', label: 'Week', long: 'this week' },
  { value: 'this_month', label: 'Month', long: 'this month' },
  { value: 'this_year', label: 'Year', long: 'this year' },
]

function BigNumber({ period }: { period: PeriodName }) {
  const totals = useStat<Totals>('totals', period)
  const long = PERIODS.find((p) => p.value === period)!.long
  if (totals.isError) return <Problem error={totals.error} onRetry={() => totals.refetch()} />
  return (
    <div className="py-4 text-center">
      <p className="text-sm text-muted">Listening time {long}</p>
      {totals.data ? (
        <>
          <p className="text-6xl font-extrabold tracking-tight text-accent sm:text-7xl tabular">
            <BlurText
              key={`${period}-${totals.data.hours}`}
              text={minutes(totals.data.hours * 60)}
              delay={90}
              className="justify-center"
            />
          </p>
          {totals.data.hours >= 1 && (
            <p className="mt-1 text-lg font-semibold text-muted tabular">
              ({duration(totals.data.hours * 60)})
            </p>
          )}
        </>
      ) : (
        <Skeleton className="mx-auto mt-2 h-16 w-64" />
      )}
    </div>
  )
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <SpotlightCard>
      <p className="text-xs text-muted">{label}</p>
      <p className="text-2xl font-extrabold tabular">{value}</p>
    </SpotlightCard>
  )
}

function Tiles({ period }: { period: PeriodName }) {
  const totals = useStat<Totals>('totals', period)
  const skips = useStat<Skips>('skips', period)
  const t = totals.data
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <Tile label="Streams" value={t ? count(t.streams) : '–'} />
      <Tile label="Artists" value={t ? count(t.artists) : '–'} />
      <Tile label="Tracks" value={t ? count(t.tracks) : '–'} />
      <Tile label="Skip rate" value={skips.data ? percent(skips.data.skip_rate) : '–'} />
    </div>
  )
}

function Chart({ period }: { period: PeriodName }) {
  const minutes = useStat<Period[]>(GRAIN_STAT[period], period)
  const title = period === 'today' ? 'Minutes by hour' : period === 'this_year' ? 'Minutes by month' : 'Minutes by day'
  return (
    <Section title={title}>
      <SpotlightCard>
        {minutes.isError ? (
          <Problem error={minutes.error} onRetry={() => minutes.refetch()} />
        ) : minutes.data ? (
          <MinutesChart points={fillPeriod(period, minutes.data)} height={180} />
        ) : (
          <Skeleton className="h-44" />
        )}
      </SpotlightCard>
    </Section>
  )
}

function Clock({ period }: { period: PeriodName }) {
  const clock = useStat<ClockCell[]>('listening_clock', period)
  return (
    <Section title="When you listen">
      <SpotlightCard>
        {clock.isError ? (
          <Problem error={clock.error} onRetry={() => clock.refetch()} />
        ) : clock.data ? (
          <ListeningClock cells={clock.data} />
        ) : (
          <Skeleton className="h-40" />
        )}
      </SpotlightCard>
    </Section>
  )
}

function StreakCards() {
  const streaks = useStat<Streaks>('streaks')
  const s = streaks.data
  return (
    <div className="grid grid-cols-2 gap-3">
      <SpotlightCard>
        <Flame className="size-5 text-accent" />
        <p className="mt-2 text-xs text-muted">Current streak</p>
        <p className="text-2xl font-extrabold tabular">{s ? `${count(s.current.days)} days` : '–'}</p>
      </SpotlightCard>
      <SpotlightCard>
        <Trophy className="size-5 text-accent" />
        <p className="mt-2 text-xs text-muted">Longest streak</p>
        <p className="text-2xl font-extrabold tabular">{s ? `${count(s.longest.days)} days` : '–'}</p>
        {s?.longest.start && (
          <p className="text-[11px] text-faint">
            {s.longest.start} to {s.longest.end}
          </p>
        )}
      </SpotlightCard>
    </div>
  )
}

function Favourite({ label, row, round }: { label: string; row?: TopRow; round?: boolean }) {
  return (
    <SpotlightCard className="p-0 transition-colors hover:bg-white/10">
      <MaybeLink href={row?.url} className="flex items-center gap-3 p-4">
        {row && (
          <Artwork src={row.image} name={row.name} round={round} className="size-14 shrink-0" />
        )}
        <div className="min-w-0">
          <p className="text-xs text-muted">{label}</p>
          <p className="truncate text-lg font-bold">{row?.name ?? '–'}</p>
          {row && (
            <p className="truncate text-xs text-faint">
              <Minutes value={row.hours * 60} hours={false} />
              {row.artist_name && ` · ${row.artist_name}`}
            </p>
          )}
        </div>
      </MaybeLink>
    </SpotlightCard>
  )
}

function Favourites({ period }: { period: PeriodName }) {
  const artists = useStat<TopRow[]>('top_artists', period)
  const tracks = useStat<TopRow[]>('top_tracks', period)
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <Favourite label="Top artist" row={artists.data?.[0]} round />
      <Favourite label="Top track" row={tracks.data?.[0]} />
    </div>
  )
}

function Lists({ period }: { period: PeriodName }) {
  const repeat = useStat<Repeat[]>('on_repeat', period)
  const discoveries = useStat<Discovery[]>('discoveries', period)
  return (
    <div className="grid gap-8 lg:grid-cols-2">
      <Section title="On repeat">
        <SpotlightCard className="p-2">
          {repeat.data?.length ? (
            <ul>
              {repeat.data.slice(0, 5).map((r) => (
                <li key={`${r.track_name}-${r.day}`}>
                  <MaybeLink
                    href={r.url}
                    className="flex items-center gap-3 rounded-xl p-2 hover:bg-white/5"
                  >
                    <Artwork src={r.image} name={r.track_name} className="size-11 text-xs" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold">{r.track_name}</p>
                      <p className="truncate text-xs text-muted">
                        {r.artist_name} · {r.day}
                      </p>
                    </div>
                    <span className="text-sm font-bold text-accent tabular">{r.streams}×</span>
                  </MaybeLink>
                </li>
              ))}
            </ul>
          ) : (
            <p className="py-6 text-center text-sm text-muted">
              {repeat.isPending ? 'Loading…' : 'No repeats yet.'}
            </p>
          )}
        </SpotlightCard>
      </Section>
      <Section title="New to you">
        <SpotlightCard className="p-2">
          {discoveries.data?.length ? (
            <ul>
              {discoveries.data.slice(0, 5).map((d) => (
                <li key={d.artist_name}>
                  <MaybeLink
                    href={d.url}
                    className="flex items-center gap-3 rounded-xl p-2 hover:bg-white/5"
                  >
                    <Artwork src={d.image} name={d.artist_name} round className="size-11 text-xs" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold">{d.artist_name}</p>
                      <p className="text-xs text-muted">First heard {d.first_played}</p>
                    </div>
                    <span className="text-xs text-faint">
                      <Minutes value={d.minutes} hours={false} />
                    </span>
                  </MaybeLink>
                </li>
              ))}
            </ul>
          ) : (
            <p className="py-6 text-center text-sm text-muted">
              {discoveries.isPending ? 'Loading…' : 'No new artists in this time.'}
            </p>
          )}
        </SpotlightCard>
      </Section>
    </div>
  )
}

/** "Updated 12m ago", and a button to fetch the latest build now. */
function Freshness({ period }: { period: PeriodName }) {
  const builtAt = useStatBuiltAt('totals', period)
  const refresh = useRefreshStats()
  return (
    <div className="flex items-center gap-2 text-xs text-muted">
      {builtAt.data && <span>Updated {ago(builtAt.data)} ago</span>}
      <Button
        variant="ghost"
        size="icon"
        onClick={refresh}
        aria-label="Refresh stats"
        title="Refresh stats"
        className="size-7"
      >
        <RefreshCw className={builtAt.isFetching ? 'size-3.5 animate-spin' : 'size-3.5'} />
      </Button>
    </div>
  )
}

export function Stats() {
  const [period, setPeriod] = useState<PeriodName>('this_week')
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-2 pr-12">
        <h1 className="text-3xl font-extrabold tracking-tight">Your stats</h1>
        <Freshness period={period} />
      </div>
      <Segmented options={PERIODS} value={period} onChange={setPeriod} />
      <BigNumber period={period} />
      <Tiles period={period} />
      <Chart period={period} />
      <Favourites period={period} />
      <Clock period={period} />
      <StreakCards />
      <Lists period={period} />
    </div>
  )
}
