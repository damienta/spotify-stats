import { motion } from 'framer-motion'
import { ChartLine, House, Trophy } from 'lucide-react'

import { cn } from '@/lib/utils'

import { ProgressiveBlur } from './skiper/progressive-blur'

export type Tab = 'home' | 'top' | 'stats'

const TABS: { id: Tab; label: string; icon: typeof House }[] = [
  { id: 'home', label: 'Home', icon: House },
  { id: 'top', label: 'Top', icon: Trophy },
  { id: 'stats', label: 'Stats', icon: ChartLine },
]

/** A glass tab bar: along the bottom on phones, down the side on wider screens. */
export function Nav({ tab, onChange }: { tab: Tab; onChange: (tab: Tab) => void }) {
  return (
    <>
      <div className="pointer-events-none fixed inset-x-0 bottom-0 z-10 h-28 md:hidden">
        <ProgressiveBlur position="bottom" height="100%" backgroundColor="#121212" />
      </div>
      <nav
        className={cn(
          'glass fixed z-20 flex',
          'inset-x-4 bottom-[max(1rem,env(safe-area-inset-bottom))] justify-around rounded-full p-1.5',
          'md:inset-x-auto md:top-6 md:bottom-6 md:left-6 md:w-52 md:flex-col md:justify-start md:gap-1 md:rounded-3xl md:p-3',
        )}
      >
        <div className="mb-4 hidden items-center gap-2 px-3 pt-2 md:flex">
          <img src="/icon.svg" alt="" className="size-7" />
          <span className="font-bold">Spotify stats</span>
        </div>
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => onChange(id)}
            aria-current={tab === id ? 'page' : undefined}
            className={cn(
              'relative flex flex-1 flex-col items-center gap-0.5 rounded-full px-4 py-2 text-[11px] font-semibold transition-colors md:flex-none md:flex-row md:gap-3 md:rounded-xl md:px-3 md:py-2.5 md:text-sm',
              tab === id ? 'text-white' : 'text-muted hover:text-white',
            )}
          >
            {tab === id && (
              <motion.span
                layoutId="nav-pill"
                className="absolute inset-0 rounded-full bg-white/10 md:rounded-xl"
                transition={{ type: 'spring', stiffness: 500, damping: 40 }}
              />
            )}
            <Icon className={cn('relative size-5', tab === id && 'text-accent')} />
            <span className="relative">{label}</span>
          </button>
        ))}
      </nav>
    </>
  )
}
