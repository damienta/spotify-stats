import { motion } from 'framer-motion'
import { ChartLine, House, LogOut, Settings, Trophy } from 'lucide-react'

import { logout } from '@/lib/api'
import { cn } from '@/lib/utils'

import { ProgressiveBlur } from './skiper/progressive-blur'
import { Button } from './ui/button'

export type Tab = 'home' | 'top' | 'stats' | 'settings'

const TABS: { id: Tab; label: string; icon: typeof House }[] = [
  { id: 'home', label: 'Home', icon: House },
  { id: 'top', label: 'Top', icon: Trophy },
  { id: 'stats', label: 'Stats', icon: ChartLine },
]

/** Settings and logout: on every tab, in the corner on phones and in the bar on wider screens. */
function Corner({
  tab,
  onChange,
  className,
}: {
  tab: Tab
  onChange: (tab: Tab) => void
  className?: string
}) {
  return (
    <div className={cn('flex gap-2', className)}>
      <Button
        variant="glass"
        size="icon"
        onClick={() => onChange('settings')}
        aria-label="Settings"
        aria-current={tab === 'settings' ? 'page' : undefined}
        title="Settings"
        className={cn(tab === 'settings' && 'text-accent')}
      >
        <Settings className="size-4" />
      </Button>
      <Button variant="glass" size="icon" onClick={logout} aria-label="Log out" title="Log out">
        <LogOut className="size-4" />
      </Button>
    </div>
  )
}

/** A glass tab bar: along the bottom on phones (in thumb reach), across the top on wider screens. */
export function Nav({ tab, onChange }: { tab: Tab; onChange: (tab: Tab) => void }) {
  return (
    <>
      <div className="pointer-events-none fixed inset-x-0 bottom-0 z-10 h-28 md:hidden">
        <ProgressiveBlur position="bottom" height="100%" backgroundColor="#121212" />
      </div>
      <div className="pointer-events-none fixed inset-x-0 top-0 z-10 hidden h-24 md:block">
        <ProgressiveBlur position="top" height="100%" backgroundColor="#121212" />
      </div>
      <Corner
        tab={tab}
        onChange={onChange}
        className="fixed top-[max(1rem,env(safe-area-inset-top))] right-4 z-20 md:hidden"
      />
      <nav
        className={cn(
          'glass fixed z-20 flex items-center rounded-full p-1.5',
          'inset-x-4 bottom-[max(1rem,env(safe-area-inset-bottom))]',
          'md:inset-x-6 md:top-4 md:bottom-auto md:mx-auto md:max-w-5xl md:justify-between md:pl-4',
        )}
      >
        <div className="hidden items-center gap-2 md:flex">
          <img src="/icon.svg" alt="" className="size-7" />
          <span className="font-bold">SpotifyStats</span>
        </div>
        <div className="flex flex-1 justify-around md:flex-none md:gap-1">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => onChange(id)}
              aria-current={tab === id ? 'page' : undefined}
              className={cn(
                'relative flex flex-1 flex-col items-center gap-0.5 rounded-full px-4 py-2 text-[11px] font-semibold transition-colors md:flex-none md:flex-row md:gap-2 md:text-sm',
                tab === id ? 'text-white' : 'text-muted hover:text-white',
              )}
            >
              {tab === id && (
                <motion.span
                  layoutId="nav-pill"
                  className="absolute inset-0 rounded-full bg-white/10"
                  transition={{ type: 'spring', stiffness: 500, damping: 40 }}
                />
              )}
              <Icon className={cn('relative size-5 md:size-4', tab === id && 'text-accent')} />
              <span className="relative">{label}</span>
            </button>
          ))}
        </div>
        <Corner tab={tab} onChange={onChange} className="hidden md:flex" />
      </nav>
    </>
  )
}
