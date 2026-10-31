import { motion } from 'framer-motion'
import { ArrowLeft, Clock, ExternalLink, Ticket } from 'lucide-react'
import type { ReactNode } from 'react'

import { Artwork } from '@/components/Artwork'
import BlurText from '@/components/BlurText'
import { MaybeLink } from '@/components/MaybeLink'
import { Minutes } from '@/components/Minutes'
import { type ChartPoint, MinutesChart } from '@/components/MinutesChart'
import { Section } from '@/components/Section'
import SpotlightCard from '@/components/SpotlightCard'
import { Problem, Skeleton } from '@/components/States'
import { Button } from '@/components/ui/button'
import { ApiError } from '@/lib/api'
import { ago, count, gigDate, minutes } from '@/lib/format'
import { ticketState } from '@/lib/gigs'
import { useArtist, useStat } from '@/lib/queries'
import type { ArtistPage, Period, Touring } from '@/lib/types'
import { cn } from '@/lib/utils'

const RANGES: { key: keyof ArtistPage['ranks']; label: string }[] = [
  { key: '4_weeks', label: '4 weeks' },
  { key: '6_months', label: '6 months' },
  { key: '12_months', label: '12 months' },
  { key: 'all_time', label: 'all time' },
]

const pad = (n: number) => String(n).padStart(2, '0')

/** Every month from their first play to now, so gaps show as empty bars. */
function months(data: Period[], now = new Date()): ChartPoint[] {
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

const longDate = (iso: string) =>
  new Date(iso.replace(' ', 'T')).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })

function Tile({ label, children }: { label: string; children: ReactNode }) {
  return (
    <SpotlightCard>
      <p className="text-xs text-muted">{label}</p>
      <p className="text-2xl font-extrabold tabular">{children}</p>
    </SpotlightCard>
  )
}

function Hero({ page }: { page: ArtistPage }) {
  const ranked = RANGES.filter((r) => page.ranks[r.key])
  return (
    <div className="flex flex-col items-center gap-5 text-center sm:flex-row sm:items-end sm:text-left">
      <Artwork
        src={page.image}
        name={page.name}
        round
        className="size-36 shrink-0 text-3xl shadow-2xl sm:size-44"
      />
      <div className="min-w-0 flex-1 space-y-3">
        <p className="text-xs font-semibold text-accent uppercase">Artist</p>
        <h1 className="text-4xl font-extrabold tracking-tight break-words sm:text-5xl">
          <BlurText key={page.name} text={page.name} delay={60} className="justify-center sm:justify-start" />
        </h1>
        <div className="flex flex-wrap justify-center gap-2 sm:justify-start">
          {ranked.map((r) => (
            <span
              key={r.key}
              className={cn(
                'rounded-full px-3 py-1 text-xs font-semibold',
                page.ranks[r.key] === 1 ? 'bg-accent text-black' : 'glass text-muted',
              )}
            >
              #{page.ranks[r.key]} {r.label}
            </span>
          ))}
        </div>
      </div>
      {page.url && (
        <Button asChild className="shrink-0">
          <a href={page.url} target="_blank" rel="noopener noreferrer">
            <ExternalLink className="size-4" />
            Open in Spotify
          </a>
        </Button>
      )}
    </div>
  )
}

function History({ page }: { page: ArtistPage }) {
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
            Busiest month: {busiest.label}, {minutes(busiest.minutes)}
          </p>
        )}
      </SpotlightCard>
    </Section>
  )
}

function Tracks({ page }: { page: ArtistPage }) {
  return (
    <Section title="Your top tracks by them">
      <SpotlightCard className="p-2">
        <ol>
          {page.top_tracks.map((t, i) => (
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

function Gigs({ name }: { name: string }) {
  const touring = useStat<Touring[]>('concerts')
  const tour = touring.data?.find((t) => t.artist.toLowerCase() === name.toLowerCase())
  if (!tour?.events.length) return null
  const now = Date.now()
  return (
    <Section title="Playing the UK">
      <SpotlightCard className="p-2">
        <ul>
          {tour.events.map((gig) => {
            const tickets = ticketState(gig, now)
            return (
              <li key={gig.url + gig.date} className="flex items-center gap-3 rounded-xl p-2">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold">{gigDate(gig.date)}</p>
                  <p className="truncate text-xs text-muted">
                    {[gig.venue, gig.city].filter(Boolean).join(', ')}
                  </p>
                </div>
                <a
                  href={gig.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={cn(
                    'flex h-8 shrink-0 items-center gap-1.5 rounded-full px-3 text-xs font-bold transition-colors',
                    tickets.buyable
                      ? 'bg-accent text-black hover:bg-accent-bright'
                      : 'glass text-white hover:bg-white/10',
                  )}
                >
                  {tickets.buyable ? <Ticket className="size-3.5" /> : <Clock className="size-3.5" />}
                  {tickets.label}
                </a>
              </li>
            )
          })}
        </ul>
      </SpotlightCard>
    </Section>
  )
}

/** One of your top artists: how much you play them, since when, and which songs. */
export function Artist({ name, onBack }: { name: string; onBack: () => void }) {
  const page = useArtist(name)
  const notTop = page.error instanceof ApiError && page.error.status === 404
  return (
    <div className="space-y-8">
      <Button variant="glass" size="sm" onClick={onBack}>
        <ArrowLeft className="size-4" />
        Back
      </Button>

      {notTop ? (
        <p className="glass rounded-2xl p-5 text-sm text-muted">
          There's no page for {name} yet. Pages are made for your top 50 artists in each range,
          and rebuilt every hour.
        </p>
      ) : page.isError ? (
        <Problem error={page.error} onRetry={() => page.refetch()} />
      ) : !page.data ? (
        <div className="space-y-4">
          <Skeleton className="h-44" />
          <Skeleton className="h-24" />
          <Skeleton className="h-64" />
        </div>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
          className="space-y-8"
        >
          <Hero page={page.data} />
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Tile label="Minutes">{count(page.data.minutes)}</Tile>
            <Tile label="Streams">{count(page.data.streams)}</Tile>
            <Tile label="Tracks played">{count(page.data.tracks)}</Tile>
            <Tile label="Of all your listening">
              {page.data.share >= 0.001 ? `${(page.data.share * 100).toFixed(1)}%` : '<0.1%'}
            </Tile>
          </div>
          <History page={page.data} />
          <div className="grid gap-8 lg:grid-cols-2">
            <Tracks page={page.data} />
            <Gigs name={page.data.name} />
          </div>
        </motion.div>
      )}
    </div>
  )
}
