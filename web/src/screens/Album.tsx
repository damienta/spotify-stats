import { motion } from 'framer-motion'
import { ArrowLeft, ExternalLink } from 'lucide-react'

import { Artwork } from '@/components/Artwork'
import BlurText from '@/components/BlurText'
import { History, Ranks, Tile } from '@/components/DetailParts'
import { MaybeLink } from '@/components/MaybeLink'
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
import { cn } from '@/lib/utils'

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

interface Song {
  number: number
  name: string
  hours: number
  url?: string | null
}

/**
 * The album's songs in the record's order, as a compact list: number, name, your minutes.
 * Your most-played song is green; songs you've never played are dimmed. Until Spotify has
 * been asked for the tracklist (usually the next hourly run), your top songs stand in.
 */
function Songs({ page }: { page: AlbumPage }) {
  const inOrder = Boolean(page.tracklist?.length)
  const songs: Song[] = inOrder
    ? page.tracklist!
    : page.top_tracks.map((t, i) => ({ number: i + 1, name: t.name, hours: t.hours, url: t.url }))
  const discs = new Set(page.tracklist?.map((t) => t.disc)).size
  const most = Math.max(...songs.map((s) => s.hours))
  return (
    <Section title={inOrder ? 'Tracklist' : 'Your top songs on it'}>
      <SpotlightCard className="p-2">
        <ol>
          {songs.map((s, i) => {
            const played = s.hours > 0
            const disc = inOrder && discs > 1 ? `${page.tracklist![i].disc}.` : ''
            return (
              <li key={`${disc}${s.number}-${s.name}`}>
                <MaybeLink
                  href={s.url}
                  className="group flex items-baseline gap-3 rounded-lg px-2 py-1.5 text-sm transition-colors hover:bg-white/5"
                >
                  <span className="w-7 shrink-0 text-right text-xs text-faint tabular">
                    {disc}
                    {s.number}
                  </span>
                  <span
                    className={cn(
                      'min-w-0 flex-1 truncate underline-offset-4 group-hover:underline',
                      played ? 'font-semibold' : 'text-faint',
                    )}
                  >
                    {s.name}
                  </span>
                  <span
                    className={cn(
                      'shrink-0 text-xs tabular',
                      played && s.hours === most ? 'font-semibold text-accent' : 'text-muted',
                    )}
                  >
                    {played ? listened(s.hours * 60) : '–'}
                  </span>
                </MaybeLink>
              </li>
            )
          })}
        </ol>
      </SpotlightCard>
    </Section>
  )
}

/** One of your top albums: its songs in order with your plays, and since when. */
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
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <Tile label={timeTile(page.data.minutes).label}>{timeTile(page.data.minutes).value}</Tile>
            <Tile label="Streams">{count(page.data.streams)}</Tile>
            <Tile label="Of all your listening">
              {(page.data.share * 100).toFixed(page.data.share < 0.01 ? 2 : 1)}%
            </Tile>
          </div>
          <div className="grid gap-8 lg:grid-cols-2">
            <Songs page={page.data} />
            <History page={page.data} />
          </div>
        </motion.div>
      )}
    </div>
  )
}
