import { AnimatePresence, motion } from 'framer-motion'
import { LogOut } from 'lucide-react'
import { useState } from 'react'

import { Nav, type Tab } from './components/Nav'
import { Button } from './components/ui/button'
import { finishLogin, getToken, logout } from './lib/api'
import { Home } from './screens/Home'
import { Login } from './screens/Login'
import { Stats } from './screens/Stats'
import { Top } from './screens/Top'

const TAB_KEY = 'spotify-stats.tab'
// Runs once, before the first render: picks up ?token= after "Log in with Spotify".
const loginError = finishLogin()

function savedTab(): Tab {
  try {
    const tab = localStorage.getItem(TAB_KEY)
    return tab === 'top' || tab === 'stats' ? tab : 'home'
  } catch {
    return 'home'
  }
}

export function App() {
  const [tab, setTab] = useState<Tab>(savedTab)

  if (!getToken()) return <Login error={loginError} />

  const go = (next: Tab) => {
    setTab(next)
    window.scrollTo({ top: 0 })
    try {
      localStorage.setItem(TAB_KEY, next)
    } catch {
      // Remembering the tab is only a convenience.
    }
  }

  return (
    <div className="min-h-screen">
      {/* A soft green glow behind the top of every page. */}
      <div className="pointer-events-none fixed inset-x-0 top-0 h-80 bg-[radial-gradient(60%_80%_at_30%_0%,rgba(29,185,84,0.22),transparent_70%)]" />
      <Nav tab={tab} onChange={go} />
      {/* Logout stays in the top corner on every tab. */}
      <Button
        variant="glass"
        size="icon"
        onClick={logout}
        aria-label="Log out"
        title="Log out"
        className="fixed top-[max(1rem,env(safe-area-inset-top))] right-4 z-20 md:top-6 md:right-6"
      >
        <LogOut className="size-4" />
      </Button>
      <main className="relative mx-auto max-w-3xl px-4 pt-6 pb-32 md:pl-64 md:pb-12 lg:max-w-5xl">
        <AnimatePresence mode="wait">
          <motion.div
            key={tab}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
          >
            {tab === 'home' && <Home onSeeAll={() => go('top')} />}
            {tab === 'top' && <Top />}
            {tab === 'stats' && <Stats />}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  )
}
