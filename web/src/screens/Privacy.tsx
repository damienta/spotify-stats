import { ArrowLeft } from 'lucide-react'
import type { ReactNode } from 'react'

function Part({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="text-lg font-bold">{title}</h2>
      <div className="space-y-2 text-muted">{children}</div>
    </section>
  )
}

/** Plain-English privacy page at /privacy, readable without logging in. */
export function Privacy() {
  return (
    <main className="mx-auto max-w-2xl space-y-8 px-6 py-10">
      <a href="/" className="inline-flex items-center gap-2 text-sm font-semibold text-muted hover:text-white">
        <ArrowLeft className="size-4" />
        Back to Stats
      </a>
      <header className="space-y-2">
        <h1 className="text-3xl font-extrabold tracking-tight">Privacy</h1>
        <p className="text-muted">What Stats keeps about you, why, and how to remove it.</p>
      </header>

      <Part title="What we read from Spotify">
        <p>
          When you log in, Spotify asks you to let Stats see your profile name and what you've
          recently played. That's all it can do: it can't play music, change playlists or see your
          email or payment details.
        </p>
      </Part>

      <Part title="What we store">
        <ul className="list-disc space-y-1 pl-5">
          <li>Your Spotify user ID and display name.</li>
          <li>
            The keys Spotify gives us to fetch your recent plays (about every 20 minutes), so your
            history keeps growing while you're away.
          </li>
          <li>Your plays (track, artist, album, when, for how long) and the stats made from them.</li>
        </ul>
        <p>
          It's kept on Amazon Web Services in Stockholm, Sweden, encrypted at rest. Nobody else can
          see your stats, and we don't sell or share your data, show ads or use tracking cookies.
        </p>
      </Part>

      <Part title="In your browser">
        <p>
          Your login and display settings (text size, animations, home city) are saved in this
          browser only.
        </p>
      </Part>

      <Part title="Gigs">
        <p>
          To find concerts we send Ticketmaster artist names only, never anything about you. Ticket links go to Ticketmaster, whose own privacy policy applies there.
        </p>
      </Part>

      <Part title="Deleting your data">
        <p>
          In Settings, <strong className="text-white">Delete my data</strong> removes your account,
          every play and all your stats straight away. To stop Stats reading your Spotify too,
          remove it at{' '}
          <a
            href="https://www.spotify.com/account/apps/"
            target="_blank"
            rel="noreferrer"
            className="text-accent underline underline-offset-2"
          >
            spotify.com/account/apps
          </a>
          .
        </p>
      </Part>

      <Part title="Questions">
        <p>
          Stats is a personal project, not made by or affiliated with Spotify. Ask anything on{' '}
          <a
            href="https://github.com/damienta/spotify-stats/issues"
            target="_blank"
            rel="noreferrer"
            className="text-accent underline underline-offset-2"
          >
            GitHub
          </a>
          .
        </p>
      </Part>
    </main>
  )
}
