import { ChevronDown, ExternalLink, LogOut, Trash2 } from 'lucide-react'
import { useState } from 'react'

import { Section } from '@/components/Section'
import { Segmented } from '@/components/Segmented'
import SpotlightCard from '@/components/SpotlightCard'
import { Button } from '@/components/ui/button'
import { deleteAccount, logout } from '@/lib/api'
import { useMe } from '@/lib/queries'
import {
  CITIES,
  type MotionSetting,
  type TextSize,
  updateSettings,
  useSettings,
} from '@/lib/settings'

function Row({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="font-semibold">{label}</p>
        {hint && <p className="text-sm text-muted">{hint}</p>}
      </div>
      {children}
    </div>
  )
}

function DeleteAccount() {
  const [confirming, setConfirming] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const remove = async () => {
    setDeleting(true)
    setError(null)
    try {
      await deleteAccount()
    } catch {
      setError("Your data couldn't be deleted. Try again in a minute.")
      setDeleting(false)
    }
  }

  if (!confirming) {
    return (
      <Button variant="glass" onClick={() => setConfirming(true)} className="text-red-400">
        <Trash2 className="size-4" />
        Delete my data
      </Button>
    )
  }
  return (
    <div role="alert" className="space-y-3 rounded-2xl border border-red-500/40 bg-red-500/10 p-4">
      <p className="font-semibold">Delete everything?</p>
      <p className="text-sm text-muted">
        This removes your account, every play we've stored and all your stats. It can't be
        undone. You can log in again later, but your history starts from scratch.
      </p>
      {error && <p className="text-sm text-red-400">{error}</p>}
      <div className="flex flex-wrap gap-2">
        <Button onClick={remove} disabled={deleting} className="bg-red-500 text-white hover:bg-red-400">
          {deleting ? 'Deleting…' : 'Delete everything'}
        </Button>
        <Button variant="ghost" onClick={() => setConfirming(false)} disabled={deleting}>
          Cancel
        </Button>
      </div>
    </div>
  )
}

export function Settings() {
  const settings = useSettings()
  const me = useMe()
  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">Settings</h1>

      <Section title="Display">
        <SpotlightCard className="space-y-5 p-5">
          <Row label="Text size" hint="Makes everything bigger, not only the text.">
            <Segmented<TextSize>
              className="sm:w-80"
              value={settings.textSize}
              onChange={(textSize) => updateSettings({ textSize })}
              options={[
                { value: 'normal', label: 'Normal' },
                { value: 'large', label: 'Large' },
                { value: 'larger', label: 'Extra large' },
              ]}
            />
          </Row>
          <Row label="Animations" hint="Reduce turns off sliding and moving.">
            <Segmented<MotionSetting>
              className="sm:w-80"
              value={settings.motion}
              onChange={(motion) => updateSettings({ motion })}
              options={[
                { value: 'device', label: 'Like my device' },
                { value: 'reduce', label: 'Reduce' },
              ]}
            />
          </Row>
        </SpotlightCard>
      </Section>

      <Section title="Concerts">
        <SpotlightCard className="p-5">
          <Row label="Home city" hint="Gigs shows dates here first.">
            <div className="relative sm:w-80">
              <select
                aria-label="Home city"
                value={settings.city}
                onChange={(e) => updateSettings({ city: e.target.value })}
                className="glass h-10 w-full appearance-none rounded-full pr-10 pl-4 text-sm font-semibold text-white outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
              >
                {CITIES.map((c) => (
                  <option key={c} value={c} className="bg-neutral-900">
                    {c}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute top-1/2 right-4 size-4 -translate-y-1/2 text-muted" />
            </div>
          </Row>
        </SpotlightCard>
      </Section>

      <Section title="Account">
        <SpotlightCard className="space-y-5 p-5">
          <Row label="Logged in as" hint={me.data?.display_name ?? '…'}>
            <Button variant="glass" onClick={logout}>
              <LogOut className="size-4" />
              Log out
            </Button>
          </Row>
          <Row label="Spotify access" hint="Stop this app reading your Spotify, on Spotify's site.">
            <Button variant="glass" asChild>
              <a href="https://www.spotify.com/account/apps/" target="_blank" rel="noreferrer">
                Manage apps
                <ExternalLink className="size-4" />
              </a>
            </Button>
          </Row>
          <Row label="Privacy and terms" hint="What we keep about you, and the rules.">
            <div className="flex gap-2">
              <Button variant="glass" asChild>
                <a href="/privacy">Privacy</a>
              </Button>
              <Button variant="glass" asChild>
                <a href="/terms">Terms</a>
              </Button>
            </div>
          </Row>
          <Row label="Delete my data" hint="Your account, plays and stats, from everywhere we store them.">
            <DeleteAccount />
          </Row>
        </SpotlightCard>
      </Section>
    </div>
  )
}
