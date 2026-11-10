// Display settings, kept in this browser. Later they can move to the users table so the phone
// app shares them.

import { useSyncExternalStore } from 'react'

export type TextSize = 'normal' | 'large' | 'larger'
export type MotionSetting = 'device' | 'reduce'
export type TimeUnit = 'minutes' | 'hours'
export type Contrast = 'normal' | 'high'
/** Where "your artists on tour" looks first. ANYWHERE keeps them in your favourite order. */
export const ANYWHERE = 'Anywhere in the UK'
export const CITIES = [
  'London', 'Manchester', 'Birmingham', 'Glasgow', 'Leeds', 'Liverpool', 'Bristol',
  'Newcastle upon Tyne', 'Nottingham', 'Sheffield', 'Brighton', 'Cardiff', 'Edinburgh',
  'Belfast', ANYWHERE,
]

export interface Settings {
  textSize: TextSize
  motion: MotionSetting
  city: string
  time: TimeUnit
  contrast: Contrast
}

const KEY = 'spotify-stats.settings'
const DEFAULTS: Settings = {
  textSize: 'normal',
  motion: 'device',
  city: 'London',
  time: 'minutes',
  contrast: 'normal',
}
// Everything is sized in rem, so changing the root font size scales the whole app.
const ROOT_SIZE: Record<TextSize, string> = { normal: '100%', large: '112.5%', larger: '125%' }

function load(): Settings {
  try {
    return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(KEY) ?? '{}') }
  } catch {
    return DEFAULTS
  }
}

let current = load()
const listeners = new Set<() => void>()

function apply(settings: Settings) {
  const root = document.documentElement
  root.style.fontSize = ROOT_SIZE[settings.textSize] ?? '100%'
  // index.css brightens grey text and borders under this attribute.
  root.dataset.contrast = settings.contrast
}
apply(current)

export function updateSettings(change: Partial<Settings>) {
  current = { ...current, ...change }
  apply(current)
  try {
    localStorage.setItem(KEY, JSON.stringify(current))
  } catch {
    // Private mode: the setting lasts until the tab closes.
  }
  listeners.forEach((l) => l())
}

/** The settings right now, for plain functions; components use useSettings so they redraw. */
export function getSettings(): Settings {
  return current
}

export function useSettings(): Settings {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
    () => current,
  )
}
