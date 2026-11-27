import { motion } from 'framer-motion'
import { ExternalLink } from 'lucide-react'
import { type ReactNode, useState } from 'react'

import { Artwork } from '@/components/Artwork'
import BlurText from '@/components/BlurText'
import { History, RANGES, Ranks, Tile } from '@/components/DetailParts'
import { MaybeLink } from '@/components/MaybeLink'
import { Section } from '@/components/Section'
import { Segmented } from '@/components/Segmented'
import SpotlightCard from '@/components/SpotlightCard'
import { Problem, Skeleton } from '@/components/States'
import { Button } from '@/components/ui/button'
import type { AlbumKey } from '@/lib/album'
import { ApiError } from '@/lib/api'
import { useOpenArtist } from '@/lib/artist'
import { count, listened, timeTile } from '@/lib/format'
import { fadeTransition } from '@/lib/motion'
import { useAlbum } from '@/lib/queries'
import type { AlbumPage, RankWindow } from '@/lib/types'
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
          <BlurText key={page.name} text={page.name} delay={0} className="justify-center sm:justify-start" />
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

type Order = 'album' | 'plays'

const ORDERS: { value: Order; label: string }[] = [
  { value: 'album', label: 'Album order' },
  { value: 'plays', label: 'Most played' },
]

const RANGE_OPTIONS = RANGES.map((r) => ({
  value: r.key,
  label: r.label[0].toUpperCase() + r.label.slice(1),
}))

interface Song {
  key: string
  // The song's place on the record ("2.4" on a second disc), kept when sorted by plays.
  number: string
  name: string
  hours: number
  url?: string | null
}

/** The songs to list: the tracklist for a range, or your top songs until it's been fetched. */
function songsFor(page: AlbumPage, range: RankWindow): Song[] {
  if (!page.tracklist?.length) {
    return page.top_tracks.map((t, i) => ({
      key: t.name,
      number: String(i + 1),
      name: t.name,
      hours: t.hours,
      url: t.url,
    }))
  }
  const discs = new Set(page.tracklist.map((t) => t.disc)).size
  return page.tracklist.map((t) => ({
    key: `${t.disc}.${t.number}-${t.name}`,
    number: discs > 1 ? `${t.disc}.${t.number}` : String(t.number),
    name: t.name,
    hours: range === 'all_time' ? t.hours : (t.hours_by_range?.[range] ?? 0),
    url: t.url,
  }))
}

/**
 * The album's songs in the record's order, as a compact list: number, name, your minutes.
 * Sort by plays, or pick a range to see what you play from it lately. Your most-played song
 * is green; songs you haven't played are dimmed. Until Spotify has been asked for the
 * tracklist (usually the next hourly run), your top songs stand in.
 */
function Songs({ page }: { page: AlbumPage }) {
  const [range, setRange] = useState<RankWindow>('all_time')
  const [order, setOrder] = useState<Order>('album')
  const inOrder = Boolean(page.tracklist?.length)
  // Pages built before the ranges were added have no per-range minutes yet.
  const hasRanges = Boolean(page.tracklist?.some((t) => t.hours_by_range))
  const listed = songsFor(page, range)
  const songs =
    order === 'plays' && inOrder ? [...listed].sort((a, b) => b.hours - a.hours) : listed
  const most = Math.max(0, ...songs.map((s) => s.hours))
  const rangeLabel = RANGES.find((r) => r.key === range)?.label
  return (
    <Section
      title={inOrder ? 'Tracklist' : 'Your top songs on it'}
      action={
        inOrder && (
          <Segmented
            options={ORDERS}
            value={order}
            onChange={setOrder}
            className="shrink-0 [&_button]:whitespace-nowrap"
          />
        )
      }
    >
      {hasRanges && <Segmented options={RANGE_OPTIONS} value={range} onChange={setRange} />}
      <SpotlightCard className="p-2">
        {most === 0 && (
          <p className="px-2 pt-1.5 pb-2 text-sm text-muted">
            You haven't played it in the last {rangeLabel}.
          </p>
        )}
        <ol>
          {songs.map((s) => {
            const played = s.hours > 0
            return (
              <motion.li key={s.key} layout="position" transition={{ duration: 0.25 }}>
                <MaybeLink
                  href={s.url}
                  className="group flex items-baseline gap-3 rounded-lg px-2 py-1.5 text-sm transition-colors hover:bg-white/5"
                >
                  <span className="w-7 shrink-0 text-right text-xs text-faint tabular">
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
              </motion.li>
            )
          })}
        </ol>
      </SpotlightCard>
    </Section>
  )
}

const pct = (share: number) => `${(share * 100).toFixed(share < 0.1 ? 1 : 0)}%`

function Fact({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-2.5">
      <p className="text-sm text-muted">{label}</p>
      <div className="min-w-0 text-right">
        <p className="truncate font-semibold">{value}</p>
        {hint && <p className="text-xs text-faint">{hint}</p>}
      </div>
    </div>
  )
}

/** A few things worked out from the page: favourite song, what you play lately, and more. */
function Highlights({ page }: { page: AlbumPage }) {
  const songs = songsFor(page, 'all_time')
  const favourite = [...songs].sort((a, b) => b.hours - a.hours)[0]
  const lately = page.tracklist?.some((t) => t.hours_by_range)
    ? [...songsFor(page, '4_weeks')].sort((a, b) => b.hours - a.hours)[0]
    : undefined
  const days = Math.max(
    1,
    (Date.now() - new Date(page.first_played.replace(' ', 'T')).getTime()) / 86_400_000,
  )
  const ofArtist = page.artist_minutes ? page.minutes / page.artist_minutes : null
  return (
    <Section title="Highlights">
      <SpotlightCard className="divide-y divide-white/10 py-2">
        {favourite && favourite.hours > 0 && (
          <Fact
            label="Favourite song"
            value={favourite.name}
            hint={`${listened(favourite.hours * 60)}, ${pct((favourite.hours * 60) / page.minutes)} of your time on it`}
          />
        )}
        {lately && lately.hours > 0 && (
          <Fact
            label="Most played lately"
            value={lately.name}
            hint={`${listened(lately.hours * 60)} in the last 4 weeks`}
          />
        )}
        {ofArtist != null && (
          <Fact
            label={`Of your ${page.artist_name} listening`}
            value={pct(Math.min(1, ofArtist))}
          />
        )}
        <Fact
          label="Since you found it"
          value={`${listened(page.minutes / days)} a day`}
          hint="on average"
        />
      </SpotlightCard>
    </Section>
  )
}

/** One of your top albums: its songs in order with your plays, and since when. */
export function Album({ album }: { album: AlbumKey }) {
  const page = useAlbum(album.name, album.artist)
  const notTop = page.error instanceof ApiError && page.error.status === 404
  return (
    <div className="space-y-8">
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
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={fadeTransition}
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
            <div className="space-y-8">
              <History page={page.data} />
              <Highlights page={page.data} />
            </div>
          </div>
        </motion.div>
      )}
    </div>
  )
}
