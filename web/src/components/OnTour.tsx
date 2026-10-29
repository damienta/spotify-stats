import { CalendarDays, Clock, MapPin, Ticket } from 'lucide-react'

import { gigDate, saleTime } from '@/lib/format'
import { useStat } from '@/lib/queries'
import { ANYWHERE, useSettings } from '@/lib/settings'
import type { Gig, Touring } from '@/lib/types'
import { cn } from '@/lib/utils'

import { Artwork } from './Artwork'
import { Carousel } from './Carousel'
import { Section } from './Section'
import SpotlightCard from './SpotlightCard'
import { Skeleton } from './States'

const OTHER_DATES = 3

const sameCity = (gig: Gig, city: string) =>
  (gig.city ?? '').localeCompare(city, 'en', { sensitivity: 'base' }) === 0

/** What the ticket button says, and whether tickets can be bought right now. */
function ticketState(gig: Gig, now: number): { label: string; buyable: boolean; note?: string } {
  const opens = gig.sale_start ? Date.parse(gig.sale_start) : NaN
  if (gig.status === 'onsale') return { label: 'Tickets', buyable: true }
  if (gig.status === 'rescheduled') return { label: 'Rescheduled', buyable: true }
  if (gig.status === 'postponed') return { label: 'Postponed', buyable: false }
  if (opens > now) {
    const presale = gig.presales?.find(
      (p) => p.start && p.end && Date.parse(p.start) <= now && now < Date.parse(p.end),
    )
    return presale
      ? { label: 'Presale on now', buyable: true, note: `General sale ${saleTime(gig.sale_start!)}` }
      : { label: `On sale ${saleTime(gig.sale_start!)}`, buyable: false }
  }
  // Off sale after the sale opened: sold out (resale may still be on Ticketmaster).
  if (gig.status === 'offsale') return { label: 'Sold out', buyable: false }
  return { label: 'Tickets', buyable: true }
}

function TourCard({ touring, city }: { touring: Touring; city: string }) {
  const home = city === ANYWHERE ? undefined : touring.events.find((g) => sameCity(g, city))
  const next = home ?? touring.events[0]
  const others = touring.events.filter((g) => g !== next)
  const tickets = ticketState(next, Date.now())
  return (
    <SpotlightCard className="flex w-72 shrink-0 snap-start flex-col gap-3 p-4">
      <a
        href={touring.url ?? undefined}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-3"
      >
        <Artwork src={touring.image} name={touring.artist} round className="size-12 shrink-0" />
        <div className="min-w-0">
          <p className="truncate font-bold">{touring.artist}</p>
          <p className="text-xs text-muted">Your #{touring.rank} artist</p>
        </div>
      </a>
      <div className="space-y-1 text-sm">
        <p className="flex items-center gap-2 font-semibold">
          <CalendarDays className="size-4 text-accent" />
          {gigDate(next.date)}
          {home && (
            <span className="rounded-full bg-accent/15 px-2 py-0.5 text-[0.7rem] font-bold text-accent">
              {city}
            </span>
          )}
        </p>
        <p className="flex items-center gap-2 text-muted">
          <MapPin className="size-4 shrink-0" />
          <span className="truncate">{[next.venue, next.city].filter(Boolean).join(', ')}</span>
        </p>
        {city !== ANYWHERE && !home && (
          <p className="text-xs text-faint">No {city} date yet</p>
        )}
      </div>
      <div className="space-y-1">
        <a
          href={next.url}
          target="_blank"
          rel="noopener noreferrer"
          className={cn(
            'flex h-9 items-center justify-center gap-2 rounded-full text-sm font-bold transition-colors',
            tickets.buyable
              ? 'bg-accent text-black hover:bg-accent-bright'
              : 'glass text-white hover:bg-white/10',
          )}
        >
          {tickets.buyable ? <Ticket className="size-4" /> : <Clock className="size-4" />}
          {tickets.label}
        </a>
        {tickets.note && <p className="text-center text-xs text-muted">{tickets.note}</p>}
      </div>
      {others.length > 0 && (
        <ul className="space-y-1 border-t border-white/10 pt-2 text-xs">
          {others.slice(0, OTHER_DATES).map((gig) => (
            <li key={gig.url + gig.date}>
              <a
                href={gig.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex justify-between gap-2 text-muted hover:text-white"
              >
                <span className="truncate">{gig.city ?? gig.venue}</span>
                <span className="shrink-0 tabular">{gigDate(gig.date)}</span>
              </a>
            </li>
          ))}
          {others.length > OTHER_DATES && (
            <li className="text-faint">
              +{others.length - OTHER_DATES} more UK{' '}
              {others.length - OTHER_DATES === 1 ? 'date' : 'dates'}
            </li>
          )}
        </ul>
      )}
    </SpotlightCard>
  )
}

/** Your top artists with UK dates announced: ones playing your city first, then favourites. */
export function OnTour() {
  const touring = useStat<Touring[]>('concerts')
  const { city } = useSettings()
  // Not built yet (needs the latest backend) or failed: nothing to show, so no section.
  if (touring.isError) return null
  const playsHere = (t: Touring) => city !== ANYWHERE && t.events.some((g) => sameCity(g, city))
  // Stable sort: within each group, the document's favourite-first order stays.
  const ordered = [...(touring.data ?? [])].sort((a, b) => Number(playsHere(b)) - Number(playsHere(a)))
  return (
    <Section
      title="Your artists on tour"
      action={
        <span className="text-xs text-faint">
          {city === ANYWHERE ? 'UK dates' : `${city} first`} · Ticketmaster
        </span>
      }
    >
      {!touring.data ? (
        <div className="flex gap-4">
          {Array.from({ length: 3 }, (_, i) => (
            <Skeleton key={i} className="h-56 w-72 shrink-0" />
          ))}
        </div>
      ) : ordered.length === 0 ? (
        <p className="px-1 text-sm text-muted">
          None of your top artists have UK dates announced right now. We check every day.
        </p>
      ) : (
        <Carousel label="Your artists on tour">
          {ordered.map((t) => (
            <TourCard key={t.artist} touring={t} city={city} />
          ))}
        </Carousel>
      )}
    </Section>
  )
}
