import { ExternalLink, LegalPage, Part } from '@/components/Legal'

/** Plain-English terms of use at /terms, readable without logging in. */
export function Terms() {
  return (
    <LegalPage
      title="Terms"
      intro="The short version: it's a free personal project, use it for your own listening, and it comes with no promises."
      updated="30 October 2026"
    >
      <Part title="Using Stats">
        <p>
          Stats is free. Log in with your own Spotify account only, and don't try to break,
          overload or get around how the app works, or read other people's data.
        </p>
      </Part>

      <Part title="Your data">
        <p>
          Your listening history stays yours. We use it only to show you your stats, as described
          in the <a href="/privacy" className="text-accent underline underline-offset-2">privacy page</a>,
          and you can delete it from Settings at any time.
        </p>
      </Part>

      <Part title="Spotify and Ticketmaster">
        <p>
          Stats isn't made by, endorsed by or affiliated with Spotify. Music data and artwork come
          from Spotify and link back to it, and{' '}
          <ExternalLink href="https://www.spotify.com/legal/end-user-agreement/">
            Spotify's terms
          </ExternalLink>{' '}
          still apply to your account. Gig dates come from Ticketmaster; tickets are bought on
          Ticketmaster under its terms, not through Stats.
        </p>
      </Part>

      <Part title="No guarantees">
        <p>
          Stats is provided as it is. Numbers can be incomplete (Spotify only shares your most
          recent plays), gig details can change, and the app may be down, change or close. If it
          closes, your data is deleted.
        </p>
      </Part>

      <Part title="Changes">
        <p>
          If these terms change, the date at the top changes too. Questions go on{' '}
          <ExternalLink href="https://github.com/damienta/spotify-stats/issues">GitHub</ExternalLink>.
        </p>
      </Part>
    </LegalPage>
  )
}
