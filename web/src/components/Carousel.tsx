import { ChevronLeft, ChevronRight } from 'lucide-react'
import { type ReactNode, useCallback, useEffect, useRef, useState } from 'react'

import { cn } from '@/lib/utils'

const FADE = '3rem'

/**
 * A row of cards that scrolls sideways: swipe on phones, the arrows with a mouse, arrow keys
 * once focused. The edges fade while there's more to see that way.
 */
export function Carousel({ label, children }: { label: string; children: ReactNode }) {
  const row = useRef<HTMLDivElement>(null)
  const [more, setMore] = useState({ before: false, after: false })

  const measure = useCallback(() => {
    const el = row.current
    if (!el) return
    setMore({
      before: el.scrollLeft > 4,
      after: el.scrollLeft + el.clientWidth < el.scrollWidth - 4,
    })
  }, [])

  useEffect(() => {
    const el = row.current
    if (!el) return
    measure()
    const resize = new ResizeObserver(measure)
    resize.observe(el)
    return () => resize.disconnect()
  }, [measure])

  const page = (direction: 1 | -1) => {
    const el = row.current
    if (!el) return
    const smooth = !matchMedia('(prefers-reduced-motion: reduce)').matches
    el.scrollBy({ left: direction * el.clientWidth * 0.8, behavior: smooth ? 'smooth' : 'auto' })
  }

  const mask = `linear-gradient(to right, ${more.before ? 'transparent' : 'black'}, black ${FADE}, black calc(100% - ${FADE}), ${more.after ? 'transparent' : 'black'})`

  return (
    <div className="group/carousel relative">
      <div
        ref={row}
        role="region"
        aria-label={label}
        tabIndex={0}
        onScroll={measure}
        style={{ maskImage: mask, WebkitMaskImage: mask }}
        className="-mx-4 flex snap-x snap-mandatory gap-4 overflow-x-auto scroll-px-4 px-4 pb-2 outline-none [scrollbar-width:none] focus-visible:ring-2 focus-visible:ring-accent/60"
      >
        {children}
      </div>
      {(['before', 'after'] as const).map((side) => (
        <button
          key={side}
          type="button"
          aria-label={side === 'before' ? 'Scroll back' : 'Scroll forward'}
          onClick={() => page(side === 'before' ? -1 : 1)}
          className={cn(
            'glass absolute top-1/2 hidden size-10 -translate-y-1/2 items-center justify-center rounded-full text-white transition-opacity hover:bg-white/15 md:flex',
            side === 'before' ? '-left-3' : '-right-3',
            more[side] ? 'opacity-100' : 'pointer-events-none opacity-0',
          )}
        >
          {side === 'before' ? <ChevronLeft className="size-5" /> : <ChevronRight className="size-5" />}
        </button>
      ))}
    </div>
  )
}
