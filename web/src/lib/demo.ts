// Demo mode (open the app with ?demo): made-up data in the API's shapes, so the app can be
// tried, tested and screenshotted without logging in or showing anyone's real listening.

// Used only inside functions, so the import cycle with api.ts is safe.
import { ApiError } from './api'

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
    case 'concerts': {
      const soon = (days: number) => ymd(new Date(Date.now() + days * 86_400_000))
      const venues = [['Barrowland', 'Glasgow'], ['Albert Hall', 'Manchester'], ['Rock City', 'Nottingham'], ['O2 Academy Brixton', 'London'], ['O2 Academy', 'Birmingham']]
      const hours = (h: number) => new Date(Date.now() + h * 3_600_000).toISOString()
      // A mix: on sale, presale now, general sale soon, sold out; some tours skip London.
      const sales = [
        { status: 'onsale', sale_start: hours(-500), presales: [] },
        { status: 'offsale', sale_start: hours(14), presales: [{ name: 'Artist Presale', start: hours(-10), end: hours(13) }] },
        { status: 'offsale', sale_start: hours(60), presales: [] },
        { status: 'offsale', sale_start: hours(-300), presales: [] },
      ]
      return [1, 3, 4, 7, 9, 12, 15].map((rank, i) => ({
        artist: ARTISTS[(rank - 1) % ARTISTS.length],
        rank,
        events: Array.from({ length: 1 + ((i * 2) % 5) }, (_, j) => ({
          name: `${ARTISTS[(rank - 1) % ARTISTS.length]} live`,
          date: soon(12 + i * 9 + j * 3),
          time: '19:30:00',
          venue: venues[j % 5][0],
          city: venues[j % 5][1],
          url: 'https://www.ticketmaster.co.uk/',
          image: null,
          ...sales[i % 4],
        })),
      }))
    }
    case 'on_repeat':
      return TRACKS.slice(0, 5).map((track_name, i) => ({ track_name, artist_name: ARTISTS[i], day: `2026-10-${pad(20 + i)}`, streams: 14 - i * 2 }))
  }
  return null
}

function artist(name: string) {
  const rank = ARTISTS.findIndex((a) => a.toLowerCase() === name.toLowerCase())
  if (rank < 0) throw new ApiError(404, 'only your top artists have a page')
  const now = new Date()
  const months = Array.from({ length: 24 }, (_, i) => {
    const d = new Date(now.getFullYear(), now.getMonth() - 23 + i, 1)
    return { start: ymd(d), minutes: i < 4 + rank ? 0 : Math.round((400 + rand() * 900) / (rank + 1)) }
  })
  const total = months.reduce((sum, m) => sum + m.minutes, 0)
  return {
    name: ARTISTS[rank],
    minutes: total,
    streams: Math.round(total / 3.2),
    tracks: 34 - rank * 2,
    share: 0.11 / (rank + 1),
    first_played: months.find((m) => m.minutes)!.start + ' 21:14:00',
    first_track: TRACKS[(rank + 4) % TRACKS.length],
    last_played: new Date(Date.now() - (rank + 1) * 3_600_000).toISOString(),
    ranks: { '4_weeks': rank + 1, '6_months': rank + 2, '12_months': rank + 1, all_time: rank + 3 },
    minutes_by_month: months,
    top_tracks: TRACKS.map((t, i) => ({ name: t, artist_name: ARTISTS[rank], streams: Math.round(200 / (i + 1)), hours: total / 60 / 3 / (i + 1.5) })),
  }
}

// Made-up friends (names and listening), kept in memory so adding and removing work until
// the page reloads.
const FRIENDS = [
  { user_id: 'demo-sam', display_name: 'Sam', minutes: 1412, streak: 41, offset: 0, sharing: true },
  { user_id: 'demo-priya', display_name: 'Priya', minutes: 2210, streak: 9, offset: 3, sharing: true },
  { user_id: 'demo-alex', display_name: 'Alex', minutes: 0, streak: 0, offset: 6, sharing: false },
]
const STRANGER = { user_id: 'demo-jo', display_name: 'Jo', minutes: 655, streak: 3, offset: 8, sharing: true }
const demoState = { share: true, friends: FRIENDS.map((f) => f.user_id), invite: 'demo-invite' }
const MY_MINUTES = 1766

const everyone = [...FRIENDS, STRANGER]
const person = (id: string) => everyone.find((f) => f.user_id === id)
// Each friend's artists are yours, shifted, plus a few you've never played.
const theirArtists = (offset: number) =>
  [...ARTISTS.slice(offset), 'Lumen Tide', 'Coral Static', 'Hollow Pines'].map((name) => ({
    name,
    artist_name: null,
    image: null,
    url: null,
  }))

function friends(path: string, method: string, body: { invite?: string }): unknown {
  const visible = (id: string) => {
    const f = person(id)
    if (!f || !demoState.friends.includes(id) || !f.sharing) throw new ApiError(404, 'not found')
    return f
  }
  if (path === '/friends' && method === 'GET') {
    return {
      friends: demoState.friends.map((id) => {
        const f = person(id)!
        return {
          user_id: id,
          display_name: f.display_name,
          since: '2026-10-20T18:00:00+00:00',
          sharing: f.sharing,
          minutes_this_week: f.sharing ? f.minutes : null,
        }
      }).sort((a, b) => a.display_name.localeCompare(b.display_name)),
    }
  }
  if (path === '/friends/leaderboard') {
    const rows = [
      { user_id: 'demo', display_name: 'Demo listener', minutes: MY_MINUTES, is_you: true },
      ...demoState.friends
        .map((id) => person(id)!)
        .filter((f) => f.sharing)
        .map((f) => ({ user_id: f.user_id, display_name: f.display_name, minutes: f.minutes, is_you: false })),
    ].sort((a, b) => b.minutes - a.minutes)
    return { leaderboard: rows.map((r, i) => ({ rank: i + 1, ...r })) }
  }
  if (path === '/friends/invite') return { invite: demoState.invite }
  if (path === '/friends/invite/reset') {
    demoState.invite = `demo-invite-${Date.now().toString(36)}`
    return { invite: demoState.invite }
  }
  // In the demo, any link other than your own is from Jo.
  if (path === '/friends/invite/preview') {
    return {
      display_name: body.invite === demoState.invite ? 'Demo listener' : STRANGER.display_name,
      is_you: body.invite === demoState.invite,
      already_friends: demoState.friends.includes(STRANGER.user_id),
    }
  }
  if (path === '/friends' && method === 'POST') {
    if (body.invite === demoState.invite) throw new ApiError(400, "that's your own invite link")
    if (demoState.friends.includes(STRANGER.user_id)) throw new ApiError(409, "you're already friends")
    demoState.friends.push(STRANGER.user_id)
    return { user_id: STRANGER.user_id, display_name: STRANGER.display_name, since: new Date().toISOString() }
  }
  const [, , id, part] = path.split('/')
  if (method === 'DELETE') {
    if (!demoState.friends.includes(id)) throw new ApiError(404, 'not found')
    demoState.friends = demoState.friends.filter((f) => f !== id)
    return undefined
  }
  const f = visible(id)
  const artists = theirArtists(f.offset)
  if (part === 'summary') {
    return {
      user_id: id,
      display_name: f.display_name,
      ready: true,
      top_artists: artists.slice(0, 10),
      top_tracks: TRACKS.map((name, i) => ({ name, artist_name: artists[i % artists.length].name, image: null, url: null })),
      minutes_this_week: f.minutes,
      streak_days: f.streak,
    }
  }
  const mine = ARTISTS.map((name) => name)
  return {
    user_id: id,
    display_name: f.display_name,
    taste_match: Math.max(8, 74 - f.offset * 9),
    both_love: artists
      .map((a, i) => ({ ...a, your_rank: mine.indexOf(a.name) + 1, their_rank: i + 1 }))
      .filter((a) => a.your_rank > 0)
      .sort((a, b) => Math.max(a.your_rank, a.their_rank) - Math.max(b.your_rank, b.their_rank) || a.your_rank - b.your_rank)
      .slice(0, 10),
    new_to_you: artists.filter((a) => !mine.includes(a.name)),
  }
}

/** Answers an API path the way the real API would, after a short pretend network delay. */
export async function demoApi(path: string, send?: { method: string; body?: unknown }): Promise<unknown> {
  await new Promise((r) => setTimeout(r, 250))
  const url = new URL(path, 'http://demo')
  const method = send?.method ?? 'GET'
  if (url.pathname === '/me') {
    const body = send?.body as { share_with_friends?: boolean } | undefined
    if (method === 'PATCH') demoState.share = body?.share_with_friends ?? demoState.share
    return { user_id: 'demo', display_name: 'Demo listener', share_with_friends: demoState.share }
  }
  if (url.pathname.startsWith('/friends')) return friends(url.pathname, method, (send?.body ?? {}) as { invite?: string })
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
  if (url.pathname === '/me/artist') return { stat_name: 'artist', generated_at: new Date().toISOString(), data: artist(url.searchParams.get('name') ?? '') }
  const stat = url.pathname.replace('/me/stats/', '')
  const window = url.searchParams.get('window') ?? ''
  return { stat_name: stat, generated_at: new Date().toISOString(), data: data(stat, window) }
}
