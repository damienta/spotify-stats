import { saleTime } from './format'
import type { Gig, Touring } from './types'

/** One gig with the artist it belongs to: what the Gigs tab lists, soonest first. */
export interface GigRow {
  artist: string
  rank: number
  image?: string | null
  artistUrl?: string | null
  gig: Gig
}

export const sameCity = (gig: Gig, city: string) =>
  (gig.city ?? '').localeCompare(city, 'en', { sensitivity: 'base' }) === 0

export function gigRows(touring: Touring[]): GigRow[] {
  return touring
    .flatMap((t) =>
      t.events.map((gig) => ({ artist: t.artist, rank: t.rank, image: t.image, artistUrl: t.url, gig })),
    )
    .sort((a, b) => a.gig.date.localeCompare(b.gig.date) || a.rank - b.rank)
}

/** What the ticket button says, and whether tickets can be bought right now. */
export function ticketState(gig: Gig, now: number): { label: string; buyable: boolean; note?: string } {
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
