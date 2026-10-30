import { ArrowLeft } from 'lucide-react'
import type { ReactNode } from 'react'

import { SiteFooter } from './SiteFooter'

export function Part({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="text-lg font-bold">{title}</h2>
      <div className="space-y-2 text-muted">{children}</div>
    </section>
  )
}

export function ExternalLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noreferrer" className="text-accent underline underline-offset-2">
      {children}
    </a>
  )
}

/** The shell for Privacy and Terms: readable without logging in. */
export function LegalPage({
  title,
  intro,
  updated,
  children,
}: {
  title: string
  intro: string
  updated: string
  children: ReactNode
}) {
  return (
    <div className="min-h-screen">
      <main className="mx-auto max-w-2xl space-y-8 px-6 py-10">
        <a
          href="/"
          className="inline-flex items-center gap-2 text-sm font-semibold text-muted hover:text-white"
        >
          <ArrowLeft className="size-4" />
          Back to Stats
        </a>
        <header className="space-y-2">
          <h1 className="text-3xl font-extrabold tracking-tight">{title}</h1>
          <p className="text-muted">{intro}</p>
          <p className="text-xs text-faint">Last updated {updated}</p>
        </header>
        {children}
      </main>
      <SiteFooter />
    </div>
  )
}
