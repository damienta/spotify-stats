import { ChevronDown } from 'lucide-react'
import { useState } from 'react'

import { Artwork } from '@/components/Artwork'
import BlurText from '@/components/BlurText'
import { MaybeLink } from '@/components/MaybeLink'
import { Minutes } from '@/components/Minutes'
import { Segmented } from '@/components/Segmented'
import SpotlightCard from '@/components/SpotlightCard'
import { Problem, Skeleton } from '@/components/States'
import { Button } from '@/components/ui/button'
import { count } from '@/lib/format'
import { useStat } from '@/lib/queries'
import type { TopRow } from '@/lib/types'

// No genres: Spotify stopped returning them to apps like this one.
type Kind = 'tracks' | 'artists' | 'albums'
type Range = '4_weeks' | '6_months' | '12_months' | 'all_time'

const KINDS: { value: Kind; label: string }[] = [
  { value: 'tracks', label: 'Tracks' },
  { value: 'artists', label: 'Artists' },
  { value: 'albums', label: 'Albums' },
]

const RANGES: { value: Range; label: string }[] = [
  { value: '4_weeks', label: '4 weeks' },
  { value: '6_months', label: '6 months' },
  { value: '12_months', label: '12 months' },
  { value: 'all_time', label: 'All time' },
]

// A short list reads better; the rest (up to 100) is one tap away.
const SHORT_LIST = 10

function Leader({ row, kind }: { row: TopRow; kind: Kind }) {
  return (
    <SpotlightCard className="p-0 transition-colors hover:bg-white/10">
      <MaybeLink href={row.url} className="flex items-center gap-5 p-5">
        <Artwork
          src={row.image}
          name={row.name}
          round={kind === 'artists'}
          className="size-28 shrink-0 text-2xl shadow-xl sm:size-36"
        />
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold text-accent">#1</p>
          <h2 className="text-2xl font-extrabold tracking-tight sm:text-3xl">
            <BlurText key={row.name} text={row.name} delay={60} />
          </h2>
          {row.artist_name && <p className="truncate text-muted">{row.artist_name}</p>}
        </div>
        <div className="shrink-0 text-right">
          <p className="text-lg font-bold">
            <Minutes value={row.hours * 60} />
          </p>
          <p className="text-sm text-muted tabular">{count(row.streams)} streams</p>
        </div>
      </MaybeLink>
    </SpotlightCard>
  )
}

function Row({ row, rank, kind }: { row: TopRow; rank: number; kind: Kind }) {
  return (
    <li>
      <MaybeLink
        href={row.url}
        className="group flex items-center gap-3 rounded-xl p-2 transition-colors hover:bg-white/5"
      >
        <span className="w-7 text-right text-sm font-semibold text-faint tabular">{rank}</span>
        <Artwork
          src={row.image}
          name={row.name}
          round={kind === 'artists'}
          className="size-12 text-xs"
        />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold underline-offset-4 group-hover:underline">
            {row.name}
          </p>
          {row.artist_name && <p className="truncate text-xs text-muted">{row.artist_name}</p>}
        </div>
        <div className="text-right text-xs">
          <p className="font-semibold">
            <Minutes value={row.hours * 60} hours={false} />
          </p>
          <p className="text-faint tabular">{count(row.streams)} streams</p>
        </div>
      </MaybeLink>
    </li>
  )
}

function TopList({ kind, range }: { kind: Kind; range: Range }) {
  const top = useStat<TopRow[]>(`top_${kind}`, range)
  const [expanded, setExpanded] = useState(false)
  if (top.isError) return <Problem error={top.error} onRetry={() => top.refetch()} />
  if (!top.data) return <Skeleton className="h-96" />
  if (!top.data.length) {
    return <p className="py-6 text-center text-sm text-muted">Nothing played in this time yet.</p>
  }
  const [first, ...rest] = top.data
  const shown = expanded ? rest : rest.slice(0, SHORT_LIST - 1)
  return (
    <div className="space-y-3">
      <Leader row={first} kind={kind} />
      {rest.length > 0 && (
        <SpotlightCard className="p-2">
          <ol>
            {shown.map((row, i) => (
              <Row key={`${row.name}-${row.artist_name}`} row={row} rank={i + 2} kind={kind} />
            ))}
          </ol>
          {top.data.length > SHORT_LIST && (
            <div className="flex justify-center p-2">
              <Button variant="glass" size="sm" onClick={() => setExpanded(!expanded)}>
                {expanded ? 'Show top 10' : `Show top ${top.data.length}`}
                <ChevronDown className={expanded ? 'size-4 rotate-180' : 'size-4'} />
              </Button>
            </div>
          )}
        </SpotlightCard>
      )}
    </div>
  )
}

export function Top() {
  const [kind, setKind] = useState<Kind>('tracks')
  const [range, setRange] = useState<Range>('4_weeks')
  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-extrabold tracking-tight">Your top</h1>
      <Segmented options={KINDS} value={kind} onChange={setKind} />
      <Segmented options={RANGES} value={range} onChange={setRange} />
      {/* A new list starts short again. */}
      <TopList key={`${kind}-${range}`} kind={kind} range={range} />
    </div>
  )
}
