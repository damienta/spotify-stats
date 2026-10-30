import { ExternalLink, LegalPage, Part } from '@/components/Legal'

/** Plain-English privacy page at /privacy, readable without logging in. */
export function Privacy() {
  return (
    <LegalPage
      title="Privacy"
      intro="What Stats keeps about you, why, and how to remove it."
      updated="30 October 2026"
    >
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
          <ExternalLink href="https://www.spotify.com/account/apps/">spotify.com/account/apps</ExternalLink>
          .
        </p>
      </Part>

      <Part title="Questions">
        <p>
          Stats is a personal project, not made by or affiliated with Spotify. Ask anything on{' '}
          <ExternalLink href="https://github.com/damienta/spotify-stats/issues">GitHub</ExternalLink>
          .
        </p>
      </Part>
    </LegalPage>
  )
}
