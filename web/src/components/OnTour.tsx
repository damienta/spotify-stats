import { CalendarDays, MapPin, Ticket } from 'lucide-react'

import { gigDate } from '@/lib/format'
import { useStat } from '@/lib/queries'
import type { Touring } from '@/lib/types'

import { Artwork } from './Artwork'
import { Section } from './Section'
import SpotlightCard from './SpotlightCard'
import { Skeleton } from './States'

function TourCard({ touring }: { touring: Touring }) {
  const [next, ...later] = touring.events
  return (
    <SpotlightCard className="flex w-72 shrink-0 flex-col gap-3 p-4">
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
        </p>
        <p className="flex items-center gap-2 text-muted">
          <MapPin className="size-4 shrink-0" />
          <span className="truncate">{[next.venue, next.city].filter(Boolean).join(', ')}</span>
        </p>
      </div>
      <a
        href={next.url}
        target="_blank"
        rel="noopener noreferrer"
        className="flex h-9 items-center justify-center gap-2 rounded-full bg-accent text-sm font-bold text-black transition-colors hover:bg-accent-bright"
      >
        <Ticket className="size-4" />
        Tickets
      </a>
      {later.length > 0 && (
        <ul className="space-y-1 border-t border-white/10 pt-2 text-xs">
          {later.map((gig) => (
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
        </ul>
      )}
    </SpotlightCard>
  )
}

/** Your top artists with UK dates announced, favourites first. */
export function OnTour() {
  const touring = useStat<Touring[]>('concerts')
  // Not built yet (needs the latest backend) or failed: nothing to show, so no section.
  if (touring.isError) return null
  return (
    <Section
      title="Your artists on tour"
      action={<span className="text-xs text-faint">UK dates from Ticketmaster</span>}
    >
      {!touring.data ? (
        <div className="flex gap-4">
          {Array.from({ length: 3 }, (_, i) => (
            <Skeleton key={i} className="h-56 w-72 shrink-0" />
          ))}
        </div>
      ) : touring.data.length === 0 ? (
        <p className="px-1 text-sm text-muted">
          None of your top artists have UK dates announced right now. We check every day.
        </p>
      ) : (
        <div className="-mx-4 flex gap-4 overflow-x-auto px-4 pb-2 [scrollbar-width:none]">
          {touring.data.map((t) => (
            <TourCard key={t.artist} touring={t} />
          ))}
        </div>
      )}
    </Section>
  )
}
