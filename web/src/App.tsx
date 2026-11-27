import { AnimatePresence, MotionConfig, motion } from 'framer-motion'
import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react'

import { ErrorBoundary } from './components/ErrorBoundary'
import { Nav, type Tab } from './components/Nav'
import { Skeleton } from './components/States'
import { finishLogin, getToken } from './lib/api'
import { type AlbumKey, OpenAlbum, albumInPath, albumPath } from './lib/album'
import { OpenArtist, artistInPath, artistPath } from './lib/artist'
import { OpenFriend, forgetInvite, friendInPath, friendPath, startInvite } from './lib/friends'
import { fadeTransition } from './lib/motion'
import { useSettings } from './lib/settings'
import { cn } from './lib/utils'

// Each screen is its own download, so the first visit only loads what it shows: the login
// screen's WebGL aurora and the Stats charts aren't fetched until they're needed.
const Home = lazy(() => import('./screens/Home').then((m) => ({ default: m.Home })))
const Login = lazy(() => import('./screens/Login').then((m) => ({ default: m.Login })))
const Privacy = lazy(() => import('./screens/Privacy').then((m) => ({ default: m.Privacy })))
const Terms = lazy(() => import('./screens/Terms').then((m) => ({ default: m.Terms })))
const Stats = lazy(() => import('./screens/Stats').then((m) => ({ default: m.Stats })))
const Settings = lazy(() =>
  import('./screens/Settings').then((m) => ({ default: m.Settings })),
)
const Top = lazy(() => import('./screens/Top').then((m) => ({ default: m.Top })))
const Gigs = lazy(() => import('./screens/Gigs').then((m) => ({ default: m.Gigs })))
const Artist = lazy(() => import('./screens/Artist').then((m) => ({ default: m.Artist })))
const Album = lazy(() => import('./screens/Album').then((m) => ({ default: m.Album })))
const Friends = lazy(() => import('./screens/Friends').then((m) => ({ default: m.Friends })))
const Friend = lazy(() => import('./screens/Friend').then((m) => ({ default: m.Friend })))
const AddFriend = lazy(() =>
  import('./screens/AddFriend').then((m) => ({ default: m.AddFriend })),
)

const TAB_KEY = 'spotify-stats.tab'
// Runs once, before the first render: picks up ?token= after "Log in with Spotify".
const loginError = finishLogin()
// Then an invite from /add/<invite>, or one saved before going to log in.
const pendingInvite = startInvite()

// The app puts the scroll back itself: the browser would do it the moment Back is pressed,
// while the old page is still fading out, so the page jumped about before the new one showed.
if ('scrollRestoration' in window.history) window.history.scrollRestoration = 'manual'

/** Opens a page in the history, remembering how far down the one you're leaving was. */
function push(state: object | null, url: string) {
  window.history.replaceState({ ...window.history.state, scroll: window.scrollY }, '')
  window.history.pushState(state, '', url)
}

function savedTab(): Tab {
  try {
    const tab = localStorage.getItem(TAB_KEY)
    return ['top', 'stats', 'gigs', 'friends', 'settings'].includes(tab ?? '') ? (tab as Tab) : 'home'
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
  // An artist's page sits over the tabs at /artist/<name>, so the browser's back button works.
  const [artist, setArtist] = useState<string | null>(() => artistInPath())
  // An album's page the same way, at /album/<artist>/<album>.
  const [album, setAlbum] = useState<AlbumKey | null>(() => albumInPath())
  // A friend's page works the same way at /friend/<id>; an artist page can open over it.
  const [friend, setFriend] = useState<string | null>(() => friendInPath())
  const [invite, setInvite] = useState<string | null>(pendingInvite)
  // Where to scroll once the next page shows: the top for a new page, back where you were
  // when going back.
  const scrollTo = useRef(0)

  useEffect(() => {
    const onPop = (e: PopStateEvent) => {
      scrollTo.current = e.state?.scroll ?? 0
      setArtist(artistInPath())
      setAlbum(albumInPath())
      setFriend(friendInPath())
    }
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  const openArtist = useCallback((name: string) => {
    push({ artist: name }, artistPath(name))
    setArtist(name)
    // From an album page: the artist's page replaces it; Back brings the album back.
    setAlbum(null)
    scrollTo.current = 0
  }, [])

  const openAlbum = useCallback((key: AlbumKey) => {
    push({ album: key }, albumPath(key))
    setAlbum(key)
    setArtist(null)
    scrollTo.current = 0
  }, [])

  const openFriend = useCallback((userId: string) => {
    push({ friend: userId }, friendPath(userId))
    setFriend(userId)
    scrollTo.current = 0
  }, [])

  // Readable whether or not you're logged in, so it can be linked from anywhere.
  const page = window.location.pathname
  if (page === '/privacy' || page === '/terms') {
    return <Suspense fallback={null}>{page === '/privacy' ? <Privacy /> : <Terms />}</Suspense>
  }

  if (!getToken()) {
    return (
      <Suspense fallback={null}>
        <Login error={loginError} invited={invite !== null} />
      </Suspense>
    )
  }

  const closeArtist = () => {
    // Opened from inside the app: go back. Opened from a link: there's nothing to go back to.
    if (window.history.state?.artist) window.history.back()
    else {
      window.history.replaceState(null, '', '/')
      setArtist(null)
    }
  }

  const closeAlbum = () => {
    if (window.history.state?.album) window.history.back()
    else {
      window.history.replaceState(null, '', '/')
      setAlbum(null)
    }
  }

  const closeFriend = () => {
    if (window.history.state?.friend) window.history.back()
    else {
      window.history.replaceState(null, '', '/')
      setFriend(null)
    }
  }

  const go = (next: Tab) => {
    if (artist || album || friend) {
      push(null, '/')
      setArtist(null)
      setAlbum(null)
      setFriend(null)
    }
    setTab(next)
    scrollTo.current = 0
    if (next === tab) window.scrollTo({ top: 0 })
    try {
      localStorage.setItem(TAB_KEY, next)
    } catch {
      // Remembering the tab is only a convenience.
    }
  }

  // Done with an invite, added or not: forget it so it doesn't come back on the next load.
  const finishInvite = () => {
    forgetInvite()
    setInvite(null)
    go('friends')
  }

  const view = invite
    ? 'invite'
    : album
      ? `album:${album.artist}/${album.name}`
      : artist
        ? `artist:${artist}`
        : friend
          ? `friend:${friend}`
          : tab
  const screen = invite ? (
    <AddFriend invite={invite} onDone={finishInvite} />
  ) : album ? (
    <Album album={album} />
  ) : artist ? (
    <Artist name={artist} />
  ) : friend ? (
    <Friend userId={friend} onBack={closeFriend} />
  ) : (
    <>
      {tab === 'home' && <Home onSeeAll={() => go('top')} onGigs={() => go('gigs')} />}
      {tab === 'top' && <Top />}
      {tab === 'stats' && <Stats />}
      {tab === 'gigs' && <Gigs />}
      {tab === 'friends' && <Friends />}
      {tab === 'settings' && <Settings />}
    </>
  )

  return (
    // Animations follow the device's "reduce motion" setting, unless Settings says reduce.
    <MotionConfig reducedMotion={settings.motion === 'reduce' ? 'always' : 'user'}>
      <OpenArtist.Provider value={openArtist}>
        <OpenAlbum.Provider value={openAlbum}>
        <div className={cn('min-h-screen', settings.motion === 'reduce' && 'reduce-motion')}>
          <a
            href="#main"
            className="sr-only z-30 rounded-full bg-accent px-4 py-2 font-semibold text-black focus:not-sr-only focus:fixed focus:top-4 focus:left-4"
          >
            Skip to content
          </a>
          {/* A soft green glow behind the top of every page. */}
          <div className="pointer-events-none fixed inset-x-0 top-0 h-80 bg-[radial-gradient(60%_80%_at_30%_0%,rgba(29,185,84,0.22),transparent_70%)]" />
          <Nav
            tab={tab}
            onChange={go}
            onBack={
              invite ? undefined : album ? closeAlbum : artist ? closeArtist : friend ? closeFriend : undefined
            }
          />
          <main
            id="main"
            className="relative mx-auto max-w-3xl px-4 pt-[max(1.5rem,env(safe-area-inset-top))] pb-32 md:pt-28 md:pb-12 lg:max-w-5xl"
          >
            <AnimatePresence
              mode="wait"
              onExitComplete={() => window.scrollTo({ top: scrollTo.current })}
            >
              <motion.div
                key={view}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1, transition: fadeTransition }}
                // Leaving stays quick, so the next page isn't kept waiting.
                exit={{ opacity: 0, transition: { duration: 0.2 } }}
              >
                <ErrorBoundary key={view}>
                  <Suspense fallback={<Loading />}>
                    <OpenFriend.Provider value={openFriend}>{screen}</OpenFriend.Provider>
                  </Suspense>
                </ErrorBoundary>
              </motion.div>
            </AnimatePresence>
          </main>
        </div>
        </OpenAlbum.Provider>
      </OpenArtist.Provider>
    </MotionConfig>
  )
}
