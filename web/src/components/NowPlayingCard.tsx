import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'

import { clock } from '@/lib/format'
import { useNowPlaying, useRecent } from '@/lib/queries'

import { Artwork } from './Artwork'
import SpotlightCard from './SpotlightCard'
import { Problem, Skeleton } from './States'

function Equalizer() {
  return (
    <span className="flex h-3 items-end gap-[2px]" aria-hidden="true">
      {[0, 0.2, 0.4].map((delay) => (
        <motion.span
          key={delay}
          className="w-[3px] rounded-full bg-accent"
          animate={{ height: ['30%', '100%', '45%', '80%', '30%'] }}
          transition={{ duration: 1.1, repeat: Infinity, delay }}
        />
      ))}
    </span>
  )
}

/**
 * What's playing, polled every 10 seconds. Between polls the progress bar moves on by itself,
 * so it ticks every second like Spotify's own player.
 */
export function NowPlayingCard() {
  const playing = useNowPlaying()
  const recent = useRecent()
  const [now, setNow] = useState(Date.now())

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])

  if (playing.isPending) return <Skeleton className="h-28" />
  if (playing.isError) {
    return (
      <SpotlightCard>
        <Problem error={playing.error} onRetry={() => playing.refetch()} />
      </SpotlightCard>
    )
  }

  const { track, is_playing, progress_ms } = playing.data
  const last = recent.data?.items[0]?.track
  const shown = track ?? last
  if (!shown) {
    return (
      <SpotlightCard>
        <p className="py-4 text-center text-sm text-muted">Nothing playing right now.</p>
      </SpotlightCard>
    )
  }

  const length = shown.duration_ms ?? 0
  const elapsed = track
    ? Math.min(length, (progress_ms ?? 0) + (is_playing ? now - playing.dataUpdatedAt : 0))
    : 0
  const label = !track ? 'Last played' : is_playing ? 'Now playing' : 'Paused'

  return (
    <SpotlightCard className="p-0">
      {shown.image && (
        <img
          src={shown.image}
          alt=""
          className="pointer-events-none absolute inset-0 size-full scale-125 object-cover opacity-25 blur-3xl"
        />
      )}
      <div className="relative flex items-center gap-4 p-4">
        <Artwork src={shown.image} name={shown.name ?? '?'} className="size-20 shrink-0 shadow-lg" />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 text-xs font-semibold text-accent">
            {track && is_playing && <Equalizer />}
            {label}
          </div>
          <a
            href={shown.url ?? undefined}
            target="_blank"
            rel="noopener noreferrer"
            className="block truncate text-lg font-bold hover:underline"
          >
            {shown.name}
          </a>
          <p className="truncate text-sm text-muted">{shown.artists.join(', ')}</p>
          {track && length > 0 && (
            <div className="mt-2 flex items-center gap-2 text-[11px] text-muted tabular">
              <span>{clock(elapsed)}</span>
              <div className="h-1 flex-1 overflow-hidden rounded-full bg-white/15">
                <div
                  className="h-full rounded-full bg-white transition-[width] duration-1000 ease-linear"
                  style={{ width: `${(elapsed / length) * 100}%` }}
                />
              </div>
              <span>{clock(length)}</span>
            </div>
          )}
        </div>
      </div>
    </SpotlightCard>
  )
}
