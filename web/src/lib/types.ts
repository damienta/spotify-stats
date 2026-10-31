// Shapes of what the API returns (see api/src/stats_api/app.py and jobs/src/stats_jobs).

export interface Me {
  user_id: string
  display_name: string
}

export interface Track {
  id: string | null
  name: string | null
  artists: string[]
  album: string | null
  image: string | null
  duration_ms: number | null
  url: string | null
}

export interface NowPlaying {
  is_playing: boolean
  progress_ms: number | null
  track: Track | null
}

export interface Recent {
  items: { played_at: string; track: Track }[]
}

export interface Totals {
  streams: number
  hours: number
  artists: number
  tracks: number
  first_played: string
  last_played: string
}

export interface TopRow {
  name: string
  artist_name: string | null
  streams: number
  hours: number
  // From Spotify's catalogue; missing until the stats job has looked the row up.
  image?: string | null
  url?: string | null
}

export interface Period {
  start: string
  minutes: number
}

export interface ClockCell {
  weekday: number
  hour: number
  minutes: number
}

export interface Streak {
  days: number
  start: string | null
  end: string | null
}

export interface Streaks {
  current: Streak
  longest: Streak
}

export interface Skips {
  skip_rate: number | null
  most_skipped_artists: { name: string; plays: number; skip_rate: number }[]
}

export interface Discovery {
  artist_name: string
  first_played: string
  streams: number
  minutes: number
  image?: string | null
  url?: string | null
}

export interface Repeat {
  track_name: string
  artist_name: string
  day: string
  streams: number
  image?: string | null
  url?: string | null
}

export interface Gig {
  name: string
  date: string
  time: string | null
  venue: string | null
  city: string | null
  url: string
  image: string | null
  /** Ticketmaster's: onsale, offsale (sold out, or not on sale yet), rescheduled, postponed. */
  status?: string | null
  /** When general sale opens (UTC). */
  sale_start?: string | null
  presales?: { name: string | null; start: string | null; end: string | null }[]
}

/** One of your top artists' pages (jobs/src/stats_jobs/artists.py). */
export interface ArtistPage {
  name: string
  minutes: number
  streams: number
  tracks: number
  /** Share of everything you've played, 0 to 1. */
  share: number
  first_played: string
  first_track: string
  last_played: string
  /** Your rank in each range, null outside its top 100. */
  ranks: Record<'4_weeks' | '6_months' | '12_months' | 'all_time', number | null>
  minutes_by_month: Period[]
  top_tracks: TopRow[]
  image?: string | null
  url?: string | null
}

/** One of your top artists with UK dates announced, from Ticketmaster. */
export interface Touring {
  artist: string
  rank: number
  image?: string | null
  url?: string | null
  events: Gig[]
}
