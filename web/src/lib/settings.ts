// Display settings, kept in this browser. Later they can move to the users table so the phone
// app shares them.

import { useSyncExternalStore } from 'react'

export type TextSize = 'normal' | 'large' | 'larger'
export type MotionSetting = 'device' | 'reduce'
export type TimeUnit = 'minutes' | 'hours'
export type Contrast = 'normal' | 'high'
export type Accent = 'green' | 'blue' | 'pink' | 'orange' | 'purple'
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
  accent: Accent
}

const KEY = 'spotify-stats.settings'
const DEFAULTS: Settings = {
  textSize: 'normal',
  motion: 'device',
  city: 'London',
  time: 'minutes',
  contrast: 'normal',
  accent: 'green',
}
// Everything is sized in rem, so changing the root font size scales the whole app.
const ROOT_SIZE: Record<TextSize, string> = { normal: '100%', large: '112.5%', larger: '125%' }

// Every accent is light enough for black text on it and bright enough on the dark background.
// `rgb` is the base colour as numbers, for the cards' soft glow.
export const ACCENTS: Record<Accent, { label: string; base: string; bright: string; rgb: string }> = {
  green: { label: 'Green', base: '#1db954', bright: '#1ed760', rgb: '29, 185, 84' },
  blue: { label: 'Blue', base: '#4b9cff', bright: '#6cb0ff', rgb: '75, 156, 255' },
  pink: { label: 'Pink', base: '#f573a0', bright: '#ff8fb6', rgb: '245, 115, 160' },
  orange: { label: 'Orange', base: '#ff8a3d', bright: '#ffa463', rgb: '255, 138, 61' },
  purple: { label: 'Purple', base: '#a77bff', bright: '#bb98ff', rgb: '167, 123, 255' },
}

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
  // Tailwind's accent classes all read these two variables, so setting them recolours the app.
  const accent = ACCENTS[settings.accent] ?? ACCENTS.green
  root.style.setProperty('--color-accent', accent.base)
  root.style.setProperty('--color-accent-bright', accent.bright)
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
