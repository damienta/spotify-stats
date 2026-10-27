import { useState } from 'react'

import { Artwork } from '@/components/Artwork'
import BlurText from '@/components/BlurText'
import { Segmented } from '@/components/Segmented'
import { AnimatedLink } from '@/components/skiper/animated-link'
import SpotlightCard from '@/components/SpotlightCard'
import { Problem, Skeleton } from '@/components/States'
import { count, duration } from '@/lib/format'
import { useStat } from '@/lib/queries'
import type { TopRow } from '@/lib/types'

type Kind = 'tracks' | 'artists' | 'albums' | 'genres'
type Range = '4_weeks' | '6_months' | '12_months' | 'all_time'

const KINDS: { value: Kind; label: string }[] = [
  { value: 'tracks', label: 'Tracks' },
  { value: 'artists', label: 'Artists' },
  { value: 'albums', label: 'Albums' },
  { value: 'genres', label: 'Genres' },
]

const RANGES: { value: Range; label: string }[] = [
  { value: '4_weeks', label: '4 weeks' },
  { value: '6_months', label: '6 months' },
  { value: '12_months', label: '12 months' },
  { value: 'all_time', label: 'All time' },
]

const spotifySearch = (row: TopRow) =>
  `https://open.spotify.com/search/${encodeURIComponent([row.name, row.artist_name].filter(Boolean).join(' '))}`

function Leader({ row, kind }: { row: TopRow; kind: Kind }) {
  return (
    <SpotlightCard className="flex items-center gap-4 p-5">
      <Artwork name={row.name} round={kind === 'artists'} className="size-24 shrink-0 text-2xl" />
      <div className="min-w-0">
        <p className="text-xs font-semibold text-accent">#1</p>
        <h2 className="text-2xl font-extrabold tracking-tight">
          <BlurText key={row.name} text={row.name} delay={60} />
        </h2>
        {row.artist_name && <p className="truncate text-muted">{row.artist_name}</p>}
        <p className="mt-1 text-sm text-muted tabular">
          {count(row.streams)} streams · {duration(row.hours * 60)}
        </p>
      </div>
    </SpotlightCard>
  )
}

function TopList({ kind, range }: { kind: Exclude<Kind, 'genres'>; range: Range }) {
  const top = useStat<TopRow[]>(`top_${kind}`, range)
  if (top.isError) return <Problem error={top.error} onRetry={() => top.refetch()} />
  if (!top.data) return <Skeleton className="h-96" />
  if (!top.data.length) {
    return <p className="py-6 text-center text-sm text-muted">Nothing played in this time yet.</p>
  }
  const [first, ...rest] = top.data
  return (
    <div className="space-y-3">
      <Leader row={first} kind={kind} />
      <SpotlightCard className="p-2">
        <ol>
          {rest.map((row, i) => (
            <li
              key={`${row.name}-${row.artist_name}`}
              className="flex items-center gap-3 rounded-xl p-2 hover:bg-white/5"
            >
              <span className="w-6 text-right text-sm font-semibold text-faint tabular">{i + 2}</span>
              <Artwork name={row.name} round={kind === 'artists'} className="size-11 text-xs" />
              <div className="min-w-0 flex-1">
                <AnimatedLink
                  href={spotifySearch(row)}
                  external
                  className="max-w-full truncate text-sm font-semibold"
                >
                  {row.name}
                </AnimatedLink>
                {row.artist_name && <p className="truncate text-xs text-muted">{row.artist_name}</p>}
              </div>
              <div className="text-right text-xs tabular">
                <p className="font-semibold">{count(row.streams)}</p>
                <p className="text-faint">{duration(row.hours * 60)}</p>
              </div>
            </li>
          ))}
        </ol>
      </SpotlightCard>
    </div>
  )
}

export function Top() {
  const [kind, setKind] = useState<Kind>('tracks')
  const [range, setRange] = useState<Range>('4_weeks')
  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-extrabold tracking-tight">Your top</h1>
      <Segmented options={KINDS} value={kind} onChange={setKind} />
      <Segmented options={RANGES} value={range} onChange={setRange} />
      {kind === 'genres' ? (
        <SpotlightCard>
          <p className="py-6 text-center text-sm text-muted">
            Genres are coming: they need artist details from Spotify, which is the next backend
            change.
          </p>
        </SpotlightCard>
      ) : (
        <TopList kind={kind} range={range} />
      )}
    </div>
  )
}
