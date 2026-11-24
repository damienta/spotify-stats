import { motion } from 'framer-motion'
import { ArrowLeft, ExternalLink } from 'lucide-react'

import { Artwork } from '@/components/Artwork'
import BlurText from '@/components/BlurText'
import { History, longDate, Ranks, Tile, Tracks } from '@/components/DetailParts'
import { Section } from '@/components/Section'
import SpotlightCard from '@/components/SpotlightCard'
import { Problem, Skeleton } from '@/components/States'
import { Button } from '@/components/ui/button'
import type { AlbumKey } from '@/lib/album'
import { ApiError } from '@/lib/api'
import { useOpenArtist } from '@/lib/artist'
import { count, listened, timeTile } from '@/lib/format'
import { useAlbum } from '@/lib/queries'
import type { AlbumPage } from '@/lib/types'

// The same parts of the day as the listening clock on Stats.
const PARTS = [
  { key: 'Morning', label: 'morning', hours: '6am–12pm' },
  { key: 'Afternoon', label: 'afternoon', hours: '12pm–6pm' },
  { key: 'Evening', label: 'evening', hours: '6pm–12am' },
  { key: 'Night', label: 'night', hours: '12am–6am' },
] as const

function Hero({ page }: { page: AlbumPage }) {
  const openArtist = useOpenArtist()
  return (
    <div className="flex flex-col items-center gap-5 text-center sm:flex-row sm:items-end sm:text-left">
      <Artwork
        src={page.image}
        name={page.name}
        className="size-40 shrink-0 text-3xl shadow-2xl sm:size-48"
      />
      <div className="min-w-0 flex-1 space-y-3">
        <p className="text-xs font-semibold text-accent uppercase">Album</p>
        <h1 className="text-4xl font-extrabold tracking-tight break-words sm:text-5xl">
          <BlurText key={page.name} text={page.name} delay={60} className="justify-center sm:justify-start" />
        </h1>
        <button
          type="button"
          onClick={() => openArtist(page.artist_name)}
          className="font-semibold text-muted underline-offset-4 hover:text-white hover:underline"
        >
          {page.artist_name}
        </button>
        <Ranks ranks={page.ranks} label="Your rank for this album" />
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

/** When in the day you play it, as one bar split four ways, plus your biggest day. */
function WhenYouPlay({ page }: { page: AlbumPage }) {
  const total = PARTS.reduce((sum, p) => sum + page.time_of_day[p.key], 0)
  if (!total) return null
  const parts = PARTS.map((p) => ({ ...p, share: page.time_of_day[p.key] / total }))
  const most = parts.reduce((a, b) => (b.share > a.share ? b : a))
  return (
    <Section title="When you play it">
      <SpotlightCard className="space-y-4">
        <p className="text-lg font-bold">
          Mostly {most.key === 'Night' ? 'at' : 'in the'}{' '}
          <span className="text-accent">{most.label}</span>
        </p>
        <div
          className="flex h-3 overflow-hidden rounded-full bg-white/10"
          role="img"
          aria-label={parts.map((p) => `${Math.round(p.share * 100)}% ${p.label}`).join(', ')}
        >
          {/* Brighter green for the part of the day you play it most. */}
          {parts.map((p) => (
            <div
              key={p.key}
              className={p.key === most.key ? 'bg-accent' : 'bg-accent/35'}
              style={{ width: `${p.share * 100}%` }}
            />
          ))}
        </div>
        <ul className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-4" aria-hidden="true">
          {parts.map((p) => (
            <li key={p.key}>
              <p className="font-semibold tabular">{Math.round(p.share * 100)}%</p>
              <p className="text-xs text-muted">
                {p.key} · {p.hours}
              </p>
            </li>
          ))}
        </ul>
        {page.biggest_day && (
          <p className="border-t border-white/10 pt-3 text-sm text-muted">
            Your biggest day with it:{' '}
            <span className="font-semibold text-white">{longDate(page.biggest_day.start)}</span>,{' '}
            {listened(page.biggest_day.minutes)}.
          </p>
        )}
      </SpotlightCard>
    </Section>
  )
}

/** One of your top albums: the songs on it you play, since when, and when in the day. */
export function Album({ album, onBack }: { album: AlbumKey; onBack: () => void }) {
  const page = useAlbum(album.name, album.artist)
  const notTop = page.error instanceof ApiError && page.error.status === 404
  return (
    <div className="space-y-8">
      <Button variant="glass" size="sm" onClick={onBack}>
        <ArrowLeft className="size-4" />
        Back
      </Button>
      {notTop ? (
        <p className="glass rounded-2xl p-5 text-sm text-muted">
          There's no page for {album.name} yet. Pages are made for your top 50 albums in each
          range, and rebuilt every hour.
        </p>
      ) : page.isError ? (
        <Problem error={page.error} onRetry={() => page.refetch()} />
      ) : !page.data ? (
        <div className="space-y-4">
          <Skeleton className="h-48" />
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
            <Tile label={timeTile(page.data.minutes).label}>{timeTile(page.data.minutes).value}</Tile>
            <Tile label="Streams">{count(page.data.streams)}</Tile>
            <Tile label="Songs played">{count(page.data.tracks)}</Tile>
            <Tile label="Of all your listening">
              {(page.data.share * 100).toFixed(page.data.share < 0.01 ? 2 : 1)}%
            </Tile>
          </div>
          <div className="grid gap-8 lg:grid-cols-2">
            <Tracks title="Your top songs on it" tracks={page.data.top_tracks} />
            <div className="space-y-8">
              <WhenYouPlay page={page.data} />
              <History page={page.data} />
            </div>
          </div>
        </motion.div>
      )}
    </div>
  )
}
