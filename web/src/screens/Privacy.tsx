import { ExternalLink, LegalPage, Part } from '@/components/Legal'

/** Plain-English privacy page at /privacy, readable without logging in. */
export function Privacy() {
  return (
    <LegalPage
      title="Privacy"
      intro="What Stats keeps about you, why, and how to remove it."
      updated="2 November 2026"
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
          It's kept on Amazon Web Services in Stockholm, Sweden, encrypted at rest. Only you, and
          friends you add (below), can see your stats. We don't sell or share your data, show ads or
          use tracking cookies.
        </p>
      </Part>

      <Part title="Friends">
        <p>
          You only have friends if you add them: by opening someone's invite link and tapping Add,
          or by someone opening yours. Once you're friends, each of you can see the other's:
        </p>
        <ul className="list-disc space-y-1 pl-5">
          <li>display name;</li>
          <li>top 10 artists and tracks of the last 4 weeks (names and pictures, not play counts);</li>
          <li>minutes listened this week, and current streak;</li>
          <li>
            a taste match worked out from both of your top artists of the last 12 months, with the
            artists you share and their top artists you haven't played.
          </li>
        </ul>
        <p>
          Friends never see your full history, recent plays, listening times or anything else.
          Turn off <strong className="text-white">Share my summary with friends</strong> in Settings
          to hide all of it, remove a friend at any time, and reset your invite link to stop old
          links working. Nobody else can find you or tell whether you use Stats.
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
          every play, all your stats and your friendships straight away. To stop Stats reading your Spotify too,
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
