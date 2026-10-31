import { motion } from 'framer-motion'
import { Clock, Ticket } from 'lucide-react'
import { useState } from 'react'

import { Artwork } from '@/components/Artwork'
import BlurText from '@/components/BlurText'
import { Problem, Skeleton } from '@/components/States'
import { useOpenArtist } from '@/lib/artist'
import { type GigRow, gigRows, sameCity, ticketState } from '@/lib/gigs'
import { useStat } from '@/lib/queries'
import { ANYWHERE, useSettings } from '@/lib/settings'
import type { Touring } from '@/lib/types'
import { cn } from '@/lib/utils'

type Where = 'city' | 'all'

function Chip({ on, onClick, children }: { on: boolean; onClick: () => void; children: string }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className={cn(
        'rounded-full px-4 py-1.5 text-sm font-semibold transition-colors',
        on ? 'bg-accent text-black' : 'glass text-muted hover:text-white',
      )}
    >
      {children}
    </button>
  )
}

function Row({ row, now }: { row: GigRow; now: number }) {
  const { gig } = row
  const day = new Date(`${gig.date}T12:00:00`)
  const tickets = ticketState(gig, now)
  const openArtist = useOpenArtist()
  return (
    <motion.li
      initial={{ opacity: 0, y: 8 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="glass flex items-center gap-3 rounded-2xl p-3 sm:gap-4"
    >
      <div className="w-12 shrink-0 text-center leading-tight">
        <p className="text-[11px] font-bold text-accent uppercase">
          {day.toLocaleDateString('en-GB', { weekday: 'short' })}
        </p>
        <p className="text-xl font-extrabold tabular">{day.getDate()}</p>
      </div>
      <button
        type="button"
        onClick={() => openArtist(row.artist)}
        className="flex min-w-0 flex-1 items-center gap-3 text-left"
      >
        <Artwork src={row.image} name={row.artist} round className="size-11 shrink-0" />
        <div className="min-w-0">
          <p className="truncate font-bold">{row.artist}</p>
          <p className="truncate text-sm text-muted">
            {[gig.venue, gig.city].filter(Boolean).join(', ')}
          </p>
          <p className="text-xs text-faint">Your #{row.rank} artist</p>
        </div>
      </button>
      <div className="flex shrink-0 flex-col items-end gap-1">
        <a
          href={gig.url}
          target="_blank"
          rel="noopener noreferrer"
          className={cn(
            'flex h-9 items-center gap-2 rounded-full px-4 text-sm font-bold transition-colors',
            tickets.buyable ? 'bg-accent text-black hover:bg-accent-bright' : 'glass text-white hover:bg-white/10',
          )}
        >
          {tickets.buyable ? <Ticket className="size-4" /> : <Clock className="size-4" />}
          <span className="hidden sm:inline">{tickets.label}</span>
          <span className="sm:hidden">{tickets.buyable ? 'Tickets' : tickets.label.replace(/,.*/, '')}</span>
        </a>
        {tickets.note && <p className="hidden text-xs text-muted sm:block">{tickets.note}</p>}
      </div>
    </motion.li>
  )
}

/** Every UK date for your top artists, soonest first, grouped by month. */
export function Gigs() {
  const touring = useStat<Touring[]>('concerts')
  const { city } = useSettings()
  const hasCity = city !== ANYWHERE
  const [where, setWhere] = useState<Where>(hasCity ? 'city' : 'all')
  const [onSale, setOnSale] = useState(false)
  const now = Date.now()

  const rows = gigRows(touring.data ?? []).filter(
    (r) =>
      (where === 'all' || !hasCity || sameCity(r.gig, city)) &&
      (!onSale || ticketState(r.gig, now).buyable),
  )
  const months = new Map<string, GigRow[]>()
  for (const row of rows) {
    const month = new Date(`${row.gig.date}T12:00:00`).toLocaleDateString('en-GB', {
      month: 'long',
      year: 'numeric',
    })
    months.set(month, [...(months.get(month) ?? []), row])
  }

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
          <BlurText text="Your gigs" delay={80} />
        </h1>
        <p className="text-sm text-muted">
          UK dates for your top artists, from Ticketmaster. Checked every day.
        </p>
      </header>

      <div className="flex flex-wrap gap-2">
        {hasCity && (
          <Chip on={where === 'city'} onClick={() => setWhere('city')}>
            {city}
          </Chip>
        )}
        <Chip on={where === 'all' || !hasCity} onClick={() => setWhere('all')}>
          All UK
        </Chip>
        <Chip on={onSale} onClick={() => setOnSale(!onSale)}>
          On sale now
        </Chip>
      </div>

      {touring.isError ? (
        <Problem error={touring.error} onRetry={() => touring.refetch()} />
      ) : !touring.data ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }, (_, i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <p className="glass rounded-2xl p-5 text-sm text-muted">
          {where === 'city' && hasCity
            ? `None of your top artists have ${city} dates announced. Try All UK, or change your home city in Settings.`
            : 'None of your top artists have UK dates announced right now. We check every day.'}
        </p>
      ) : (
        [...months].map(([month, list]) => (
          <section key={month} className="space-y-2">
            <h2 className="px-1 text-sm font-bold text-faint">{month}</h2>
            <ul className="space-y-2">
              {list.map((row) => (
                <Row key={row.gig.url + row.gig.date + row.artist} row={row} now={now} />
              ))}
            </ul>
          </section>
        ))
      )}
    </div>
  )
}
