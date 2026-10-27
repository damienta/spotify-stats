import { LogOut } from 'lucide-react'

import { Artwork } from '@/components/Artwork'
import { MinutesChart } from '@/components/MinutesChart'
import { NowPlayingCard } from '@/components/NowPlayingCard'
import { Section } from '@/components/Section'
import SpotlightCard from '@/components/SpotlightCard'
import { Problem, Skeleton } from '@/components/States'
import { Button } from '@/components/ui/button'
import { logout } from '@/lib/api'
import { ago, count, duration, greeting } from '@/lib/format'
import { fillPeriod } from '@/lib/periods'
import { useMe, useRecent, useStat } from '@/lib/queries'
import type { Period, TopRow, Totals } from '@/lib/types'

function Header() {
  const me = useMe()
  return (
    <header className="flex items-center justify-between">
      <div>
        <p className="text-sm text-muted">{greeting()}</p>
        <h1 className="text-2xl font-extrabold tracking-tight">{me.data?.display_name ?? ' '}</h1>
      </div>
      <Button variant="glass" size="icon" onClick={logout} aria-label="Log out">
        <LogOut className="size-4" />
      </Button>
    </header>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <SpotlightCard>
      <p className="text-xs text-muted">{label}</p>
      <p className="text-3xl font-extrabold tabular">{value}</p>
    </SpotlightCard>
  )
}

function Today() {
  const totals = useStat<Totals>('totals', 'today')
  const hours = useStat<Period[]>('minutes_by_hour', 'today')
  return (
    <Section title="Today">
      <div className="grid grid-cols-2 gap-3">
        <Metric label="Minutes" value={totals.data ? count(totals.data.hours * 60) : '–'} />
        <Metric label="Streams" value={totals.data ? count(totals.data.streams) : '–'} />
      </div>
      <SpotlightCard>
        <p className="mb-2 text-xs text-muted">By hour</p>
        {hours.isError ? (
          <Problem error={hours.error} onRetry={() => hours.refetch()} />
        ) : hours.data ? (
          <MinutesChart points={fillPeriod('today', hours.data)} height={110} />
        ) : (
          <Skeleton className="h-28" />
        )}
      </SpotlightCard>
    </Section>
  )
}

function TopArtists({ onSeeAll }: { onSeeAll: () => void }) {
  const top = useStat<TopRow[]>('top_artists', '4_weeks')
  return (
    <Section
      title="Your top artists recently"
      action={
        <button
          onClick={onSeeAll}
          className="text-sm font-semibold text-muted underline-offset-4 hover:text-white hover:underline"
        >
          See all
        </button>
      }
    >
      {top.isError ? (
        <Problem error={top.error} onRetry={() => top.refetch()} />
      ) : (
        <div className="-mx-4 flex gap-4 overflow-x-auto px-4 pb-2 [scrollbar-width:none]">
          {top.data
            ? top.data.slice(0, 10).map((a) => (
                <div key={a.name} className="w-24 shrink-0 text-center">
                  <Artwork name={a.name} round className="size-24 text-xl" />
                  <p className="mt-2 truncate text-sm font-semibold">{a.name}</p>
                  <p className="text-xs text-muted">{duration(a.hours * 60)}</p>
                </div>
              ))
            : Array.from({ length: 6 }, (_, i) => (
                <Skeleton key={i} className="size-24 shrink-0 rounded-full" />
              ))}
        </div>
      )}
    </Section>
  )
}

function RecentlyPlayed() {
  const recent = useRecent(10)
  return (
    <Section title="Recently played">
      <SpotlightCard className="p-2">
        {recent.isError ? (
          <Problem error={recent.error} onRetry={() => recent.refetch()} />
        ) : !recent.data ? (
          <Skeleton className="h-64" />
        ) : (
          <ul>
            {recent.data.items.map(({ played_at, track }) => (
              <li key={played_at} className="flex items-center gap-3 rounded-xl p-2 hover:bg-white/5">
                <Artwork src={track.image} name={track.name ?? '?'} className="size-11" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold">{track.name}</p>
                  <p className="truncate text-xs text-muted">{track.artists.join(', ')}</p>
                </div>
                <span className="text-xs text-faint tabular">{ago(played_at)}</span>
              </li>
            ))}
          </ul>
        )}
      </SpotlightCard>
    </Section>
  )
}

export function Home({ onSeeAll }: { onSeeAll: () => void }) {
  return (
    <div className="space-y-8">
      <Header />
      <NowPlayingCard />
      <div className="grid gap-8 lg:grid-cols-2">
        <Today />
        <RecentlyPlayed />
      </div>
      <TopArtists onSeeAll={onSeeAll} />
    </div>
  )
}
