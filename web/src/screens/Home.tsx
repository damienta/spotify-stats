import { Artwork } from '@/components/Artwork'
import BlurText from '@/components/BlurText'
import { MaybeLink } from '@/components/MaybeLink'
import { Minutes } from '@/components/Minutes'
import { MinutesChart } from '@/components/MinutesChart'
import { NowPlayingCard } from '@/components/NowPlayingCard'
import { GigsTeaser } from '@/components/GigsTeaser'
import { Section } from '@/components/Section'
import SpotlightCard from '@/components/SpotlightCard'
import { Problem, Skeleton } from '@/components/States'
import { ago, count, greeting } from '@/lib/format'
import { fillPeriod } from '@/lib/periods'
import { useMe, useRecent, useStat } from '@/lib/queries'
import type { Period, TopRow, Totals } from '@/lib/types'

function Header() {
  const me = useMe()
  const name = me.data?.display_name
  return (
    <header className="pr-24 md:pr-0">
      {/* The greeting un-blurs word by word; screen readers get the plain sentence. */}
      <h1 className="min-h-[2.5em] text-4xl font-extrabold tracking-tight sm:text-5xl">
        <span className="sr-only">
          {greeting()}, {name}
        </span>
        <BlurText text={`${greeting()},`} delay={80} />
        {name && <BlurText key={name} text={name} delay={80} className="text-accent" />}
      </h1>
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

/** Today's top artist or track, with its picture. */
function TodayTop({ label, row, round }: { label: string; row?: TopRow; round?: boolean }) {
  return (
    <SpotlightCard className="p-0 transition-colors hover:bg-white/10">
      <MaybeLink href={row?.url} className="flex items-center gap-3 p-4">
        {row ? (
          <>
            <Artwork src={row.image} name={row.name} round={round} className="size-14 shrink-0" />
            <div className="min-w-0">
              <p className="text-xs text-muted">{label}</p>
              <p className="truncate font-bold">{row.name}</p>
              <p className="truncate text-xs text-muted">
                <Minutes value={row.hours * 60} hours={false} />
                {row.artist_name && ` · ${row.artist_name}`}
              </p>
            </div>
          </>
        ) : (
          <div>
            <p className="text-xs text-muted">{label}</p>
            <p className="font-bold">–</p>
          </div>
        )}
      </MaybeLink>
    </SpotlightCard>
  )
}

function Today() {
  const totals = useStat<Totals>('totals', 'today')
  const hours = useStat<Period[]>('minutes_by_hour', 'today')
  const artists = useStat<TopRow[]>('top_artists', 'today')
  const tracks = useStat<TopRow[]>('top_tracks', 'today')
  const t = totals.data
  return (
    <Section title="Today" className="h-full">
      <div className="grid grid-cols-2 gap-3">
        <Metric label="Minutes" value={t ? count(t.hours * 60) : '–'} />
        <Metric label="Streams" value={t ? count(t.streams) : '–'} />
        <Metric label="Artists" value={t ? count(t.artists) : '–'} />
        <Metric label="Tracks" value={t ? count(t.tracks) : '–'} />
      </div>
      {/* Grows so Today ends level with Recently played beside it. */}
      <SpotlightCard className="flex min-h-40 flex-1 flex-col">
        <p className="mb-2 text-xs text-muted">Minutes by hour</p>
        {hours.isError ? (
          <Problem error={hours.error} onRetry={() => hours.refetch()} />
        ) : hours.data ? (
          <div className="min-h-28 flex-1">
            <MinutesChart points={fillPeriod('today', hours.data)} height="100%" />
          </div>
        ) : (
          <Skeleton className="h-28 flex-1" />
        )}
      </SpotlightCard>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
        <TodayTop label="Top artist today" row={artists.data?.[0]} round />
        <TodayTop label="Top track today" row={tracks.data?.[0]} />
      </div>
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
                <a
                  key={a.name}
                  href={a.url ?? undefined}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group w-28 shrink-0 text-center"
                >
                  <Artwork
                    src={a.image}
                    name={a.name}
                    round
                    className="size-28 text-xl transition-transform group-hover:scale-105"
                  />
                  <p className="mt-2 truncate text-sm font-semibold">{a.name}</p>
                  <p className="text-xs text-muted">
                    <Minutes value={a.hours * 60} hours={false} />
                  </p>
                </a>
              ))
            : Array.from({ length: 6 }, (_, i) => (
                <Skeleton key={i} className="size-28 shrink-0 rounded-full" />
              ))}
        </div>
      )}
    </Section>
  )
}

function RecentlyPlayed() {
  const recent = useRecent(10)
  return (
    <Section title="Recently played" className="h-full">
      <SpotlightCard className="flex-1 p-2">
        {recent.isError ? (
          <Problem error={recent.error} onRetry={() => recent.refetch()} />
        ) : !recent.data ? (
          <Skeleton className="h-64" />
        ) : (
          <ul>
            {recent.data.items.map(({ played_at, track }) => (
              <li key={played_at}>
                <a
                  href={track.url ?? undefined}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 rounded-xl p-2 hover:bg-white/5"
                >
                  <Artwork src={track.image} name={track.name ?? '?'} className="size-11" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold">{track.name}</p>
                    <p className="truncate text-xs text-muted">{track.artists.join(', ')}</p>
                  </div>
                  <span className="text-xs text-faint tabular">{ago(played_at)}</span>
                </a>
              </li>
            ))}
          </ul>
        )}
      </SpotlightCard>
    </Section>
  )
}

export function Home({ onSeeAll, onGigs }: { onSeeAll: () => void; onGigs: () => void }) {
  return (
    <div className="space-y-8">
      <Header />
      <NowPlayingCard />
      <GigsTeaser onOpen={onGigs} />
      <div className="grid gap-8 lg:grid-cols-2">
        <Today />
        <RecentlyPlayed />
      </div>
      <TopArtists onSeeAll={onSeeAll} />
    </div>
  )
}
