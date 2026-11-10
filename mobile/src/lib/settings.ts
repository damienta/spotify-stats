// Display settings. Only the time unit for now, with the web app's default; the Settings screen
// that changes it (and saves it on the phone) comes in a later PR.

export type TimeUnit = 'minutes' | 'hours'

export interface Settings {
  time: TimeUnit
}

const current: Settings = { time: 'minutes' }

export function getSettings(): Settings {
  return current
}
