import { AnimatePresence, MotionConfig, motion } from 'framer-motion'
import { lazy, Suspense, useState } from 'react'

import { ErrorBoundary } from './components/ErrorBoundary'
import { Nav, type Tab } from './components/Nav'
import { Skeleton } from './components/States'
import { finishLogin, getToken } from './lib/api'
import { useSettings } from './lib/settings'

// Each screen is its own download, so the first visit only loads what it shows: the login
// screen's WebGL aurora and the Stats charts aren't fetched until they're needed.
const Home = lazy(() => import('./screens/Home').then((m) => ({ default: m.Home })))
const Login = lazy(() => import('./screens/Login').then((m) => ({ default: m.Login })))
const Privacy = lazy(() => import('./screens/Privacy').then((m) => ({ default: m.Privacy })))
const Stats = lazy(() => import('./screens/Stats').then((m) => ({ default: m.Stats })))
const Settings = lazy(() =>
  import('./screens/Settings').then((m) => ({ default: m.Settings })),
)
const Top = lazy(() => import('./screens/Top').then((m) => ({ default: m.Top })))

const TAB_KEY = 'spotify-stats.tab'
// Runs once, before the first render: picks up ?token= after "Log in with Spotify".
const loginError = finishLogin()

function savedTab(): Tab {
  try {
    const tab = localStorage.getItem(TAB_KEY)
    return tab === 'top' || tab === 'stats' || tab === 'settings' ? tab : 'home'
  } catch {
    return 'home'
  }
}

function Loading() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Loading">
      <Skeleton className="h-12 w-64" />
      <Skeleton className="h-28" />
      <Skeleton className="h-64" />
    </div>
  )
}

export function App() {
  const [tab, setTab] = useState<Tab>(savedTab)
  const settings = useSettings()

  // Readable whether or not you're logged in, so it can be linked from anywhere.
  if (window.location.pathname === '/privacy') {
    return (
      <Suspense fallback={null}>
        <Privacy />
      </Suspense>
    )
  }

  if (!getToken()) {
    return (
      <Suspense fallback={null}>
        <Login error={loginError} />
      </Suspense>
    )
  }

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
    // Animations follow the device's "reduce motion" setting, unless Settings says reduce.
    <MotionConfig reducedMotion={settings.motion === 'reduce' ? 'always' : 'user'}>
      <div className="min-h-screen">
        <a
          href="#main"
          className="sr-only z-30 rounded-full bg-accent px-4 py-2 font-semibold text-black focus:not-sr-only focus:fixed focus:top-4 focus:left-4"
        >
          Skip to content
        </a>
        {/* A soft green glow behind the top of every page. */}
        <div className="pointer-events-none fixed inset-x-0 top-0 h-80 bg-[radial-gradient(60%_80%_at_30%_0%,rgba(29,185,84,0.22),transparent_70%)]" />
        <Nav tab={tab} onChange={go} />
        <main
          id="main"
          className="relative mx-auto max-w-3xl px-4 pt-[max(1.5rem,env(safe-area-inset-top))] pb-32 md:pt-28 md:pb-12 lg:max-w-5xl"
        >
          <AnimatePresence mode="wait">
            <motion.div
              key={tab}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2 }}
            >
              <ErrorBoundary key={tab}>
                <Suspense fallback={<Loading />}>
                  {tab === 'home' && <Home onSeeAll={() => go('top')} />}
                  {tab === 'top' && <Top />}
                  {tab === 'stats' && <Stats />}
                  {tab === 'settings' && <Settings />}
                </Suspense>
              </ErrorBoundary>
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </MotionConfig>
  )
}
