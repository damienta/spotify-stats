import { Clock3, Flame, ShieldCheck, Ticket, Trophy } from 'lucide-react'

import Aurora from '@/components/Aurora'
import BlurText from '@/components/BlurText'
import { AnimatedLink } from '@/components/skiper/animated-link'
import { Button } from '@/components/ui/button'
import { login } from '@/lib/api'

const FEATURES = [
  { icon: Trophy, title: 'Your top 100', text: 'Artists, tracks and albums, ranked by minutes.' },
  { icon: Clock3, title: 'When you listen', text: 'Your busiest hours and days of the week.' },
  { icon: Flame, title: 'Streaks', text: 'How many days in a row you’ve kept listening.' },
  { icon: Ticket, title: 'Gigs', text: 'UK dates for the artists you play most, with tickets.' },
]

/** A small, static taste of what you see after logging in. */
function Preview() {
  const bars = [92, 74, 61, 48, 40]
  return (
    <div
      aria-hidden
      className="glass w-full max-w-sm rotate-1 space-y-4 rounded-3xl p-5 text-left shadow-2xl"
    >
      <div className="flex items-center justify-between">
        <p className="text-sm font-bold">Your top artists</p>
        <span className="rounded-full bg-white/10 px-2 py-0.5 text-[11px] text-muted">4 weeks</span>
      </div>
      <ol className="space-y-2.5">
        {bars.map((width, i) => (
          <li key={width} className="flex items-center gap-3 text-sm">
            <span className="w-3 text-faint tabular">{i + 1}</span>
            <span className="size-8 shrink-0 rounded-full bg-gradient-to-br from-accent/80 to-emerald-950" />
            <span className="flex-1">
              <span
                className="block h-2 rounded-full bg-accent"
                style={{ width: `${width}%`, opacity: 1 - i * 0.15 }}
              />
            </span>
            <span className="w-24 text-right text-xs text-muted tabular">
              {(width * 19).toLocaleString()} minutes
            </span>
          </li>
        ))}
      </ol>
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-2xl bg-white/[0.05] p-3">
          <p className="text-[11px] text-faint uppercase">This week</p>
          <p className="text-lg font-extrabold text-accent">1,766 minutes</p>
        </div>
        <div className="rounded-2xl bg-white/[0.05] p-3">
          <p className="text-[11px] text-faint uppercase">Streak</p>
          <p className="text-lg font-extrabold">23 days</p>
        </div>
      </div>
    </div>
  )
}

export function Login({ error }: { error: string | null }) {
  return (
    <div className="relative min-h-screen overflow-hidden">
      <div className="absolute inset-x-0 top-0 h-[60vh] opacity-80">
        <Aurora colorStops={['#0b3d1f', '#1db954', '#0b3d1f']} amplitude={1.1} blend={0.6} />
      </div>

      <header className="relative mx-auto flex max-w-5xl items-center gap-2.5 px-6 pt-6">
        <img src="/icon.svg" alt="" className="size-8" />
        <span className="text-lg font-extrabold tracking-tight">Stats</span>
      </header>

      <main className="relative mx-auto grid max-w-5xl items-center gap-12 px-6 py-14 md:grid-cols-[1.1fr_1fr] md:py-20">
        <div className="flex flex-col items-center gap-6 text-center md:items-start md:text-left">
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
            <BlurText
              text="Your listening, in numbers."
              delay={120}
              className="justify-center md:justify-start"
            />
          </h1>
          <p className="max-w-md text-lg text-muted">
            Your own Wrapped, all year round: top artists, when you listen, streaks, and gigs by
            the artists you play most.
          </p>
          <div className="flex flex-col items-center gap-3 sm:flex-row">
            <Button size="lg" onClick={login}>
              Log in with Spotify
            </Button>
            <AnimatedLink href="/?demo" className="px-3 text-sm font-semibold text-muted hover:text-white">
              Try the demo first
            </AnimatedLink>
          </div>
          {error && (
            <p role="alert" className="text-sm text-red-400">
              Login didn't finish ({error}). Try again.
            </p>
          )}
          <p className="flex flex-wrap items-center justify-center gap-x-2 gap-y-1 text-xs text-muted">
            <ShieldCheck className="size-4 text-accent" />
            Read-only: it sees what you play, nothing else. Delete your data any time.
            <a href="/privacy" className="underline underline-offset-2 hover:text-white">
              Privacy
            </a>
          </p>
        </div>
        <div className="flex justify-center md:justify-end">
          <Preview />
        </div>
      </main>

      <section className="relative mx-auto grid max-w-5xl gap-3 px-6 pb-14 sm:grid-cols-2 lg:grid-cols-4">
        {FEATURES.map(({ icon: Icon, title, text }) => (
          <div key={title} className="glass rounded-2xl p-4">
            <Icon className="size-5 text-accent" />
            <p className="mt-2 font-bold">{title}</p>
            <p className="text-sm text-muted">{text}</p>
          </div>
        ))}
      </section>

      <footer className="relative mx-auto flex max-w-5xl flex-wrap justify-between gap-2 px-6 pb-8 text-xs text-faint">
        <span>Not made by or affiliated with Spotify. Gig data from Ticketmaster.</span>
        <a href="/privacy" className="hover:text-white">
          Privacy
        </a>
      </footer>
    </div>
  )
}
