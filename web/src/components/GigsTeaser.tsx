import { ArrowRight, Ticket } from 'lucide-react'

import { gigDate } from '@/lib/format'
import { gigRows } from '@/lib/gigs'
import { useStat } from '@/lib/queries'
import type { Touring } from '@/lib/types'

import SpotlightCard from './SpotlightCard'

/** One line on Home pointing at the Gigs tab; hidden when nobody's touring. */
export function GigsTeaser({ onOpen }: { onOpen: () => void }) {
  const touring = useStat<Touring[]>('concerts')
  const rows = gigRows(touring.data ?? [])
  if (!rows.length) return null

  const artists = new Set(rows.map((r) => r.artist)).size
  const next = rows[0]
  return (
    <SpotlightCard className="p-0">
      <button
        type="button"
        onClick={onOpen}
        className="flex w-full items-center gap-3 p-4 text-left"
      >
        <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-accent/15">
          <Ticket className="size-5 text-accent" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block font-bold">
            {artists} of your artists {artists === 1 ? 'plays' : 'play'} the UK soon
          </span>
          <span className="block truncate text-sm text-muted">
            Next: {next.artist}, {gigDate(next.gig.date)}
          </span>
        </span>
        <span className="flex shrink-0 items-center gap-1 text-sm font-semibold text-accent">
          <span className="hidden sm:inline">See gigs</span>
          <ArrowRight className="size-4" />
        </span>
      </button>
    </SpotlightCard>
  )
}
