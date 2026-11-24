import { motion } from 'framer-motion'
import { ArrowLeft, Clock, ExternalLink, Ticket } from 'lucide-react'

import { Artwork } from '@/components/Artwork'
import BlurText from '@/components/BlurText'
import { History, Ranks, Tile, Tracks } from '@/components/DetailParts'
import { MaybeLink } from '@/components/MaybeLink'
import { Section } from '@/components/Section'
import SpotlightCard from '@/components/SpotlightCard'
import { Problem, Skeleton } from '@/components/States'
import { Button } from '@/components/ui/button'
import { useOpenAlbum } from '@/lib/album'
import { ApiError } from '@/lib/api'
import { count, gigDate, listened, timeTile } from '@/lib/format'
import { ticketState } from '@/lib/gigs'
import { useArtist, useStat } from '@/lib/queries'
import type { AlbumRow, ArtistPage, Touring } from '@/lib/types'
import { cn } from '@/lib/utils'

function Hero({ page }: { page: ArtistPage }) {
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
        <Ranks ranks={page.ranks} label="Your rank for this artist" />
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

/**
 * Their albums you play most, as a grid of covers beside the top tracks. Albums with their
 * own page open it; the rest open in Spotify.
 */
function Albums({ artist, albums }: { artist: string; albums: AlbumRow[] }) {
  const openAlbum = useOpenAlbum()
  return (
    <Section title="Your top albums by them">
      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-2">
        {albums.map((a) => {
          const body = (
            <>
              <Artwork src={a.image} name={a.name} className="aspect-square w-full text-xl" />
              <p className="mt-2 truncate text-sm font-semibold underline-offset-4 group-hover:underline">
                {a.name}
              </p>
              <p className="text-xs text-muted">{listened(a.hours * 60)}</p>
            </>
          )
          return (
            <li key={a.name}>
              {a.page ? (
                <button
                  type="button"
                  onClick={() => openAlbum({ name: a.name, artist })}
                  className="group w-full text-left"
                >
                  {body}
                </button>
              ) : (
                <MaybeLink href={a.url} className="group block">
                  {body}
                </MaybeLink>
              )}
            </li>
          )
        })}
      </ul>
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
            <Tile label={timeTile(page.data.minutes).label}>{timeTile(page.data.minutes).value}</Tile>
            <Tile label="Streams">{count(page.data.streams)}</Tile>
            <Tile label="Tracks played">{count(page.data.tracks)}</Tile>
            <Tile label="Of all your listening">
              {page.data.share >= 0.001 ? `${(page.data.share * 100).toFixed(1)}%` : '<0.1%'}
            </Tile>
          </div>
          <History page={page.data} />
          {/* Albums sit beside the tracks on wide screens and below them on phones. */}
          <div className="grid gap-8 lg:grid-cols-2">
            <Tracks title="Your top tracks by them" tracks={page.data.top_tracks} />
            {page.data.top_albums?.length ? (
              <Albums artist={page.data.name} albums={page.data.top_albums} />
            ) : (
              <Gigs name={page.data.name} />
            )}
          </div>
          {page.data.top_albums?.length ? <Gigs name={page.data.name} /> : null}
        </motion.div>
      )}
    </div>
  )
}
