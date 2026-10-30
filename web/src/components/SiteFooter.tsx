const REPO = 'https://github.com/damienta/spotify-stats'

const COLUMNS: { title: string; links: { label: string; href: string; external?: boolean }[] }[] = [
  {
    title: 'Stats',
    links: [
      { label: 'Log in', href: '/' },
      { label: 'Try the demo', href: '/?demo' },
    ],
  },
  {
    title: 'Legal',
    links: [
      { label: 'Privacy', href: '/privacy' },
      { label: 'Terms', href: '/terms' },
    ],
  },
  {
    title: 'Project',
    links: [
      { label: 'Source code', href: REPO, external: true },
      { label: 'Report a problem', href: `${REPO}/issues`, external: true },
    ],
  },
]

/** The footer on pages you can see without logging in: login, Privacy and Terms. */
export function SiteFooter() {
  return (
    <footer className="relative border-t border-white/10">
      <div className="mx-auto grid max-w-5xl gap-8 px-6 py-10 sm:grid-cols-[1.4fr_1fr_1fr_1fr]">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <img src="/icon.svg" alt="" className="size-6" />
            <span className="font-extrabold tracking-tight">Stats</span>
          </div>
          <p className="max-w-xs text-sm text-muted">
            Your listening, in numbers. A personal project by Damien Ta.
          </p>
        </div>
        {COLUMNS.map((column) => (
          <nav key={column.title} aria-label={column.title} className="space-y-2 text-sm">
            <p className="font-bold">{column.title}</p>
            <ul className="space-y-1.5">
              {column.links.map((link) => (
                <li key={link.label}>
                  <a
                    href={link.href}
                    {...(link.external ? { target: '_blank', rel: 'noreferrer' } : {})}
                    className="text-muted transition-colors hover:text-white"
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </nav>
        ))}
      </div>
      <div className="mx-auto flex max-w-5xl flex-wrap justify-between gap-2 border-t border-white/5 px-6 py-5 text-xs text-faint">
        <span>© {new Date().getFullYear()} Stats</span>
        <span>Not made by or affiliated with Spotify. Gig data from Ticketmaster.</span>
      </div>
    </footer>
  )
}
