import { motion } from 'framer-motion'
import { ArrowLeft, UserMinus } from 'lucide-react'
import { type ReactNode, useState } from 'react'

import { Artwork } from '@/components/Artwork'
import BlurText from '@/components/BlurText'
import { MaybeLink } from '@/components/MaybeLink'
import { Minutes } from '@/components/Minutes'
import { Section } from '@/components/Section'
import SpotlightCard from '@/components/SpotlightCard'
import { Problem, Skeleton } from '@/components/States'
import { Button } from '@/components/ui/button'
import { ApiError } from '@/lib/api'
import { useOpenArtist } from '@/lib/artist'
import { count } from '@/lib/format'
import { useCompare, useFriendSummary, useRemoveFriend } from '@/lib/queries'
import type { Compare, PublicRow } from '@/lib/types'

/** Taste match as a ring that fills to the percentage. */
function TasteRing({ value }: { value: number | null }) {
  const r = 42
  const circumference = 2 * Math.PI * r
  const filled = value === null ? 0 : (value / 100) * circumference
  return (
    <div className="relative size-28 shrink-0">
      <svg viewBox="0 0 100 100" className="size-full -rotate-90" aria-hidden="true">
        <circle cx="50" cy="50" r={r} fill="none" strokeWidth="9" className="stroke-white/10" />
        <motion.circle
          cx="50"
          cy="50"
          r={r}
          fill="none"
          strokeWidth="9"
          strokeLinecap="round"
          className="stroke-accent"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference - filled }}
          transition={{ duration: 0.9, ease: 'easeOut' }}
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-2xl font-extrabold tabular">
        {value === null ? '–' : `${value}%`}
      </span>
    </div>
  )
}

function Tile({ label, children }: { label: string; children: ReactNode }) {
  return (
    <SpotlightCard>
      <p className="text-xs text-muted">{label}</p>
      <p className="text-2xl font-extrabold tabular">{children}</p>
    </SpotlightCard>
  )
}

/** A friend's row: links to Spotify, since you have no stats page for their artists. */
function RowItem({ row, rank }: { row: PublicRow; rank: number }) {
  return (
    <li>
      <MaybeLink
        href={row.url}
        className="group flex items-center gap-3 rounded-xl p-2 transition-colors hover:bg-white/5"
      >
        <span className="w-6 text-right text-sm font-semibold text-faint tabular">{rank}</span>
        <Artwork
          src={row.image}
          name={row.name}
          round={!row.artist_name}
          className="size-11 text-xs"
        />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-semibold underline-offset-4 group-hover:underline">
            {row.name}
          </span>
          {row.artist_name && (
            <span className="block truncate text-xs text-muted">{row.artist_name}</span>
          )}
        </span>
      </MaybeLink>
    </li>
  )
}

function List({ title, rows, empty }: { title: string; rows: PublicRow[]; empty: string }) {
  return (
    <Section title={title}>
      <SpotlightCard className="p-2">
        {rows.length ? (
          <ol>
            {rows.map((row, i) => (
              <RowItem key={`${row.name}-${i}`} row={row} rank={i + 1} />
            ))}
          </ol>
        ) : (
          <p className="p-4 text-sm text-muted">{empty}</p>
        )}
      </SpotlightCard>
    </Section>
  )
}

function BothLove({ compare }: { compare: Compare }) {
  const openArtist = useOpenArtist()
  return (
    <Section title="You both love">
      <SpotlightCard className="p-2">
        {compare.both_love.length ? (
          <ul>
            {compare.both_love.map((a) => (
              <li key={a.name}>
                {/* They're one of your artists too, so your own artist page has more. */}
                <button
                  type="button"
                  onClick={() => openArtist(a.name)}
                  className="group flex w-full items-center gap-3 rounded-xl p-2 text-left transition-colors hover:bg-white/5"
                >
                  <Artwork src={a.image} name={a.name} round className="size-11 text-xs" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-semibold underline-offset-4 group-hover:underline">
                      {a.name}
                    </span>
                    <span className="block text-xs text-muted tabular">
                      #{a.your_rank} for you · #{a.their_rank} for {compare.display_name}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="p-4 text-sm text-muted">No artists in common in the last 12 months yet.</p>
        )}
      </SpotlightCard>
    </Section>
  )
}

function RemoveFriend({
  userId,
  name,
  onRemoved,
}: {
  userId: string
  name: string
  onRemoved: () => void
}) {
  const [confirming, setConfirming] = useState(false)
  const remove = useRemoveFriend()
  if (!confirming) {
    return (
      <Button variant="glass" onClick={() => setConfirming(true)} className="text-red-400">
        <UserMinus className="size-4" />
        Remove friend
      </Button>
    )
  }
  return (
    <div role="alert" className="space-y-3 rounded-2xl border border-red-500/40 bg-red-500/10 p-4">
      <p className="font-semibold">Remove {name}?</p>
      <p className="text-sm text-muted">
        You'll stop seeing each other's stats. They won't be told, and you can add each other again
        with a new link.
      </p>
      {remove.isError && (
        <p className="text-sm text-red-400">That didn't work. Try again in a minute.</p>
      )}
      <div className="flex flex-wrap gap-2">
        <Button
          onClick={() => remove.mutate(userId, { onSuccess: onRemoved })}
          disabled={remove.isPending}
          className="bg-red-500 text-white hover:bg-red-400"
        >
          {remove.isPending ? 'Removing…' : 'Remove'}
        </Button>
        <Button variant="ghost" onClick={() => setConfirming(false)} disabled={remove.isPending}>
          Cancel
        </Button>
      </div>
    </div>
  )
}

/** A friend's page: their summary, and how your tastes compare. */
export function Friend({ userId, onBack }: { userId: string; onBack: () => void }) {
  const summary = useFriendSummary(userId)
  const compare = useCompare(userId)
  const gone = summary.error instanceof ApiError && summary.error.status === 404
  const s = summary.data
  return (
    <div className="space-y-8">
      <Button variant="glass" size="sm" onClick={onBack}>
        <ArrowLeft className="size-4" />
        Back
      </Button>

      {gone ? (
        <p className="glass rounded-2xl p-5 text-sm text-muted">
          You can't see this person's stats. They may have turned sharing off or removed you.
        </p>
      ) : summary.isError ? (
        <Problem error={summary.error} onRetry={() => summary.refetch()} />
      ) : !s ? (
        <div className="space-y-4">
          <Skeleton className="h-32" />
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
          <div className="flex flex-col items-center gap-5 text-center sm:flex-row sm:text-left">
            <Artwork name={s.display_name} round className="size-28 shrink-0 text-3xl shadow-2xl" />
            <div className="min-w-0 flex-1 space-y-1">
              <p className="text-xs font-semibold text-accent uppercase">Friend</p>
              <h1 className="text-4xl font-extrabold tracking-tight break-words sm:text-5xl">
                <BlurText
                  key={s.display_name}
                  text={s.display_name}
                  delay={60}
                  className="justify-center sm:justify-start"
                />
              </h1>
            </div>
            <div className="flex flex-col items-center gap-1">
              {compare.data ? (
                <TasteRing value={compare.data.taste_match} />
              ) : (
                <Skeleton className="size-28 rounded-full" />
              )}
              <p className="text-xs font-semibold text-muted">Taste match</p>
            </div>
          </div>

          {!s.ready && (
            <p className="glass rounded-2xl p-4 text-sm text-muted">
              {s.display_name}'s stats are still being built. New accounts start with only their
              last few plays, so check back in a day or two.
            </p>
          )}
          {compare.data && compare.data.taste_match === null && s.ready && (
            <p className="text-sm text-muted">
              Not enough listening on one side yet to compare tastes.
            </p>
          )}

          <div className="grid grid-cols-2 gap-3">
            <Tile label="This week">
              <Minutes value={s.minutes_this_week} hours={false} />
            </Tile>
            <Tile label="Current streak">
              {count(s.streak_days)} {s.streak_days === 1 ? 'day' : 'days'}
            </Tile>
          </div>

          {compare.isError ? (
            <Problem error={compare.error} onRetry={() => compare.refetch()} />
          ) : !compare.data ? (
            <Skeleton className="h-48" />
          ) : (
            <div className="grid gap-8 lg:grid-cols-2">
              <BothLove compare={compare.data} />
              <List
                title="Theirs, new to you"
                rows={compare.data.new_to_you}
                empty="Nothing new: you've played all their top artists."
              />
            </div>
          )}

          <div className="grid gap-8 lg:grid-cols-2">
            <List title="Their top artists, 4 weeks" rows={s.top_artists} empty="Nothing yet." />
            <List title="Their top tracks, 4 weeks" rows={s.top_tracks} empty="Nothing yet." />
          </div>

          <RemoveFriend userId={userId} name={s.display_name} onRemoved={onBack} />
        </motion.div>
      )}
    </div>
  )
}
