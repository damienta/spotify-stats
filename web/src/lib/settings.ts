// Display settings, kept in this browser. Later they can move to the users table so the phone
// app shares them.

import { useSyncExternalStore } from 'react'

export type TextSize = 'normal' | 'large' | 'larger'
export type MotionSetting = 'device' | 'reduce'

export interface Settings {
  textSize: TextSize
  motion: MotionSetting
}

const KEY = 'spotify-stats.settings'
const DEFAULTS: Settings = { textSize: 'normal', motion: 'device' }
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
  document.documentElement.style.fontSize = ROOT_SIZE[settings.textSize] ?? '100%'
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

export function useSettings(): Settings {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
    () => current,
  )
}
