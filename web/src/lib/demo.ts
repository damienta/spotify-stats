// Demo mode (open the app with ?demo): made-up data in the API's shapes, so the app can be
// tried, tested and screenshotted without logging in or showing anyone's real listening.

const DEMO_KEY = 'spotify-stats.demo'

export function isDemo(): boolean {
  try {
    if (new URLSearchParams(window.location.search).has('demo')) {
      sessionStorage.setItem(DEMO_KEY, '1')
      window.history.replaceState(null, '', '/')
    }
    return sessionStorage.getItem(DEMO_KEY) === '1'
  } catch {
    return false
  }
}

export function leaveDemo() {
  try {
    sessionStorage.removeItem(DEMO_KEY)
  } catch {
    // Nothing to clear.
  }
}

const ARTISTS = ['Nova Lane', 'The Static', 'Kairo', 'Mellow Fox', 'Juno Park', 'Arlo Grey', 'Pale Sun', 'Velvet Hours', 'Oslo Rain', 'Mira Vale']
const TRACKS = ['Night drive', 'Low tide', 'Paper planes', 'Golden', 'Echoes', 'Slow burn', 'Satellites', 'Glass house', 'Afterglow', 'Northern lights']

// A fixed pseudo-random sequence, so the demo looks the same on every load.
let seed = 7
function rand() {
  seed = (seed * 16807) % 2147483647
  return seed / 2147483647
}

const SCALE: Record<string, number> = {
  today: 0.03,
  this_week: 0.2,
  this_month: 0.8,
  this_year: 8,
  '4_weeks': 0.8,
  '6_months': 5,
  '12_months': 10,
  all_time: 40,
}

function track(i: number) {
  return {
    id: `demo${i}`,
    name: TRACKS[i % TRACKS.length],
    artists: [ARTISTS[i % ARTISTS.length]],
    album: `${TRACKS[(i + 3) % TRACKS.length]} (deluxe)`,
    image: null,
    duration_ms: 160_000 + (i % 5) * 20_000,
    url: null,
  }
}

function top(kind: string, scale: number) {
  return Array.from({ length: 50 }, (_, i) => ({
    name:
      kind === 'artists'
        ? (ARTISTS[i] ?? `Artist ${i + 1}`)
        : `${TRACKS[i % TRACKS.length]}${i >= TRACKS.length ? ` ${Math.floor(i / TRACKS.length) + 1}` : ''}`,
    artist_name: kind === 'artists' ? null : ARTISTS[i % ARTISTS.length],
    streams: Math.round((900 / (i + 1.5)) * scale),
    hours: ((50 / (i + 1.5)) * scale) / 1.2,
  }))
}

const pad = (n: number) => String(n).padStart(2, '0')
const ymd = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`

function minutes(stat: string, window: string) {
  const now = new Date()
  if (stat === 'minutes_by_hour') {
    return Array.from({ length: now.getHours() + 1 }, (_, h) => ({
      start: `${ymd(now)}T${pad(h)}:00:00`,
      minutes: h < 7 ? 0 : Math.round(rand() * 45),
    }))
  }
  if (stat === 'minutes_by_month') {
    return Array.from({ length: now.getMonth() + 1 }, (_, m) => ({
      start: `${now.getFullYear()}-${pad(m + 1)}-01`,
      minutes: 2500 + Math.round(rand() * 2500),
    }))
  }
  const days = window === 'this_week' ? (now.getDay() + 6) % 7 : now.getDate() - 1
  return Array.from({ length: days + 1 }, (_, i) => ({
    start: ymd(new Date(now.getFullYear(), now.getMonth(), now.getDate() - days + i)),
    minutes: 60 + Math.round(rand() * 180),
  }))
}

function data(stat: string, window: string): unknown {
  const s = SCALE[window] ?? 1
  switch (stat) {
    case 'totals':
      return { streams: Math.round(3200 * s), hours: 190 * s, artists: Math.round(40 + 300 * Math.sqrt(s)), tracks: Math.round(80 + 900 * Math.sqrt(s)), first_played: '', last_played: '' }
    case 'top_artists':
      return top('artists', s)
    case 'top_tracks':
    case 'top_albums':
      return top('tracks', s)
    case 'minutes_by_hour':
    case 'minutes_by_day':
    case 'minutes_by_month':
      return minutes(stat, window)
    case 'listening_clock':
      return Array.from({ length: 168 }, (_, i) => {
        const hour = i % 24
        const busy = hour >= 7 && hour <= 23 ? 1 + Math.sin((hour - 7) / 3) : 0.05
        return { weekday: Math.floor(i / 24), hour, minutes: Math.round(busy * 60 * s * rand()) }
      })
    case 'streaks':
      return { current: { days: 23, start: '2026-10-05', end: '2026-10-27' }, longest: { days: 412, start: '2023-02-01', end: '2024-03-18' } }
    case 'skips':
      return { skip_rate: 0.18, most_skipped_artists: [] }
    case 'discoveries':
      return ARTISTS.slice(5).map((artist_name, i) => ({ artist_name, first_played: '2026-10-0' + (i + 2), streams: 40 - i * 6, minutes: 130 - i * 20 }))
    case 'on_repeat':
      return TRACKS.slice(0, 5).map((track_name, i) => ({ track_name, artist_name: ARTISTS[i], day: `2026-10-${pad(20 + i)}`, streams: 14 - i * 2 }))
  }
  return null
}

/** Answers an API path the way the real API would, after a short pretend network delay. */
export async function demoApi(path: string): Promise<unknown> {
  await new Promise((r) => setTimeout(r, 250))
  const url = new URL(path, 'http://demo')
  if (url.pathname === '/me') return { user_id: 'demo', display_name: 'Demo listener' }
  if (url.pathname === '/me/now-playing') return { is_playing: true, progress_ms: 61_000, track: track(0) }
  if (url.pathname === '/me/recent') {
    const limit = Number(url.searchParams.get('limit') ?? 20)
    return {
      items: Array.from({ length: limit }, (_, i) => ({
        played_at: new Date(Date.now() - (i + 1) * 3.4 * 60_000).toISOString(),
        track: track(i + 1),
      })),
    }
  }
  const stat = url.pathname.replace('/me/stats/', '')
  const window = url.searchParams.get('window') ?? ''
  return { stat_name: stat, generated_at: new Date().toISOString(), data: data(stat, window) }
}
