import Aurora from '@/components/Aurora'
import BlurText from '@/components/BlurText'
import { AnimatedLink } from '@/components/skiper/animated-link'
import { Button } from '@/components/ui/button'
import { login } from '@/lib/api'

export function Login({ error }: { error: string | null }) {
  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-6 text-center">
      <div className="absolute inset-x-0 top-0 h-[60vh] opacity-80">
        <Aurora colorStops={['#0b3d1f', '#1db954', '#0b3d1f']} amplitude={1.1} blend={0.6} />
      </div>
      <div className="relative flex max-w-md flex-col items-center gap-6">
        <div className="flex items-center gap-3">
          <img src="/icon.svg" alt="" className="size-12" />
          <span className="text-2xl font-extrabold tracking-tight">SpotifyStats</span>
        </div>
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
          <BlurText text="Your listening, in numbers." delay={120} className="justify-center" />
        </h1>
        <p className="text-muted">
          Top artists, tracks and albums, when you listen, your streaks and your own Wrapped, all
          year round.
        </p>
        <div className="flex flex-col items-center gap-3">
          <Button size="lg" onClick={login}>
            Log in with Spotify
          </Button>
          <AnimatedLink href="/?demo" className="text-sm font-semibold text-muted hover:text-white">
            Try the demo
          </AnimatedLink>
        </div>
        {error && <p className="text-sm text-red-400">Login didn't finish: {error}</p>}
        <p className="text-xs text-faint">Read-only: it can see what you play, nothing else.</p>
      </div>
    </div>
  )
}
